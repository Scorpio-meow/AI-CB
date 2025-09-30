"""
Global RAG Manager - Singleton pattern to ensure only one RAG instance across the application.
This prevents memory waste and index synchronization issues.
"""
import logging
import threading
from typing import Optional
from app.rag.contextual_rag import HybridContextualRAG

logger = logging.getLogger(__name__)


class RAGManager:
    """
    Singleton RAG Manager to ensure only one RAG instance exists across the application.
    Thread-safe implementation using double-checked locking pattern.
    """
    _instance: Optional[HybridContextualRAG] = None
    _lock = threading.Lock()
    _initialized = False

    @classmethod
    def get_instance(cls) -> HybridContextualRAG:
        """
        Get the singleton RAG instance. Creates it on first call.
        Thread-safe using double-checked locking.
        """
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
        """
        Reset the singleton instance (useful for testing or forced reinitialization).
        Warning: This should rarely be used in production.
        """
        with cls._lock:
            if cls._instance is not None:
                logger.warning("Resetting global RAG instance...")
                cls._instance = None
                cls._initialized = False
                logger.info("Global RAG instance reset complete")

    @classmethod
    def is_initialized(cls) -> bool:
        """Check if RAG instance has been initialized."""
        return cls._initialized


# Convenience function for easy access
def get_rag_system() -> HybridContextualRAG:
    """
    Get the global RAG system instance.
    
    Returns:
        HybridContextualRAG: The singleton RAG instance
    """
    return RAGManager.get_instance()
