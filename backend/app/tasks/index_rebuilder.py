"""
Periodic Index Rebuilder Task
Automatically rebuilds FAISS and BM25 indices at specified intervals.
"""
import asyncio
import os
import logging
from datetime import datetime
from app.core.rag_manager import get_rag_system

logger = logging.getLogger(__name__)

# Configuration from environment
REINDEX_INTERVAL_HOURS = int(os.getenv("REINDEX_INTERVAL_HOURS", "24"))
ENABLE_AUTO_REINDEX_TASK = os.getenv("ENABLE_AUTO_REINDEX_TASK", "1") == "1"


async def periodic_index_rebuild():
    """
    Background task to periodically rebuild indices.
    
    This task runs in a dedicated process/thread to avoid conflicts with
    the main application. It checks the last rebuild time and triggers
    a full reindex if the threshold is exceeded.
    """
    if not ENABLE_AUTO_REINDEX_TASK:
        logger.info("Periodic index rebuild task is disabled (ENABLE_AUTO_REINDEX_TASK=0)")
        return
    
    interval_seconds = REINDEX_INTERVAL_HOURS * 3600
    logger.info(f"Starting periodic index rebuild task (interval: {REINDEX_INTERVAL_HOURS}h)")
    
    while True:
        try:
            await asyncio.sleep(interval_seconds)
            
            logger.info("Periodic reindex triggered - checking if rebuild is needed...")
            rag_system = get_rag_system()
            
            # Check if reindex is actually needed
            metadata_path = getattr(rag_system, 'metadata_path', None)
            if metadata_path and os.path.exists(metadata_path):
                try:
                    import pickle
                    with open(metadata_path, 'rb') as f:
                        metadata = pickle.load(f)
                    
                    last_reindex = metadata.get("last_reindex")
                    if last_reindex and isinstance(last_reindex, datetime):
                        hours_since = (datetime.now() - last_reindex).total_seconds() / 3600
                        
                        if hours_since < REINDEX_INTERVAL_HOURS:
                            logger.info(f"Skipping reindex - only {hours_since:.1f}h since last rebuild")
                            continue
                except Exception as e:
                    logger.warning(f"Failed to check reindex metadata: {e}")
            
            # Perform reindex
            logger.info("Starting index rebuild...")
            rag_system.force_reindex()
            logger.info("Index rebuild completed successfully")
            
        except Exception as e:
            logger.error(f"Error in periodic index rebuild task: {e}", exc_info=True)
            # Continue running despite errors
            await asyncio.sleep(300)  # Wait 5 minutes before retry on error


async def start_index_rebuilder():
    """
    Start the periodic index rebuilder as a background task.
    Called from main.py lifespan event.
    """
    if ENABLE_AUTO_REINDEX_TASK:
        return asyncio.create_task(periodic_index_rebuild())
    else:
        logger.info("Auto reindex task disabled")
        return None
