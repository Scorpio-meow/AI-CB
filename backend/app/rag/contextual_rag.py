from typing import List, Dict, Any, Optional, Tuple, AsyncGenerator
import os
import pickle
import logging
from datetime import datetime

from .types import Document
from .tokenizers import init_domain_dictionary, HAS_JIEBA
from .indices.vector_store import VectorStoreManager
from .indices.bm25_store import BM25StoreManager
from .retrievers.hybrid import HybridRetriever
from .pipeline import RAGPipeline
from .evaluator import RAGEvaluator

logger = logging.getLogger(__name__)


from app.core.config import settings

class HybridContextualRAG:
    """
    RAG 核心門面（Facade），統整向量檢索、BM25 倒排索引、混合檢索、Cross-Encoder 重排序與生成管線。
    維持 100% 向下相容介面。
    """
    def __init__(self):
        self.chunk_size = settings.CHUNK_SIZE
        self.chunk_overlap = settings.CHUNK_OVERLAP
        self.similarity_threshold = settings.SIMILARITY_THRESHOLD
        self.top_k = settings.TOP_K
        self.rerank_top_k = settings.RERANK_TOP_K
        self.final_k = settings.FINAL_K
        self.rerank_weight = settings.RERANK_WEIGHT
        self.final_threshold = settings.FINAL_THRESHOLD
        self.hybrid_alpha = settings.HYBRID_ALPHA
        self.normalization = settings.NORMALIZATION.lower()
        self.reindex_threshold_hours = settings.REINDEX_HOURS
        self.llm_timeout = settings.LLM_TIMEOUT
        self.model_name = settings.MODEL_NAME or ""
        self.api_base = (settings.LLM_API_BASE or "").strip()
        self.data_dir = settings.DATA_DIR
        self.use_fp16 = settings.USE_FP16_QUANTIZATION
        self.force_cpu = settings.FORCE_CPU
        self.use_faiss_gpu = settings.USE_FAISS_GPU
        self.faiss_gpu_device = settings.FAISS_GPU_DEVICE

        os.makedirs(self.data_dir, exist_ok=True)
        init_domain_dictionary(self.data_dir)


        self.vector_store = VectorStoreManager(
            data_dir=self.data_dir,
            embedding_model=settings.EMBEDDING_MODEL,
            force_cpu=self.force_cpu,
            use_fp16=self.use_fp16,
            use_faiss_gpu=self.use_faiss_gpu,
            faiss_gpu_device=self.faiss_gpu_device,
            similarity_threshold=self.similarity_threshold,
            top_k=self.top_k,
        )


        self.bm25_store = BM25StoreManager(data_dir=self.data_dir)


        self.retriever = HybridRetriever(
            vector_store=self.vector_store,
            bm25_store=self.bm25_store,
            hybrid_alpha=self.hybrid_alpha,
            rerank_top_k=self.rerank_top_k,
            final_k=self.final_k,
            rerank_weight=self.rerank_weight,
            final_threshold=self.final_threshold,
            normalization=self.normalization,
            use_fp16=self.use_fp16,
        )


        self.pipeline = RAGPipeline(
            vector_store=self.vector_store,
            bm25_store=self.bm25_store,
            retriever=self.retriever,
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            llm_timeout=self.llm_timeout,
            model_name=self.model_name,
        )


        self.evaluator = RAGEvaluator(self.retriever)

        logger.info("HybridContextualRAG 門面模組初始化完成")


    @property
    def documents(self) -> List[Document]:
        return self.vector_store.documents

    @documents.setter
    def documents(self, value: List[Document]):
        self.vector_store.documents = value

    @property
    def index(self):
        return self.vector_store.index

    @property
    def embedding_dimension(self) -> int:
        return self.vector_store.embedding_dimension

    @property
    def local_embeddings(self):
        return self.vector_store.local_embeddings

    @property
    def cross_encoder(self):
        return self.retriever.cross_encoder

    @property
    def has_reranker(self) -> bool:
        return self.retriever.has_reranker

    @property
    def context_memory(self):
        return self.pipeline.context_memory

    @property
    def device(self):
        return self.vector_store.device

    @property
    def bm25_index(self):
        return self.bm25_store.bm25_index

    @property
    def bm25_searcher(self):
        return self.bm25_store.bm25_searcher


    def vector_search(self, query: str, top_k: int = None, apply_threshold: bool = True) -> List[Tuple[Document, float]]:
        return self.vector_store.search(query, top_k=top_k, apply_threshold=apply_threshold)

    def bm25_search(self, query: str, top_k: int = None) -> List[Tuple[Document, float]]:
        return self.bm25_store.search(query, self.vector_store.documents, top_k=top_k or self.top_k)

    def hybrid_search(self, query: str, alpha: float = None) -> List[Tuple[Document, float]]:
        return self.retriever.hybrid_search(query, alpha=alpha)

    def rerank_with_cross_encoder(self, query: str, doc_score_pairs: List[Tuple[Document, float]]) -> List[Tuple[Document, float]]:
        return self.retriever.rerank_with_cross_encoder(query, doc_score_pairs)

    def smart_search(self, query: str) -> List[Tuple[Document, float]]:
        return self.retriever.smart_search(query)


    def add_documents(self, documents: List[Document]) -> int:
        return self.pipeline.process_and_add_documents(documents)

    def remove_document_by_id(self, document_id: int, rebuild_bm25: bool = True):
        removed = self.vector_store.remove_document_by_id(document_id)
        if rebuild_bm25 and removed > 0:
            self.bm25_store.rebuild(self.vector_store.documents)

    def clear_vector_store(self):
        self.vector_store.clear()
        self.bm25_store.clear()
        self.pipeline.context_memory.clear()


    async def generate_response(
        self,
        query: str,
        conversation_id: Optional[int] = None,
        model_name: Optional[str] = None,
        user_id: Optional[int] = None,
        reasoning_effort: Optional[str] = "medium"
    ) -> Dict[str, Any]:
        return await self.pipeline.generate_response(
            query=query,
            conversation_id=conversation_id,
            model_name=model_name,
            user_id=user_id,
            reasoning_effort=reasoning_effort
        )

    async def generate_response_stream(
        self,
        query: str,
        conversation_id: Optional[int] = None,
        model_name: Optional[str] = None,
        user_id: Optional[int] = None,
        reasoning_effort: Optional[str] = "medium",
        attachments: Optional[List[Any]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        async for event in self.pipeline.generate_response_stream(
            query=query,
            conversation_id=conversation_id,
            model_name=model_name,
            user_id=user_id,
            reasoning_effort=reasoning_effort,
            attachments=attachments
        ):
            yield event

    def clear_conversation_context(self, conversation_id: int, user_id: Optional[int] = None):
        self.pipeline.clear_conversation_context(conversation_id, user_id)


    def evaluate_retrieval(self, test_queries: List[str], gold_doc_ids: List[List[int]], k_values: List[int] = [1, 3, 5, 10]) -> Dict[str, Any]:
        return self.evaluator.evaluate_retrieval(test_queries, gold_doc_ids, k_values)

    def auto_tune_alpha(self, test_queries: List[str], gold_doc_ids: List[List[int]], alphas: List[float] = None) -> Dict[str, Any]:
        return self.evaluator.auto_tune_alpha(test_queries, gold_doc_ids, alphas)


    def get_statistics(self) -> Dict[str, Any]:
        bm25_status = "Available" if self.bm25_store.bm25_index else "Not Available"
        reranker_status = "Available" if self.retriever.has_reranker else "Not Available"
        return {
            "total_documents": len(self.vector_store.documents),
            "total_conversations": len(self.pipeline.context_memory),
            "total_vectors": self.vector_store.index.ntotal,
            "embedding_dimension": self.vector_store.embedding_dimension,
            "bm25_status": bm25_status,
            "reranker_status": reranker_status,
            "similarity_threshold": self.similarity_threshold,
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
            "last_reindex": self._get_last_reindex_time()
        }

    def _get_last_reindex_time(self) -> Optional[str]:
        try:
            if os.path.exists(self.vector_store.metadata_path):
                with open(self.vector_store.metadata_path, "rb") as f:
                    metadata = pickle.load(f)
                last_reindex = metadata.get("last_reindex")
                if last_reindex and isinstance(last_reindex, datetime):
                    return last_reindex.isoformat()
        except Exception:
            pass
        return None

    def get_vector_store_info(self) -> Dict[str, Any]:
        return {
            "total_vectors": self.vector_store.index.ntotal,
            "total_documents": len(self.vector_store.documents),
            "embedding_dimension": self.vector_store.embedding_dimension,
            "index_type": "FAISS IndexFlatIP + Whoosh BM25",
            "vector_index_exists": os.path.exists(self.vector_store.faiss_index_path),
            "bm25_index_exists": os.path.exists(self.bm25_store.bm25_index_dir),
            "documents_file_exists": os.path.exists(self.vector_store.documents_path),
            "reranker_available": self.retriever.has_reranker,
            "last_reindex": self._get_last_reindex_time(),
            "auto_reindex_hours": self.reindex_threshold_hours
        }

    def force_reindex(self):
        logger.info("Forcing reindex...")
        if self.vector_store.documents:
            docs = list(self.vector_store.documents)
            self.clear_vector_store()
            self.add_documents(docs)
        return True


ContextualRAG = HybridContextualRAG