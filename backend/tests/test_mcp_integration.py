import pytest
import anyio
import json
from app.models.database import Base, engine, SessionLocal
from app.models import McpServer
from app.services.mcp_service import McpManager
from app.rag.tools import ResearchToolRegistry
from app.api.mcp import _serialize_mcp_server
@pytest.mark.anyio
async def test_mcp_stdio_lifecycle():
    Base.metadata.create_all(bind=engine)
    presets = McpManager.get_preset_servers()
    time_preset = next(p for p in presets if p["name"] == "mcp_time")
    tools, init_info = await McpManager.discover_server_tools(time_preset)
    assert len(tools) >= 1
    assert tools[0]["name"] == "get_current_time"
    assert init_info.get("protocolVersion") == "2024-11-05"
    call_res = await McpManager.execute_mcp_tool(
        time_preset,
        "get_current_time",
        {"timezone": "Asia/Taipei"}
    )
    assert call_res["is_success"] is True
    assert len(call_res["content"]) >= 1
    assert "當前時間" in call_res["content"][0]["text"]
    db = SessionLocal()
    db.query(McpServer).filter(McpServer.name == "mcp_time_test").delete()
    db.commit()
    server = McpServer(
        name="mcp_time_test",
        display_name="測試時間伺服器",
        description="提供時間查詢",
        transport_type="stdio",
        command=time_preset["command"],
        args=json.dumps(time_preset["args"], ensure_ascii=False),
        discovered_tools=json.dumps(tools, ensure_ascii=False),
        is_enabled=True,
        status="connected"
    )
    db.add(server)
    db.commit()
    db.refresh(server)
    registry = ResearchToolRegistry()
    defs = registry.get_tool_definitions()
    tool_names = [t["function"]["name"] for t in defs]
    expected_tool_name = "mcp_mcp_time_test_get_current_time"
    assert expected_tool_name in tool_names
    exec_res = await registry.execute_tool(expected_tool_name, {"timezone": "UTC"})
    assert exec_res["is_success"] is True
    assert "當前時間" in exec_res["content"][0]["text"]
    db.delete(server)
    db.commit()
    db.close()
    print("MCP 完整生命週期與調用測試順利通過！")