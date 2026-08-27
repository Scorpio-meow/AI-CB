import pytest
from app.rag.types import Document
from app.rag.tools import ResearchToolRegistry
from app.rag.agent import ResearchAgent
class MockRetriever:
    def __init__(self):
        self.last_retrieval_strategy = "mock_hybrid"
    def smart_search(self, query: str):
        doc1 = Document(
            page_content="員工特休假每年依年資計算，滿半年享3天，滿一年享7天特休。",
            metadata={"source": "勞工休假辦法.pdf", "chunk_index": 1}
        )
        doc2 = Document(
            page_content="加班應事先於系統填寫加班申請單，經主管核准後生效。",
            metadata={"source": "加班管理辦法.pdf", "chunk_index": 0}
        )
        return [(doc1, 0.95), (doc2, 0.82)]
@pytest.mark.asyncio
async def test_research_tool_registry():
    retriever = MockRetriever()
    registry = ResearchToolRegistry(retriever=retriever)
    
    tools_def = registry.get_tool_definitions()
    assert len(tools_def) == 4
    tool_names = [t["function"]["name"] for t in tools_def]
    assert "search_knowledge_base" in tool_names
    assert "filter_and_count_records" in tool_names
    assert "web_search" in tool_names
    assert "web_fetch" in tool_names
    res = await registry.execute_tool("search_knowledge_base", {"query": "特休規定", "top_k": 2})
    assert res["total_found"] == 2
    assert len(res["documents"]) == 2
    assert res["documents"][0]["source"] == "勞工休假辦法.pdf"
    assert res["documents"][0]["score"] == 0.95
@pytest.mark.asyncio
async def test_research_agent_run():
    retriever = MockRetriever()
    registry = ResearchToolRegistry(retriever=retriever)
    agent = ResearchAgent(tool_registry=registry)
    result = await agent.run_research(
        query="請幫我查詢特休規定",
        model_name="gpt-5.6-luna",
        max_turns=2
    )
    assert "answer" in result
    assert "sources" in result
    assert "sources_detail" in result
    assert "research_trace" in result
    assert "retrieval_strategy" in result