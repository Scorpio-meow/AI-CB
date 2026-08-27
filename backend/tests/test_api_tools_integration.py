import pytest
import anyio
from app.models.database import Base, engine, SessionLocal
from app.models import CustomApiTool
from app.services.openapi_parser import OpenApiParser
from app.rag.tools import ResearchToolRegistry
from app.api.api_tools import execute_http_api_tool, _serialize_tool_model
@pytest.mark.anyio
async def test_custom_api_tools_lifecycle():
    Base.metadata.create_all(bind=engine)
    oas2_yaml = """
swagger: '2.0'
info:
  title: Test Weather API
  version: 1.0.0
host: httpbin.org
basePath: /
schemes:
  - https
paths:
  /get:
    get:
      summary: Get weather by city
      operationId: getWeatherByCity
      parameters:
        - name: city
          in: query
          required: true
          type: string
"""
    parsed = await OpenApiParser.parse(oas2_yaml)
    assert len(parsed["endpoints"]) == 1
    endpoint = parsed["endpoints"][0]
    db = SessionLocal()
    db.query(CustomApiTool).filter(CustomApiTool.name == endpoint["name"]).delete()
    db.commit()
    import json
    new_tool = CustomApiTool(
        name=endpoint["name"],
        display_name=endpoint["display_name"],
        description=endpoint["description"],
        method=endpoint["method"],
        url=endpoint["full_url"],
        base_url=endpoint["base_url"],
        path=endpoint["path"],
        parameters_schema=json.dumps(endpoint["parameters_schema"]),
        param_locations=json.dumps(endpoint["param_locations"]),
        is_enabled=True,
        spec_version=endpoint["spec_version"]
    )
    db.add(new_tool)
    db.commit()
    db.refresh(new_tool)
    registry = ResearchToolRegistry()
    defs = registry.get_tool_definitions()
    tool_names = [t["function"]["name"] for t in defs]
    assert endpoint["name"] in tool_names
    tool_dict = _serialize_tool_model(new_tool)
    res = await execute_http_api_tool(tool_dict, {"city": "Taipei"})
    assert res["status_code"] == 200
    assert res["is_success"] is True
    assert "Taipei" in str(res["data"])
    new_tool.is_enabled = False
    db.commit()
    defs_after = registry.get_tool_definitions()
    tool_names_after = [t["function"]["name"] for t in defs_after]
    assert endpoint["name"] not in tool_names_after
    db.delete(new_tool)
    db.commit()
    db.close()
    print("Custom API Tools 完整生命週期測試通過！")