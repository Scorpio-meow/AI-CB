
import logging
import threading
from typing import Optional
from app.rag.contextual_rag import HybridContextualRAG
logger = logging.getLogger(__name__)
class RAGManager:
    _instance: Optional[HybridContextualRAG] = None
    _lock = threading.Lock()
    _initialized = False
    @classmethod
    def get_instance(cls) -> HybridContextualRAG:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    logger.info("Initializing global RAG instance...")
                    cls._instance = HybridContextualRAG()
                    cls._initialized = True
                    logger.info("Global RAG instance initialized successfully")
        return cls._instance
    @classmethod
    def reset_instance(cls):
        with cls._lock:
            if cls._instance is not None:
                logger.warning("Resetting global RAG instance...")
                cls._instance = None
                cls._initialized = False
                logger.info("Global RAG instance reset complete")
    @classmethod
    def is_initialized(cls) -> bool:
        return cls._initialized
def get_rag_system() -> HybridContextualRAG:
    return RAGManager.get_instance()
