import json
import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.models.database import get_db
from app.models import (
    McpServer,
    McpServerCreate,
    McpServerUpdate,
    McpServerResponse,
    McpToolTestRequest,
)
from app.core.jwt_auth import get_current_active_user as get_current_user
from app.services.mcp_service import McpManager
logger = logging.getLogger(__name__)
router = APIRouter()
def _serialize_mcp_server(server: McpServer) -> Dict[str, Any]:
    """序列化 McpServer 模型為 Dict"""
    args = []
    if server.args:
        try:
            args = json.loads(server.args)
        except Exception:
            args = [server.args]
    env_vars = {}
    if server.env_vars:
        try:
            env_vars = json.loads(server.env_vars)
        except Exception:
            env_vars = {}
    headers = {}
    if server.headers:
        try:
            headers = json.loads(server.headers)
        except Exception:
            headers = {}
    discovered_tools = []
    if server.discovered_tools:
        try:
            discovered_tools = json.loads(server.discovered_tools)
        except Exception:
            discovered_tools = []
    return {
        "id": server.id,
        "name": server.name,
        "display_name": server.display_name,
        "description": server.description,
        "transport_type": server.transport_type,
        "command": server.command,
        "args": args,
        "env_vars": env_vars,
        "url": server.url,
        "headers": headers,
        "is_enabled": bool(server.is_enabled),
        "status": server.status,
        "last_error": server.last_error,
        "discovered_tools": discovered_tools,
        "timeout": server.timeout or 30,
        "created_at": server.created_at,
        "updated_at": server.updated_at,
    }
@router.get("/presets")
async def get_preset_servers(current_user: dict = Depends(get_current_user)):
    """獲取常用官方與社群 MCP 伺服器範本"""
    return {
        "status": "success",
        "presets": McpManager.get_preset_servers()
    }
