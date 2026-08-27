from typing import List, Dict, Any, Optional, Tuple, AsyncGenerator
import os
import time
import logging
from datetime import datetime
import httpx
from .types import Document, RecursiveCharacterTextSplitter
from app.core.llm_client import call_llm
from .indices.vector_store import VectorStoreManager
from .indices.bm25_store import BM25StoreManager
from .retrievers.hybrid import HybridRetriever

from .tools import ResearchToolRegistry
from .agent import ResearchAgent
from app.core.config import settings

logger = logging.getLogger(__name__)


class RAGPipeline:
    def __init__(
        self,
        vector_store: VectorStoreManager,
        bm25_store: BM25StoreManager,
        retriever: HybridRetriever,
        chunk_size: int = 300,
        chunk_overlap: int = 100,
        llm_timeout: int = 120,
        model_name: Optional[str] = None,
    ):
        self.vector_store = vector_store
        self.bm25_store = bm25_store
        self.retriever = retriever
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.llm_timeout = llm_timeout
        self.model_name = model_name or settings.MODEL_NAME or ""
        self.context_memory: Dict[str, List[Dict[str, Any]]] = {}

        self.tool_registry = ResearchToolRegistry(retriever=self.retriever)
        self.agent = ResearchAgent(tool_registry=self.tool_registry)

        self.text_splitter = self._create_text_splitter()

    def _create_text_splitter(self) -> RecursiveCharacterTextSplitter:
        separators = [
            "\n\n---\n\n",
            "\n\n",
            "\n",
            "。", "！", "？", "；", "：", "，",
            ". ", "! ", "? ", ", ",
            " ", ""
        ]
        return RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            length_function=len,
            separators=separators,
        )

    def process_and_add_documents(self, raw_documents: List[Document]) -> int:
        if not raw_documents:
            return 0

        all_chunks: List[Document] = []
        for doc in raw_documents:
            if doc.metadata.get("preserve_whole", False):
                chunk_doc = Document(
                    page_content=doc.page_content,
                    metadata={
                        **doc.metadata,
                        "chunk_id": f"{doc.metadata.get('source', 'unknown')}_0",
                        "chunk_index": 0,
                        "original_doc_id": doc.metadata.get("document_id"),
                        "added_timestamp": datetime.now().isoformat()
                    }
                )
                all_chunks.append(chunk_doc)
            else:
                chunks = self.text_splitter.split_text(doc.page_content)
                for i, chunk in enumerate(chunks):
                    chunk_doc = Document(
                        page_content=chunk,
                        metadata={
                            **doc.metadata,
                            "chunk_id": f"{doc.metadata.get('source', 'unknown')}_{i}",
                            "chunk_index": i,
                            "original_doc_id": doc.metadata.get("document_id"),
                            "added_timestamp": datetime.now().isoformat()
                        }
                    )
                    all_chunks.append(chunk_doc)

        if not all_chunks:
            return 0

        start_id = len(self.vector_store.documents)
        added_count = self.vector_store.add_documents(all_chunks)
        self.bm25_store.add_documents(all_chunks, start_id=start_id)

        logger.info(f"Added {added_count} chunks. Total vectors: {self.vector_store.index.ntotal}")
        return added_count

    def build_context_prompt(
        self,
        query: str,
        relevant_docs: List[Document],
        conversation_id: Optional[int] = None,
        user_id: Optional[int] = None
    ) -> Tuple[str, List[Dict[str, str]]]:
        conversation_history: List[Dict[str, str]] = []
        if conversation_id is not None:
            key = f"{user_id}:{conversation_id}" if user_id is not None else f"{conversation_id}"
            if key in self.context_memory:
                recent_context = self.context_memory[key][-3:]
                for exchange in recent_context:
                    conversation_history.append({"role": "user", "content": exchange["user"]})
                    conversation_history.append({"role": "assistant", "content": exchange["assistant"]})

        document_context = ""
        max_docs = min(len(relevant_docs), 5)
        for i, doc in enumerate(relevant_docs[:max_docs]):
            source = doc.metadata.get("source", "未知來源")
            chunk_id = doc.metadata.get("chunk_index", 0)
            document_context += f"文檔 [{i+1}] (來源: {source}, 段落: {chunk_id}):\n{doc.page_content}\n\n"

        user_prompt = f"""用戶問題: {query}
檔案片段:
{document_context}"""
        return user_prompt, conversation_history

    async def call_llm_api(
        self,
        prompt: str,
        model_name: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        reasoning_effort: Optional[str] = None
    ) -> str:
        model_to_use = model_name or self.model_name
        try:
            messages = [
                {
                    "role": "system",
                    "content": """你是一個具備自主研究能力的智慧知識助理「AskMiao」，負責根據用戶問題、對話上下文與檔案片段，產出準確、客觀且可追溯的繁體中文回答。
規則：
1) 以繁體中文回答問題。
2) 在回答末尾列出使用到的來源，格式為："[n] 來源名稱 (段落: m)"。若來源未知請標示為「無來源」。
3) 避免編造事實；若資料不足或為推論，請在回覆中明確標註「推論」或回報「無法確定」，並建議下一步可查詢的關鍵字或資料位置。
4) 回應中不得包含任何系統內部實作細節、索引 id 或未經驗證的 URL。"""
                }
            ]

            if conversation_history:
                messages.extend(conversation_history)

            messages.append({"role": "user", "content": prompt})

            response_text = await call_llm(
                messages,
                model_name=model_to_use,
                timeout=self.llm_timeout,
                reasoning_effort=reasoning_effort
            )
            if response_text:
                logger.info(f"LLM response received: {len(response_text)} chars")
                return response_text
            else:
                logger.warning("LLM returned empty response")
                return "抱歉，模型沒有返回有效回應。"

        except httpx.TimeoutException:
            logger.error(f"LLM API timeout after {self.llm_timeout}s for model {model_to_use}")
            return f"抱歉，請求超時 ({self.llm_timeout}秒)。請嘗試使用較小的模型或稍後再試。"
        except httpx.RequestError as e:
            logger.error(f"LLM API network error: {e}")
            return "抱歉，無法連接到語言模型服務。請檢查網路連接。"
        except httpx.HTTPStatusError as e:
            status_code = e.response.status_code if e.response else "unknown"
            error_detail = ""
            try:
                error_detail = e.response.text if e.response else ""
            except Exception:
                pass
            logger.error(f"LLM API HTTP error {status_code}: {e}, detail: {error_detail[:200]}")
            if status_code == 500:
                return f"抱歉，模型服務器錯誤 (500)。可能是模型 '{model_to_use}' 負載過重，建議切換到較小的模型。"
            return f"抱歉，模型 API 返回錯誤 ({status_code}): {str(e)}"
        except Exception as e:
            logger.error(f"LLM API unexpected error: {type(e).__name__}: {e}")
            return f"抱歉，生成回應時出現錯誤: {str(e)}"

    async def generate_response(
        self,
        query: str,
        conversation_id: Optional[int] = None,
        model_name: Optional[str] = None,
        user_id: Optional[int] = None,
        reasoning_effort: Optional[str] = "medium"
    ) -> Dict[str, Any]:
        start_time = time.time()


        history_msgs = []
        if conversation_id is not None:
            key = f"{user_id}:{conversation_id}" if user_id is not None else f"{conversation_id}"
            if key in self.context_memory:
                for item in self.context_memory[key]:
                    if item.get("user"):
                        history_msgs.append({"role": "user", "content": item.get("user")})
                    if item.get("assistant"):
                        history_msgs.append({"role": "assistant", "content": item.get("assistant")})


        research_result = await self.agent.run_research(
            query=query,
            model_name=model_name or self.model_name,
            conversation_history=history_msgs,
            reasoning_effort=reasoning_effort
        )

        answer = research_result.get("answer", "")
        sources = research_result.get("sources", [])
        sources_detail = research_result.get("sources_detail", [])
        research_trace = research_result.get("research_trace", [])


        if not answer:
            doc_score_pairs = self.retriever.smart_search(query)
            relevant_docs = [doc for doc, _ in doc_score_pairs]
            user_prompt, conv_hist = self.build_context_prompt(
                query, relevant_docs, conversation_id, user_id
            )
            answer = await self.call_llm_api(user_prompt, model_name, conv_hist, reasoning_effort=reasoning_effort)
            if not sources:
                sources = [doc.metadata.get("source", "內部文件") for doc in relevant_docs[:3]]
                sources_detail = [
                    {
                        "source": doc.metadata.get("source", "內部文件"),
                        "chunk": doc.metadata.get("chunk_index", 0),
                        "score": round(float(doc_score_pairs[i][1]), 4) if i < len(doc_score_pairs) else None,
                        "snippet": doc.page_content[:200]
                    }
                    for i, doc in enumerate(relevant_docs[:3])
                ]


        if conversation_id is not None:
            key = f"{user_id}:{conversation_id}" if user_id is not None else f"{conversation_id}"
            if key not in self.context_memory:
                self.context_memory[key] = []
            self.context_memory[key].append({
                "user": query,
                "assistant": answer,
                "timestamp": time.time(),
                "sources": sources,
            })
            if len(self.context_memory[key]) > 10:
                self.context_memory[key] = self.context_memory[key][-10:]

        return {
            "answer": answer,
            "context_used": len(sources_detail),
            "sources": sources,
            "sources_detail": sources_detail,
            "research_trace": research_trace,
            "total_time": round(time.time() - start_time, 2),
            "retrieval_strategy": research_result.get("retrieval_strategy", "agentic_research")
        }

    async def generate_response_stream(
        self,
        query: str,
        conversation_id: Optional[int] = None,
        model_name: Optional[str] = None,
        user_id: Optional[int] = None,
        reasoning_effort: Optional[str] = "medium",
        attachments: Optional[List[Any]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """非同步生成器：向 API 層提供研究步驟與回答文字串流"""
        history_msgs = []
        if conversation_id is not None:
            key = f"{user_id}:{conversation_id}" if user_id is not None else f"{conversation_id}"
            if key in self.context_memory:
                for item in self.context_memory[key]:
                    if item.get("user"):
                        history_msgs.append({"role": "user", "content": item.get("user")})
                    if item.get("assistant"):
                        history_msgs.append({"role": "assistant", "content": item.get("assistant")})

        final_answer = ""
        final_sources = []

        async for event_item in self.agent.stream_research(
            query=query,
            model_name=model_name or self.model_name,
            conversation_history=history_msgs,
            reasoning_effort=reasoning_effort,
            attachments=attachments
        ):
            ev = event_item.get("event")
            data = event_item.get("data", {})
            if ev == "token":
                final_answer += data.get("content", "")
            elif ev == "sources":
                final_sources = data.get("sources", [])
            elif ev == "done":
                if not final_answer:
                    final_answer = data.get("answer", "")
                if not final_sources:
                    final_sources = data.get("sources", [])

            yield event_item


        if conversation_id is not None and final_answer:
            key = f"{user_id}:{conversation_id}" if user_id is not None else f"{conversation_id}"
            if key not in self.context_memory:
                self.context_memory[key] = []
            self.context_memory[key].append({
                "user": query,
                "assistant": final_answer,
                "timestamp": time.time(),
                "sources": final_sources,
            })
            if len(self.context_memory[key]) > 10:
                self.context_memory[key] = self.context_memory[key][-10:]

    def clear_conversation_context(self, conversation_id: int, user_id: Optional[int] = None) -> None:
        key = f"{user_id}:{conversation_id}" if user_id is not None else f"{conversation_id}"
        if key in self.context_memory:
            del self.context_memory[key]
        elif str(conversation_id) in self.context_memory:
            del self.context_memory[str(conversation_id)]
        logger.info(f"Cleared context for conversation {conversation_id}")
