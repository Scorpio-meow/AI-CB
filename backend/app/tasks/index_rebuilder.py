
import asyncio
import os
import logging
from datetime import datetime
from app.core.rag_manager import get_rag_system
from app.core.config import settings

logger = logging.getLogger(__name__)

REINDEX_HOURS = settings.REINDEX_HOURS
ENABLE_AUTO_REINDEX_TASK = bool(settings.ENABLE_AUTO_REINDEX_TASK)
async def periodic_index_rebuild():
    if not ENABLE_AUTO_REINDEX_TASK:
        logger.info("Periodic index rebuild task is disabled (ENABLE_AUTO_REINDEX_TASK=0)")
        return
    
    interval_seconds = REINDEX_HOURS * 3600
    logger.info(f"Starting periodic index rebuild task (interval: {REINDEX_HOURS}h)")
    
    while True:
        try:
            await asyncio.sleep(interval_seconds)
            
            logger.info("Periodic reindex triggered - checking if rebuild is needed...")
            rag_system = get_rag_system()
            
            metadata_path = getattr(rag_system, 'metadata_path', None)
            if metadata_path and os.path.exists(metadata_path):
                try:
                    import pickle
                    with open(metadata_path, 'rb') as f:
                        metadata = pickle.load(f)
                    
                    last_reindex = metadata.get("last_reindex")
                    if last_reindex and isinstance(last_reindex, datetime):
                        hours_since = (datetime.now() - last_reindex).total_seconds() / 3600
                        
                        if hours_since < REINDEX_HOURS:
                            logger.info(f"Skipping reindex - only {hours_since:.1f}h since last rebuild")
                            continue
                except Exception as e:
                    logger.warning(f"Failed to check reindex metadata: {e}")
            
            logger.info("Starting index rebuild...")
            rag_system.force_reindex()
            logger.info("Index rebuild completed successfully")
            
        except Exception as e:
            logger.error(f"Error in periodic index rebuild task: {e}", exc_info=True)
            await asyncio.sleep(300)
async def start_index_rebuilder():
    if ENABLE_AUTO_REINDEX_TASK:
        return asyncio.create_task(periodic_index_rebuild())
    else:
        logger.info("Auto reindex task disabled")
        return None
