import json
import logging
import time
from typing import Any, Dict, List, Optional
import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.models.database import get_db
from app.models import (
    CustomApiTool,
    CustomApiToolCreate,
    CustomApiToolUpdate,
    CustomApiToolResponse,
    OpenApiParseRequest,
    OpenApiImportRequest,
    ToolTestRequest,
)
from app.core.jwt_auth import get_current_active_user as get_current_user
from app.services.openapi_parser import OpenApiParser
logger = logging.getLogger(__name__)
router = APIRouter()
def _serialize_tool_model(tool: CustomApiTool) -> Dict[str, Any]:
    """將資料庫 CustomApiTool 模型轉換為 Dict"""
    headers = None
    if tool.headers:
        try:
            headers = json.loads(tool.headers)
        except Exception:
            headers = {}
    auth_config = None
    if tool.auth_config:
        try:
            auth_config = json.loads(tool.auth_config)
        except Exception:
            auth_config = {}
    parameters_schema = None
    if tool.parameters_schema:
        try:
            parameters_schema = json.loads(tool.parameters_schema)
        except Exception:
            parameters_schema = {"type": "object", "properties": {}}
    request_body_schema = None
    if tool.request_body_schema:
        try:
            request_body_schema = json.loads(tool.request_body_schema)
        except Exception:
            request_body_schema = None
    param_locations = None
    if tool.param_locations:
        try:
            param_locations = json.loads(tool.param_locations)
        except Exception:
            param_locations = {}
    return {
        "id": tool.id,
        "name": tool.name,
        "display_name": tool.display_name,
        "description": tool.description,
        "category": tool.category or "custom_api",
        "method": (tool.method or "GET").upper(),
        "url": tool.url,
        "base_url": tool.base_url,
        "path": tool.path,
        "headers": headers,
        "auth_type": tool.auth_type or "none",
        "auth_config": auth_config,
        "parameters_schema": parameters_schema,
        "request_body_schema": request_body_schema,
        "param_locations": param_locations,
        "response_mapping": tool.response_mapping,
        "is_enabled": bool(tool.is_enabled),
        "timeout": tool.timeout or 15,
        "spec_version": tool.spec_version or "manual",
        "created_at": tool.created_at,
        "updated_at": tool.updated_at,
    }
