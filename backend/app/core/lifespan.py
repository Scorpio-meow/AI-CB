import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.core.config import settings
from app.models.database import create_tables
from app.tasks.uploads_watcher import scan_and_cleanup_uploads
from app.tasks.index_rebuilder import start_index_rebuilder
from app.core.rag_manager import get_rag_system
logger = logging.getLogger(__name__)
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting ChatBot application...")
    
    await create_tables()
    
    logger.info("Initializing global RAG system...")
    rag_system = get_rag_system()
    logger.info(f"RAG system initialized: {rag_system.get_vector_store_info()}")
    
    uploads_watcher_task = asyncio.create_task(
        scan_and_cleanup_uploads(settings.UPLOADS_WATCHER_INTERVAL)
    )
    app.state._uploads_watcher_task = uploads_watcher_task
    logger.info("Uploads watcher task started")
    
    index_rebuilder_task = await start_index_rebuilder()
    app.state._index_rebuilder_task = index_rebuilder_task
    if index_rebuilder_task:
        logger.info("Index rebuilder task started")
    
    logger.info("ChatBot application startup complete")
    
    yield
    
    logger.info("Shutting down ChatBot application...")
    
    task = getattr(app.state, '_uploads_watcher_task', None)
    if task:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        logger.info("Uploads watcher task stopped")
    
    rebuilder_task = getattr(app.state, '_index_rebuilder_task', None)
    if rebuilder_task:
        rebuilder_task.cancel()
        try:
            await rebuilder_task
        except asyncio.CancelledError:
            pass
        logger.info("Index rebuilder task stopped")
        
    logger.info("ChatBot application shutdown complete")
