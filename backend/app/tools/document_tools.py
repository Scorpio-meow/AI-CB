import anyio
from pydantic import BaseModel, Field
from typing import List, Dict, Any
from app.tools.registry import register_tool
from app.core.rag_manager import get_rag_system

class SearchDocumentsArgs(BaseModel):
    query: str = Field(..., description="要檢索與搜尋的關鍵字或句子")
    top_k: int = Field(5, description="要返回的最相關文檔數量")

@register_tool(
    name="search_documents",
    description="在知識庫與文檔庫中進行混合檢索，返回與查詢最相關的文本段落與資訊",
    args_schema=SearchDocumentsArgs
)
async def search_documents_tool(query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """
    RAG 混合檢索工具。
    在進行 RAG 回答時，可供 LLM 呼叫以檢索相關背景文件。
    """
    def run_search():
        rag = get_rag_system()
        # 呼叫 Hybrid RAG 的 smart_search
        results = rag.smart_search(query)
        # 取 top_k 個結果
        sliced = results[:top_k]
        formatted = []
        for doc, score in sliced:
            formatted.append({
                "content": doc.page_content,
                "metadata": doc.metadata,
                "score": float(score)
            })
        return formatted

    # 在 thread-pool 中異步執行同步的搜尋操作，防止阻塞 event loop
    return await anyio.to_thread.run_sync(run_search)
