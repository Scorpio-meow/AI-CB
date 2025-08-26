from app.celery_app import celery_app
from app.rag.contextual_rag import HybridContextualRAG
from langchain.schema import Document as LangchainDocument
import os
import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

# create a rag instance per worker process
rag_system = HybridContextualRAG()

# ThreadPool for running blocking operations when needed
_executor = ThreadPoolExecutor(max_workers=2)


@celery_app.task(bind=True)
def add_documents_task(self, docs: list):
    """Celery task to add documents to RAG. docs is a list of dicts with keys page_content and metadata."""
    try:
        lc_docs = [LangchainDocument(page_content=d['page_content'], metadata=d['metadata']) for d in docs]
        # add_documents is async in the RAG implementation; run in event loop
        try:
            result = asyncio.run(rag_system.add_documents(lc_docs))
            return {'status': 'ok', 'added': result}
        except Exception as e:
            logger.exception(f"Async add_documents failed: {e}")
            return {'status': 'error', 'error': str(e)}
    except Exception as e:
        logger.exception(f"add_documents_task failed: {e}")
        return {'status': 'error', 'error': str(e)}


@celery_app.task(bind=True)
def force_reindex_task(self):
    try:
        # run blocking rebuild in a thread to avoid blocking worker's event loop
        fut = _executor.submit(rag_system.force_reindex)
        res = fut.result()
        return {'status': 'ok', 'result': res}
    except Exception as e:
        logger.exception(f"force_reindex_task failed: {e}")
        return {'status': 'error', 'error': str(e)}


@celery_app.task(bind=True)
def remove_document_task(self, document_id: int):
    try:
        fut = _executor.submit(rag_system.remove_document_by_id, document_id)
        fut.result()
        return {'status': 'ok'}
    except Exception as e:
        logger.exception(f"remove_document_task failed: {e}")
        return {'status': 'error', 'error': str(e)}
