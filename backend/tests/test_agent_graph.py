import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.agent_graph import build_agent_graph, AgentState
from langgraph.checkpoint.memory import MemorySaver

@pytest.mark.anyio
async def test_agent_graph_execution(mocker):
    # Mock LLM provider
    mock_provider = AsyncMock()
    # 模擬規劃器生成、寫作者生成、審查者審查（包含 'PASS' 表示通過）
    mock_provider.chat_with_tools.side_effect = [
        "Plan steps",       # planner output
        "Written content",  # writer output
        "Content is good: PASS"  # reviewer output
    ]
    mocker.patch("app.services.agent_graph.get_llm_provider", return_value=mock_provider)
    
    graph = build_agent_graph()
    
    initial_state = {
        "messages": [],
        "task": "Test Graph task",
        "node_id_map": {},
        "current_node": "",
        "final_result": None,
        "reviewer_approved": False,
        "review_comments": None
    }
    
    # 執行 Graph (無 checkpointer)
    result = await graph.ainvoke(initial_state)
    
    # 驗證狀態機是否成功執行到終點並且通過審查
    assert result["current_node"] == "reviewer_node"
    assert result["reviewer_approved"] is True
    assert result["final_result"] == "Written content"
