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
    # Startup
    logger.info("Starting ChatBot application...")
    
    # Initialize database tables
    await create_tables()
    
    # Initialize global RAG system (singleton) using to_thread
    logger.info("Initializing global RAG system using to_thread...")
    rag_system = await asyncio.to_thread(get_rag_system)
    vector_store_info = await asyncio.to_thread(rag_system.get_vector_store_info)
    logger.info(f"RAG system initialized: {vector_store_info}")
    
    # Initialize RAG httpx client
    await rag_system.init_client()
    
    # Start background tasks
    uploads_watcher_task = asyncio.create_task(
        scan_and_cleanup_uploads(settings.UPLOADS_WATCHER_INTERVAL)
    )
    app.state._uploads_watcher_task = uploads_watcher_task
    logger.info("Uploads watcher task started")
    
    # Start periodic index rebuilder
    index_rebuilder_task = await start_index_rebuilder()
    app.state._index_rebuilder_task = index_rebuilder_task
    if index_rebuilder_task:
        logger.info("Index rebuilder task started")
    
    logger.info("ChatBot application startup complete")
    
    yield
    
    # Shutdown
    logger.info("Shutting down ChatBot application...")
    
    # Cancel uploads watcher
    task = getattr(app.state, '_uploads_watcher_task', None)
    if task:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        logger.info("Uploads watcher task stopped")
    
    # Cancel index rebuilder
    rebuilder_task = getattr(app.state, '_index_rebuilder_task', None)
    if rebuilder_task:
        rebuilder_task.cancel()
        try:
            await rebuilder_task
        except asyncio.CancelledError:
            pass
        logger.info("Index rebuilder task stopped")
        
    # Close global HTTP client for workflows
    try:
        from app.services.workflow_service import close_http_client
        await close_http_client()
        logger.info("Workflow HTTP client closed")
    except Exception as e:
        logger.warning(f"Failed to close workflow HTTP client: {e}")
        
    # Close global RAG httpx client
    try:
        rag_system = get_rag_system()
        await rag_system.close_client()
        logger.info("RAG HTTP client closed")
    except Exception as e:
        logger.warning(f"Failed to close RAG HTTP client: {e}")
    
    logger.info("ChatBot application shutdown complete")