async def execute_http_api_tool(tool_dict: Dict[str, Any], arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    通用 HTTP API 工具非同步執行器
    支援：
    - Path 變數替換（如 /pets/{petId}）
    - Query 參數組裝
    - Header 參數與 Auth 注入
    - JSON Body 或 FormData 序列化
    - 隔離超時與錯誤保護
    """
    start_time = time.time()
    method = (tool_dict.get("method") or "GET").upper()
    base_url = (tool_dict.get("base_url") or "").rstrip("/")
    path = tool_dict.get("path") or ""
    url = tool_dict.get("url") or ""
    if not url and base_url and path:
        url = f"{base_url}/{path.lstrip('/')}"
    elif not url:
        url = path
    param_locations = tool_dict.get("param_locations") or {}
    headers = dict(tool_dict.get("headers") or {})
    timeout = int(tool_dict.get("timeout") or 15)
    auth_type = tool_dict.get("auth_type", "none")
    auth_config = tool_dict.get("auth_config") or {}
    if auth_type == "bearer" and auth_config.get("token"):
        headers["Authorization"] = f"Bearer {auth_config['token']}"
    elif auth_type == "api_key":
        key_name = auth_config.get("key_name", "X-API-Key")
        key_value = auth_config.get("key_value", "")
        key_in = auth_config.get("key_in", "header")
        if key_in == "header" and key_name and key_value:
            headers[key_name] = key_value
        elif key_in == "query" and key_name and key_value:
            arguments[key_name] = key_value
    elif auth_type == "basic" and auth_config.get("username"):
        import base64
        u = auth_config.get("username", "")
        p = auth_config.get("password", "")
        b64_auth = base64.b64encode(f"{u}:{p}".encode()).decode()
        headers["Authorization"] = f"Basic {b64_auth}"
    query_params: Dict[str, Any] = {}
    body_data: Dict[str, Any] = {}
    path_replaced_url = url
    for k, v in arguments.items():
        loc = param_locations.get(k)
        if f"{{{k}}}" in path_replaced_url or loc == "path":
            path_replaced_url = path_replaced_url.replace(f"{{{k}}}", str(v))
        elif loc == "header":
            headers[k] = str(v)
        elif loc == "body":
            body_data[k] = v
        elif loc == "query":
            query_params[k] = v
        else:
            if method in ["POST", "PUT", "PATCH"]:
                body_data[k] = v
            else:
                query_params[k] = v
    if "request_body" in arguments and isinstance(arguments["request_body"], dict):
        body_data = arguments["request_body"]
    try:
        async with httpx.AsyncClient(timeout=float(timeout), follow_redirects=True) as client:
            req_kwargs: Dict[str, Any] = {
                "method": method,
                "url": path_replaced_url,
                "headers": headers,
                "params": query_params if query_params else None,
            }
            if method in ["POST", "PUT", "PATCH", "DELETE"]:
                if body_data:
                    req_kwargs["json"] = body_data
            response = await client.request(**req_kwargs)
            duration = round(time.time() - start_time, 3)
            content_type = response.headers.get("content-type", "").lower()
            if "application/json" in content_type:
                try:
                    res_body = response.json()
                except Exception:
                    res_body = response.text
            else:
                res_body = response.text[:4000]
            return {
                "status_code": response.status_code,
                "is_success": response.is_success,
                "duration_seconds": duration,
                "url": str(response.url),
                "data": res_body
            }
    except Exception as e:
        duration = round(time.time() - start_time, 3)
        logger.error(f"執行自訂 API 工具 {tool_dict.get('name')} 失敗: {e}")
        return {
            "status_code": 500,
            "is_success": False,
            "duration_seconds": duration,
            "url": path_replaced_url,
            "error": f"API 請求連線失敗: {str(e)}"
        }
@router.post("/parse-spec")
async def parse_openapi_spec(
    request_data: OpenApiParseRequest,
    current_user: dict = Depends(get_current_user)
):
    """解析 OpenAPI / Swagger 規格 (支援 OAS 2.0, 3.0, 3.1)"""
    try:
        parsed_result = await OpenApiParser.parse(
            spec_content_or_url=request_data.spec_content_or_url,
            default_base_url=request_data.default_base_url
        )
        return {
            "status": "success",
            "data": parsed_result
        }
    except Exception as e:
        logger.error(f"OpenAPI 規格解析失敗: {e}")
        raise HTTPException(status_code=400, detail=f"OpenAPI 規格解析失敗: {str(e)}")
@router.post("/import")
async def import_openapi_tools(
    import_data: OpenApiImportRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """批次匯入選定的 OpenAPI 端點為自訂 AI 工具"""
    imported_count = 0
    updated_count = 0
    global_base_url = import_data.global_base_url
    global_headers = import_data.global_headers or {}
    global_auth_type = import_data.global_auth_type or "none"
    global_auth_config = import_data.global_auth_config or {}
    for item in import_data.tools:
        effective_base = item.base_url or global_base_url or ""
        effective_url = item.full_url
        if effective_base and item.path:
            effective_url = f"{effective_base.rstrip('/')}/{item.path.lstrip('/')}"
        merged_headers = dict(global_headers)
        if item.headers:
            merged_headers.update(item.headers)
        effective_auth_type = item.auth_type if item.auth_type and item.auth_type != "none" else global_auth_type
        effective_auth_config = item.auth_config if item.auth_config else global_auth_config
        existing = db.query(CustomApiTool).filter(CustomApiTool.name == item.name).first()
        if existing:
            existing.display_name = item.display_name
            existing.description = item.description
            existing.method = item.method.upper()
            existing.url = effective_url
            existing.base_url = effective_base
            existing.path = item.path
            existing.headers = json.dumps(merged_headers, ensure_ascii=False) if merged_headers else None
            existing.auth_type = effective_auth_type
            existing.auth_config = json.dumps(effective_auth_config, ensure_ascii=False) if effective_auth_config else None
            existing.parameters_schema = json.dumps(item.parameters_schema, ensure_ascii=False) if item.parameters_schema else None
            existing.request_body_schema = json.dumps(item.request_body_schema, ensure_ascii=False) if item.request_body_schema else None
            existing.param_locations = json.dumps(item.param_locations, ensure_ascii=False) if item.param_locations else None
            existing.spec_version = item.spec_version
            existing.is_enabled = True
            updated_count += 1
        else:
            new_tool = CustomApiTool(
                name=item.name,
                display_name=item.display_name,
                description=item.description,
                method=item.method.upper(),
                url=effective_url,
                base_url=effective_base,
                path=item.path,
                headers=json.dumps(merged_headers, ensure_ascii=False) if merged_headers else None,
                auth_type=effective_auth_type,
                auth_config=json.dumps(effective_auth_config, ensure_ascii=False) if effective_auth_config else None,
                parameters_schema=json.dumps(item.parameters_schema, ensure_ascii=False) if item.parameters_schema else None,
                request_body_schema=json.dumps(item.request_body_schema, ensure_ascii=False) if item.request_body_schema else None,
                param_locations=json.dumps(item.param_locations, ensure_ascii=False) if item.param_locations else None,
                spec_version=item.spec_version,
                is_enabled=True,
                created_by=current_user.get("id") if isinstance(current_user, dict) else getattr(current_user, "id", None)
            )
            db.add(new_tool)
            imported_count += 1
    db.commit()
    return {
        "status": "success",
        "message": f"成功匯入 {imported_count} 個新工具，更新 {updated_count} 個既有工具。",
        "imported": imported_count,
        "updated": updated_count
    }
@router.get("")
async def get_all_api_tools(
    category: Optional[str] = Query(None),
    is_enabled: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """獲取自訂 API 工具清單"""
    query = db.query(CustomApiTool)
    if category:
        query = query.filter(CustomApiTool.category == category)
    if is_enabled is not None:
        query = query.filter(CustomApiTool.is_enabled == is_enabled)
    if search:
        s = f"%{search.strip()}%"
        query = query.filter(
            (CustomApiTool.name.ilike(s)) |
            (CustomApiTool.display_name.ilike(s)) |
            (CustomApiTool.description.ilike(s)) |
            (CustomApiTool.url.ilike(s))
        )
    tools = query.order_by(CustomApiTool.id.desc()).all()
    return {
        "status": "success",
        "total": len(tools),
        "tools": [_serialize_tool_model(t) for t in tools]
    }
@router.post("")
async def create_api_tool(
    tool_data: CustomApiToolCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """手動建立自訂 API 工具"""
    clean_name = OpenApiParser._generate_tool_name(tool_data.method, tool_data.path or tool_data.url, tool_data.name)
    existing = db.query(CustomApiTool).filter(CustomApiTool.name == clean_name).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"已存在同名工具: {clean_name}")
    new_tool = CustomApiTool(
        name=clean_name,
        display_name=tool_data.display_name,
        description=tool_data.description,
        category=tool_data.category or "custom_api",
        method=tool_data.method.upper(),
        url=tool_data.url,
        base_url=tool_data.base_url,
        path=tool_data.path,
        headers=json.dumps(tool_data.headers, ensure_ascii=False) if tool_data.headers else None,
        auth_type=tool_data.auth_type or "none",
        auth_config=json.dumps(tool_data.auth_config, ensure_ascii=False) if tool_data.auth_config else None,
        parameters_schema=json.dumps(tool_data.parameters_schema, ensure_ascii=False) if tool_data.parameters_schema else None,
        request_body_schema=json.dumps(tool_data.request_body_schema, ensure_ascii=False) if tool_data.request_body_schema else None,
        param_locations=json.dumps(tool_data.param_locations, ensure_ascii=False) if tool_data.param_locations else None,
        response_mapping=tool_data.response_mapping,
        is_enabled=tool_data.is_enabled if tool_data.is_enabled is not None else True,
        timeout=tool_data.timeout or 15,
        spec_version=tool_data.spec_version or "manual",
        created_by=current_user.get("id") if isinstance(current_user, dict) else getattr(current_user, "id", None)
    )
    db.add(new_tool)
    db.commit()
    db.refresh(new_tool)
    return {
        "status": "success",
        "message": "自訂 API 工具建立成功",
        "tool": _serialize_tool_model(new_tool)
    }
@router.get("/{tool_id}")
async def get_api_tool_detail(
    tool_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """獲取單一自訂 API 工具詳情"""
    tool = db.query(CustomApiTool).filter(CustomApiTool.id == tool_id).first()
    if not tool:
        raise HTTPException(status_code=404, detail="找不到該自訂 API 工具")
    return {
        "status": "success",
        "tool": _serialize_tool_model(tool)
    }
@router.put("/{tool_id}")
async def update_api_tool(
    tool_id: int,
    tool_data: CustomApiToolUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """更新自訂 API 工具"""
    tool = db.query(CustomApiTool).filter(CustomApiTool.id == tool_id).first()
    if not tool:
        raise HTTPException(status_code=404, detail="找不到該自訂 API 工具")
    if tool_data.display_name is not None:
        tool.display_name = tool_data.display_name
    if tool_data.description is not None:
        tool.description = tool_data.description
    if tool_data.category is not None:
        tool.category = tool_data.category
    if tool_data.method is not None:
        tool.method = tool_data.method.upper()
    if tool_data.url is not None:
        tool.url = tool_data.url
    if tool_data.base_url is not None:
        tool.base_url = tool_data.base_url
    if tool_data.path is not None:
        tool.path = tool_data.path
    if tool_data.headers is not None:
        tool.headers = json.dumps(tool_data.headers, ensure_ascii=False) if tool_data.headers else None
    if tool_data.auth_type is not None:
        tool.auth_type = tool_data.auth_type
    if tool_data.auth_config is not None:
        tool.auth_config = json.dumps(tool_data.auth_config, ensure_ascii=False) if tool_data.auth_config else None
    if tool_data.parameters_schema is not None:
        tool.parameters_schema = json.dumps(tool_data.parameters_schema, ensure_ascii=False) if tool_data.parameters_schema else None
    if tool_data.request_body_schema is not None:
        tool.request_body_schema = json.dumps(tool_data.request_body_schema, ensure_ascii=False) if tool_data.request_body_schema else None
    if tool_data.param_locations is not None:
        tool.param_locations = json.dumps(tool_data.param_locations, ensure_ascii=False) if tool_data.param_locations else None
    if tool_data.is_enabled is not None:
        tool.is_enabled = tool_data.is_enabled
    if tool_data.timeout is not None:
        tool.timeout = tool_data.timeout
    db.commit()
    db.refresh(tool)
    return {
        "status": "success",
        "message": "自訂 API 工具更新成功",
        "tool": _serialize_tool_model(tool)
    }
@router.patch("/{tool_id}/toggle")
async def toggle_api_tool(
    tool_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """切換工具啟用/停用狀態"""
    tool = db.query(CustomApiTool).filter(CustomApiTool.id == tool_id).first()
    if not tool:
        raise HTTPException(status_code=404, detail="找不到該自訂 API 工具")
    tool.is_enabled = not tool.is_enabled
    db.commit()
    db.refresh(tool)
    return {
        "status": "success",
        "is_enabled": tool.is_enabled,
        "message": f"工具已{'啟用' if tool.is_enabled else '停用'}"
    }
@router.delete("/{tool_id}")
async def delete_api_tool(
    tool_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """刪除自訂 API 工具"""
    tool = db.query(CustomApiTool).filter(CustomApiTool.id == tool_id).first()
    if not tool:
        raise HTTPException(status_code=404, detail="找不到該自訂 API 工具")
    db.delete(tool)
    db.commit()
    return {
        "status": "success",
        "message": "自訂 API 工具已成功刪除"
    }
@router.post("/{tool_id}/test")
async def test_api_tool(
    tool_id: int,
    test_data: ToolTestRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """即時測試發送自訂 API 工具請求"""
    tool = db.query(CustomApiTool).filter(CustomApiTool.id == tool_id).first()
    if not tool:
        raise HTTPException(status_code=404, detail="找不到該自訂 API 工具")
    tool_dict = _serialize_tool_model(tool)
    result = await execute_http_api_tool(tool_dict, test_data.arguments or {})
    return {
        "status": "success",
        "tool_name": tool.name,
        "result": result
    }
