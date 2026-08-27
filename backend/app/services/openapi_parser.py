import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple, Union
import yaml
import httpx
logger = logging.getLogger(__name__)
class OpenApiParser:
    """
    全版本 OpenAPI Specification 解析器
    支援：
    - Swagger / OpenAPI 2.0 (JSON / YAML)
    - OpenAPI 3.0.x (JSON / YAML)
    - OpenAPI 3.1.x (JSON / YAML, JSON Schema 2020-12)
    """
    @classmethod
    async def parse(
        cls,
        spec_content_or_url: str,
        default_base_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        解析 OpenAPI 規格文字、JSON/YAML 字串或遠端 URL
        回傳結構：
        {
            "version": "openapi_3.0" | "swagger_2.0" | "openapi_3.1",
            "title": "API Title",
            "description": "...",
            "base_url": "https://api.example.com",
            "endpoints": [ ... ],
            "raw_spec": { ... }
        }
        """
        raw_text = spec_content_or_url.strip()
        if raw_text.startswith("http://") or raw_text.startswith("https://"):
            try:
                async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                    resp = await client.get(raw_text)
                    if resp.status_code != 200:
                        raise ValueError(f"無法從該 URL 取得 OpenAPI 規格 (狀態碼 {resp.status_code})")
                    raw_text = resp.text
            except Exception as e:
                raise ValueError(f"獲取遠端 OpenAPI 規格失敗: {str(e)}")
        spec_dict = cls._parse_raw_text_to_dict(raw_text)
        if not isinstance(spec_dict, dict):
            raise ValueError("OpenAPI 規格格式無效，必須是合法的 JSON 或 YAML 物件。")
        spec_version = cls._detect_spec_version(spec_dict)
        info = spec_dict.get("info", {})
        title = info.get("title", "未命名 API")
        description = info.get("description", "")
        extracted_base_url = cls._extract_base_url(spec_dict, spec_version)
        effective_base_url = default_base_url or extracted_base_url or ""
        endpoints = cls._extract_endpoints(spec_dict, spec_version, effective_base_url)
        return {
            "version": spec_version,
            "title": title,
            "description": description,
            "base_url": effective_base_url,
            "endpoints_count": len(endpoints),
            "endpoints": endpoints,
            "raw_spec": spec_dict
        }
    @classmethod
    def _parse_raw_text_to_dict(cls, text: str) -> Dict[str, Any]:
        """嘗試以 JSON 或 YAML 解析文字"""
        text = text.strip()
        if text.startswith("{") or text.startswith("["):
            try:
                return json.loads(text)
            except Exception:
                pass
        try:
            return yaml.safe_load(text)
        except Exception as e:
            try:
                return json.loads(text)
            except Exception:
                raise ValueError(f"無法將內容解析為 JSON 或 YAML: {str(e)}")
    @classmethod
    def _detect_spec_version(cls, spec: Dict[str, Any]) -> str:
        """偵測 OpenAPI 規格版本"""
        if "swagger" in spec:
            ver = str(spec.get("swagger", "")).strip()
            if ver.startswith("2"):
                return "swagger_2.0"
            return "swagger_2.0"
        elif "openapi" in spec:
            ver = str(spec.get("openapi", "")).strip()
            if ver.startswith("3.1"):
                return "openapi_3.1"
            elif ver.startswith("3.0"):
                return "openapi_3.0"
            elif ver.startswith("3"):
                return "openapi_3.0"
        if "paths" in spec:
            if "definitions" in spec or "host" in spec:
                return "swagger_2.0"
            return "openapi_3.0"
        raise ValueError("無法識別 OpenAPI 或 Swagger 規格版本，請確認包含 'openapi' 或 'swagger' 宣告欄位。")
    @classmethod
    def _extract_base_url(cls, spec: Dict[str, Any], version: str) -> str:
        """從規格中提取基礎 URL (Base URL)"""
        if version == "swagger_2.0":
            host = spec.get("host", "").strip()
            base_path = spec.get("basePath", "").strip()
            schemes = spec.get("schemes", ["https"])
            scheme = schemes[0] if schemes else "https"
            if host:
                if not base_path.startswith("/") and base_path:
                    base_path = "/" + base_path
                return f"{scheme}://{host}{base_path}".rstrip("/")
            return base_path.rstrip("/")
        else:
            servers = spec.get("servers", [])
            if servers and isinstance(servers, list):
                first_server = servers[0]
                if isinstance(first_server, dict):
                    url = first_server.get("url", "")
                    variables = first_server.get("variables", {})
                    for var_name, var_info in variables.items():
                        default_val = var_info.get("default", "")
                        url = url.replace(f"{{{var_name}}}", str(default_val))
                    return url.rstrip("/")
                elif isinstance(first_server, str):
                    return first_server.rstrip("/")
        return ""
    @classmethod
    def _resolve_ref(cls, ref: str, root_spec: Dict[str, Any], visited: Optional[set] = None) -> Dict[str, Any]:
        """遞迴解析 $ref 本地內部參照引用"""
        if visited is None:
            visited = set()
        if ref in visited or not ref.startswith("#/"):
            return {"type": "object", "description": f"參照目標: {ref}"}
        visited.add(ref)
        parts = ref.lstrip("#/").split("/")
        curr = root_spec
        try:
            for p in parts:
                p = p.replace("~1", "/").replace("~0", "~")
                curr = curr[p]
        except Exception:
            return {"type": "object", "description": f"無法解析之參照: {ref}"}
        if isinstance(curr, dict) and "$ref" in curr:
            return cls._resolve_ref(curr["$ref"], root_spec, visited)
        elif isinstance(curr, dict):
            return cls._clean_schema(curr, root_spec, visited)
        return curr if isinstance(curr, dict) else {}
    @classmethod
    def _clean_schema(cls, schema: Dict[str, Any], root_spec: Dict[str, Any], visited: Optional[set] = None) -> Dict[str, Any]:
        """遞迴清理並正規化 JSON Schema（相容 Function Calling 與各版本型別定義）"""
        if not isinstance(schema, dict):
            return {"type": "string"}
        if "$ref" in schema:
            return cls._resolve_ref(schema["$ref"], root_spec, visited)
        cleaned: Dict[str, Any] = {}
        raw_type = schema.get("type")
        if isinstance(raw_type, list):
            non_null = [t for t in raw_type if t != "null"]
            cleaned["type"] = non_null[0] if non_null else "string"
        elif isinstance(raw_type, str):
            cleaned["type"] = raw_type
        elif "properties" in schema:
            cleaned["type"] = "object"
        elif "items" in schema:
            cleaned["type"] = "array"
        else:
            cleaned["type"] = "string"
        if "description" in schema:
            cleaned["description"] = schema["description"]
        if "enum" in schema:
            cleaned["enum"] = schema["enum"]
        if "default" in schema:
            cleaned["default"] = schema["default"]
        if "properties" in schema and isinstance(schema["properties"], dict):
            props = {}
            for prop_name, prop_val in schema["properties"].items():
                props[prop_name] = cls._clean_schema(prop_val, root_spec, visited)
            cleaned["properties"] = props
        if "required" in schema and isinstance(schema["required"], list):
            cleaned["required"] = [str(r) for r in schema["required"]]
        if "items" in schema and isinstance(schema["items"], dict):
            cleaned["items"] = cls._clean_schema(schema["items"], root_spec, visited)
        return cleaned
    @classmethod
    def _extract_endpoints(
        cls,
        spec: Dict[str, Any],
        version: str,
        base_url: str
    ) -> List[Dict[str, Any]]:
        """提取並轉換所有 API 端點為標準化 Tool 結構"""
        paths = spec.get("paths", {})
        endpoints = []
        valid_methods = {"get", "post", "put", "delete", "patch", "head", "options"}
        for path_str, path_item in paths.items():
            if not isinstance(path_item, dict):
                continue
            common_params = path_item.get("parameters", [])
            if not isinstance(common_params, list):
                common_params = []
            for method_name, op in path_item.items():
                method_lower = method_name.lower()
                if method_lower not in valid_methods or not isinstance(op, dict):
                    continue
                endpoint_info = cls._parse_single_operation(
                    path_str=path_str,
                    method=method_lower.upper(),
                    op=op,
                    common_params=common_params,
                    root_spec=spec,
                    version=version,
                    base_url=base_url
                )
                if endpoint_info:
                    endpoints.append(endpoint_info)
        return endpoints
    @classmethod
    def _parse_single_operation(
        cls,
        path_str: str,
        method: str,
        op: Dict[str, Any],
        common_params: List[Any],
        root_spec: Dict[str, Any],
        version: str,
        base_url: str
    ) -> Dict[str, Any]:
        """解析單一 API 操作並建構 Function Calling Tool 規格"""
        summary = op.get("summary") or op.get("description") or f"{method} {path_str}"
        description = op.get("description") or op.get("summary") or summary
        operation_id = op.get("operationId")
        tool_name = cls._generate_tool_name(method, path_str, operation_id)
        display_name = summary.split("\n")[0][:60]
        op_params = op.get("parameters", [])
        if not isinstance(op_params, list):
            op_params = []
        all_raw_params = list(common_params) + list(op_params)
        param_properties: Dict[str, Any] = {}
        required_params: List[str] = []
        param_locations: Dict[str, str] = {}
        body_content_type = "application/json"
        has_body = False
        for p in all_raw_params:
            if isinstance(p, dict) and "$ref" in p:
                p = cls._resolve_ref(p["$ref"], root_spec)
            if not isinstance(p, dict):
                continue
            p_name = p.get("name")
            p_in = p.get("in", "query")
            p_required = bool(p.get("required", False))
            p_desc = p.get("description", "")
            if not p_name:
                continue
            param_locations[p_name] = p_in
            if p_required or p_in == "path":
                required_params.append(p_name)
            if version == "swagger_2.0" and p_in == "body":
                has_body = True
                body_schema = p.get("schema", {})
                cleaned_body_schema = cls._clean_schema(body_schema, root_spec)
                if cleaned_body_schema.get("type") == "object" and "properties" in cleaned_body_schema:
                    for b_prop_name, b_prop_schema in cleaned_body_schema.get("properties", {}).items():
                        param_properties[b_prop_name] = b_prop_schema
                        param_locations[b_prop_name] = "body"
                    for b_req in cleaned_body_schema.get("required", []):
                        if b_req not in required_params:
                            required_params.append(b_req)
                else:
                    param_properties[p_name] = {
                        "type": cleaned_body_schema.get("type", "object"),
                        "description": p_desc or "請求本文資料物件"
                    }
                continue
            if "schema" in p:
                cleaned_p_schema = cls._clean_schema(p["schema"], root_spec)
                if p_desc and "description" not in cleaned_p_schema:
                    cleaned_p_schema["description"] = p_desc
                param_properties[p_name] = cleaned_p_schema
            else:
                p_type = p.get("type", "string")
                prop_item: Dict[str, Any] = {
                    "type": p_type if p_type in ["string", "number", "integer", "boolean", "array", "object"] else "string",
                    "description": p_desc or f"位置: {p_in}"
                }
                if "enum" in p:
                    prop_item["enum"] = p["enum"]
                if "default" in p:
                    prop_item["default"] = p["default"]
                if p_type == "array" and "items" in p:
                    prop_item["items"] = cls._clean_schema(p["items"], root_spec)
                param_properties[p_name] = prop_item
        if version != "swagger_2.0" and "requestBody" in op:
            req_body = op.get("requestBody")
            if isinstance(req_body, dict) and "$ref" in req_body:
                req_body = cls._resolve_ref(req_body["$ref"], root_spec)
            if isinstance(req_body, dict):
                has_body = True
                req_body_required = bool(req_body.get("required", False))
                content = req_body.get("content", {})
 
                target_mime = None
                for mime in ["application/json", "application/x-www-form-urlencoded", "multipart/form-data"]:
                    if mime in content:
                        target_mime = mime
                        break
                if not target_mime and content:
                    target_mime = list(content.keys())[0]
                if target_mime:
                    body_content_type = target_mime
                    body_schema_obj = content[target_mime].get("schema", {})
                    cleaned_body = cls._clean_schema(body_schema_obj, root_spec)
                    if cleaned_body.get("type") == "object" and "properties" in cleaned_body:
                        for b_name, b_schema in cleaned_body.get("properties", {}).items():
                            param_properties[b_name] = b_schema
                            param_locations[b_name] = "body"
                        if req_body_required:
                            for b_req in cleaned_body.get("required", []):
                                if b_req not in required_params:
                                    required_params.append(b_req)
                    else:
                        param_properties["request_body"] = {
                            "type": cleaned_body.get("type", "object"),
                            "description": req_body.get("description", "請求本文資料")
                        }
                        param_locations["request_body"] = "body"
                        if req_body_required:
                            required_params.append("request_body")
        function_definition = {
            "type": "function",
            "function": {
                "name": tool_name,
                "description": f"{summary}\n\n詳細說明: {description}".strip() if description != summary else summary,
                "parameters": {
                    "type": "object",
                    "properties": param_properties,
                    "required": list(set(required_params))
                }
            }
        }
        full_url = f"{base_url.rstrip('/')}/{path_str.lstrip('/')}" if base_url else path_str
        return {
            "name": tool_name,
            "display_name": display_name,
            "description": summary,
            "long_description": description,
            "method": method,
            "path": path_str,
            "base_url": base_url,
            "full_url": full_url,
            "has_body": has_body,
            "body_content_type": body_content_type,
            "param_locations": param_locations,
            "parameters_schema": {
                "type": "object",
                "properties": param_properties,
                "required": list(set(required_params))
            },
            "function_definition": function_definition,
            "tags": op.get("tags", []),
            "spec_version": version
        }
    @classmethod
    def _generate_tool_name(cls, method: str, path: str, operation_id: Optional[str]) -> str:
        """生成符合 Function Calling 規範的唯一合法工具名稱 (英文字母、數字與底線)"""
        if operation_id:
            clean_op = re.sub(r'[^a-zA-Z0-9_]', '_', operation_id.strip())
            clean_op = re.sub(r'_+', '_', clean_op).strip('_')
            if clean_op and re.match(r'^[a-zA-Z]', clean_op):
                return clean_op.lower()
        path_clean = re.sub(r'[\{\}\/]', '_', path)
        combined = f"{method.lower()}_{path_clean}"
        clean_name = re.sub(r'[^a-zA-Z0-9_]', '_', combined)
        clean_name = re.sub(r'_+', '_', clean_name).strip('_')
        if not re.match(r'^[a-zA-Z]', clean_name):
            clean_name = f"api_{clean_name}"
        return clean_name[:64]