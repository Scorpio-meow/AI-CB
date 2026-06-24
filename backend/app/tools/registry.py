import logging
from typing import Callable, Type, Dict, List, Any
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# 全域工具註冊表與 Schema 清單
TOOL_REGISTRY: Dict[str, Callable] = {}
TOOL_SCHEMAS: List[Dict[str, Any]] = []

def _clean_schema(schema: dict) -> dict:
    """
    遞迴移除 Pydantic 自動生成的 title 欄位。
    OpenAI 可接受 title，但 Ollama 部分模型會拒絕包含 title 詮釋資料的 Schema。
    """
    cleaned = schema.copy()
    cleaned.pop("title", None)
    
    # 清洗 properties
    if "properties" in cleaned:
        new_properties = {}
        for k, v in cleaned["properties"].items():
            if isinstance(v, dict):
                # 遞迴清洗子屬性
                new_properties[k] = _clean_schema(v)
            else:
                new_properties[k] = v
        cleaned["properties"] = new_properties
        
    # 清洗 Pydantic v2 的 $defs 或 Pydantic v1 的 definitions
    for defs_key in ("$defs", "definitions"):
        if defs_key in cleaned:
            new_defs = {}
            for k, v in cleaned[defs_key].items():
                if isinstance(v, dict):
                    new_defs[k] = _clean_schema(v)
                else:
                    new_defs[k] = v
            cleaned[defs_key] = new_defs
            
    # 清洗 items (針對 array 型態)
    if "items" in cleaned and isinstance(cleaned["items"], dict):
        cleaned["items"] = _clean_schema(cleaned["items"])
        
    return cleaned

def register_tool(name: str, description: str, args_schema: Type[BaseModel]):
    """
    工具註冊裝飾器。
    
    :param name: 工具名稱 (必須唯一，只包含字母、數字、底線)
    :param description: 工具用途描述，供 LLM 判斷何時呼叫
    :param args_schema: 繼承自 Pydantic BaseModel 的引數規格類別
    """
    def decorator(fn: Callable):
        if name in TOOL_REGISTRY:
            logger.warning(f"工具 '{name}' 已存在註冊表，將會進行覆蓋。")
            
        raw_schema = args_schema.model_json_schema()
        cleaned_schema = _clean_schema(raw_schema)
        
        TOOL_REGISTRY[name] = fn
        
        # 移除已有的同名 schema (覆蓋用)
        global TOOL_SCHEMAS
        TOOL_SCHEMAS = [s for s in TOOL_SCHEMAS if s["function"]["name"] != name]
        
        TOOL_SCHEMAS.append({
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": cleaned_schema
            }
        })
        logger.info(f"成功註冊工具: {name} ({description})")
        return fn
    return decorator
