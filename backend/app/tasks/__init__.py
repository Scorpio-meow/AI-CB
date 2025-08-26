# RAG 後台任務模組

# 導入所有任務以確保它們被 Celery 註冊
from .rag_tasks import add_documents_task

__all__ = ['add_documents_task']