@router.get("/servers")
async def get_all_servers(
    is_enabled: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """獲取所有已配置的 MCP 伺服器清單"""
    query = db.query(McpServer)
    if is_enabled is not None:
        query = query.filter(McpServer.is_enabled == is_enabled)
    servers = query.order_by(McpServer.id.desc()).all()
    return {
        "status": "success",
        "total": len(servers),
        "servers": [_serialize_mcp_server(s) for s in servers]
    }
@router.post("/servers")
async def create_server(
    server_data: McpServerCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """新增 MCP 伺服器配置"""
    clean_name = server_data.name.strip().lower()
    existing = db.query(McpServer).filter(McpServer.name == clean_name).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"已存在同名 MCP 伺服器: {clean_name}")
    new_server = McpServer(
        name=clean_name,
        display_name=server_data.display_name,
        description=server_data.description,
        transport_type=server_data.transport_type or "stdio",
        command=server_data.command,
        args=json.dumps(server_data.args, ensure_ascii=False) if server_data.args else None,
        env_vars=json.dumps(server_data.env_vars, ensure_ascii=False) if server_data.env_vars else None,
        url=server_data.url,
        headers=json.dumps(server_data.headers, ensure_ascii=False) if server_data.headers else None,
        is_enabled=server_data.is_enabled if server_data.is_enabled is not None else True,
        timeout=server_data.timeout or 30,
        status="disconnected",
        created_by=current_user.get("id") if isinstance(current_user, dict) else getattr(current_user, "id", None)
    )
    db.add(new_server)
    db.commit()
    db.refresh(new_server)
    try:
        server_dict = _serialize_mcp_server(new_server)
        tools, init_info = await McpManager.discover_server_tools(server_dict)
        new_server.discovered_tools = json.dumps(tools, ensure_ascii=False)
        new_server.status = "connected"
        new_server.last_error = None
        db.commit()
        db.refresh(new_server)
    except Exception as e:
        logger.warning(f"初次探索 MCP 工具失敗: {e}")
        new_server.status = "error"
        new_server.last_error = str(e)
        db.commit()
        db.refresh(new_server)
    return {
        "status": "success",
        "message": "MCP 伺服器建立成功",
        "server": _serialize_mcp_server(new_server)
    }
@router.get("/servers/{server_id}")
async def get_server_detail(
    server_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """獲取單一 MCP 伺服器詳情"""
    server = db.query(McpServer).filter(McpServer.id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="找不到該 MCP 伺服器")
    return {
        "status": "success",
        "server": _serialize_mcp_server(server)
    }
@router.put("/servers/{server_id}")
async def update_server(
    server_id: int,
    server_data: McpServerUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """更新 MCP 伺服器配置"""
    server = db.query(McpServer).filter(McpServer.id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="找不到該 MCP 伺服器")
    if server_data.display_name is not None:
        server.display_name = server_data.display_name
    if server_data.description is not None:
        server.description = server_data.description
    if server_data.transport_type is not None:
        server.transport_type = server_data.transport_type
    if server_data.command is not None:
        server.command = server_data.command
    if server_data.args is not None:
        server.args = json.dumps(server_data.args, ensure_ascii=False)
    if server_data.env_vars is not None:
        server.env_vars = json.dumps(server_data.env_vars, ensure_ascii=False)
    if server_data.url is not None:
        server.url = server_data.url
    if server_data.headers is not None:
        server.headers = json.dumps(server_data.headers, ensure_ascii=False)
    if server_data.is_enabled is not None:
        server.is_enabled = server_data.is_enabled
    if server_data.timeout is not None:
        server.timeout = server_data.timeout
    db.commit()
    db.refresh(server)
    return {
        "status": "success",
        "message": "MCP 伺服器配置更新成功",
        "server": _serialize_mcp_server(server)
    }
@router.delete("/servers/{server_id}")
async def delete_server(
    server_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """刪除 MCP 伺服器配置"""
    server = db.query(McpServer).filter(McpServer.id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="找不到該 MCP 伺服器")
    db.delete(server)
    db.commit()
    return {
        "status": "success",
        "message": "MCP 伺服器已成功刪除"
    }
@router.post("/servers/{server_id}/discover")
async def discover_server_tools(
    server_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """即時連線並探索 MCP 伺服器提供的所有工具 (tools/list)"""
    server = db.query(McpServer).filter(McpServer.id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="找不到該 MCP 伺服器")
    server_dict = _serialize_mcp_server(server)
    try:
        tools, init_info = await McpManager.discover_server_tools(server_dict)
        server.discovered_tools = json.dumps(tools, ensure_ascii=False)
        server.status = "connected"
        server.last_error = None
        db.commit()
        db.refresh(server)
        return {
            "status": "success",
            "message": f"成功連線並探索到 {len(tools)} 項 MCP 工具",
            "tools_count": len(tools),
            "tools": tools,
            "init_info": init_info,
            "server": _serialize_mcp_server(server)
        }
    except Exception as e:
        logger.error(f"探索 MCP 伺服器工具失敗: {e}")
        server.status = "error"
        server.last_error = str(e)
        db.commit()
        db.refresh(server)
        raise HTTPException(status_code=400, detail=f"連線與探索 MCP 工具失敗: {str(e)}")
@router.patch("/servers/{server_id}/toggle")
async def toggle_server(
    server_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """切換 MCP 伺服器啟用狀態"""
    server = db.query(McpServer).filter(McpServer.id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="找不到該 MCP 伺服器")
    server.is_enabled = not server.is_enabled
    db.commit()
    db.refresh(server)
    return {
        "status": "success",
        "is_enabled": server.is_enabled,
        "message": f"MCP 伺服器已{'啟用' if server.is_enabled else '停用'}"
    }
@router.post("/servers/{server_id}/tools/{tool_name}/test")
async def test_mcp_tool(
    server_id: int,
    tool_name: str,
    test_data: McpToolTestRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """即時線上測試特定 MCP 工具調用 (tools/call)"""
    server = db.query(McpServer).filter(McpServer.id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="找不到該 MCP 伺服器")
    server_dict = _serialize_mcp_server(server)
    result = await McpManager.execute_mcp_tool(server_dict, tool_name, test_data.arguments or {})
    return {
        "status": "success",
        "server_name": server.name,
        "tool_name": tool_name,
        "result": result
    }