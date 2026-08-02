import asyncio
import os
import logging
from typing import List
from sqlalchemy.orm import Session
from app.models import Document
from app.models.database import SessionLocal
from app.core.rag_manager import get_rag_system
from app.api.chat import manager as ws_manager
logger = logging.getLogger(__name__)
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "data/uploads")
UPLOADS_WATCHER_INTERVAL = int(os.getenv("UPLOADS_WATCHER_INTERVAL", "30"))
def get_db_session() -> Session:
    return SessionLocal()
async def scan_and_cleanup_uploads(interval_seconds: int = None):
    if interval_seconds is None:
        interval_seconds = UPLOADS_WATCHER_INTERVAL
        
    upload_dir = UPLOAD_DIR
    os.makedirs(upload_dir, exist_ok=True)
    while True:
        try:
            db = get_db_session()
            try:
                documents: List[Document] = db.query(Document).all()
                missing_ids = []
                for doc in documents:
                    file_path = os.path.join(upload_dir, doc.filename) if doc.filename else None
                    if not file_path or not os.path.exists(file_path):
                        logger.info(f"Detected missing file for document id={doc.id}, filename={doc.filename}")
                        try:
                            rag_system = get_rag_system()
                            await asyncio.to_thread(rag_system.remove_document_by_id, doc.id, False)
                        except Exception as e:
                            logger.warning(f"Failed to remove document {doc.id} from RAG: {e}")
                        try:
                            db.delete(doc)
                            db.commit()
                            missing_ids.append(doc.id)
                        except Exception as e:
                            logger.error(f"Failed to remove DB records for missing document {doc.id}: {e}")
                            try:
                                db.rollback()
                            except Exception:
                                pass
                if missing_ids:
                    payload = {
                        "type": "documents_update",
                        "removed_ids": missing_ids,
                    }
                    for ws in list(ws_manager.active_connections):
                        try:
                            await ws.send_text(__import__('json').dumps(payload))
                        except Exception as e:
                            logger.debug(f"Failed to send websocket notification: {e}")
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Error in uploads watcher: {e}")
        await asyncio.sleep(interval_seconds)
