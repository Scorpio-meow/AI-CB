from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session
from app.models.database import get_db
from app.models import Document, DocumentChunk
from app.rag.contextual_rag import ContextualRAG
from app.services.document_processor import DocumentProcessor
from langchain.schema import Document as LangchainDocument
import os
import shutil
from typing import List, Dict, Any
from pydantic import BaseModel
import asyncio
import logging

logger = logging.getLogger(__name__)
router = APIRouter()
rag_system = ContextualRAG()
# Global deletion lock to ensure only one deletion (single or bulk) runs at a time
_deletion_lock = asyncio.Lock()


async def _acquire_deletion_lock_or_409():
    """Acquire the global deletion lock immediately or raise 409 if another deletion is running."""
    if _deletion_lock.locked():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="刪除作業正在進行中，請稍後重試")
    await _deletion_lock.acquire()
    return True

@router.post("/upload")
async def upload_document(
    file: List[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    """上傳文件到知識庫"""
    # 支援多檔案上傳
    if not file or len(file) == 0:
        raise HTTPException(status_code=400, detail="請上傳至少一個文件")

    upload_dir = "data/uploads"
    os.makedirs(upload_dir, exist_ok=True)

    results = []
    for up in file:
        # 檢查文件類型
        if not DocumentProcessor.validate_file_type(up.content_type):
            results.append({
                "filename": up.filename,
                "status": "failed",
                "detail": f"不支援的文件類型: {up.content_type}"
            })
            continue

        max_size = 50 * 1024 * 1024

        try:
            # 生成安全且不重複的檔名
            safe_filename = up.filename.replace(" ", "_").replace("..", "")
            base_name, ext = os.path.splitext(safe_filename)
            file_path = os.path.join(upload_dir, safe_filename)
            counter = 1
            while os.path.exists(file_path):
                safe_filename = f"{base_name}_{counter}{ext}"
                file_path = os.path.join(upload_dir, safe_filename)
                counter += 1

            # 流式寫入到磁碟，同時計算大小
            bytes_written = 0
            with open(file_path, "wb") as buffer:
                while True:
                    chunk = await up.read(1024 * 1024)
                    if not chunk:
                        break
                    buffer.write(chunk)
                    bytes_written += len(chunk)
                    if bytes_written > max_size:
                        # 超過大小限制，清理並標記失敗
                        buffer.close()
                        if os.path.exists(file_path):
                            os.remove(file_path)
                        results.append({
                            "filename": up.filename,
                            "status": "failed",
                            "detail": "文件大小不能超過 50MB"
                        })
                        break

            if bytes_written > max_size:
                continue

            # 使用文檔處理器提取文本內容
            content = DocumentProcessor.extract_text_from_file(file_path, up.content_type)
            if not content or not content.strip():
                # 清理已上傳的文件
                if os.path.exists(file_path):
                    os.remove(file_path)
                results.append({
                    "filename": safe_filename,
                    "status": "failed",
                    "detail": "無法從文件中提取文本內容"
                })
                continue

            # 保存到數據庫
            document = Document(
                filename=safe_filename,
                content=content,
                file_type=up.content_type,
                uploaded_by=1
            )
            db.add(document)
            db.commit()
            db.refresh(document)

            # 添加到 RAG 系統
            langchain_doc = LangchainDocument(
                page_content=content,
                metadata={
                    "source": safe_filename,
                    "document_id": document.id,
                    "uploaded_by": 1,
                    "content_type": up.content_type,
                    "original_filename": up.filename
                }
            )
            await rag_system.add_documents([langchain_doc])

            # 標記為已處理
            document.is_processed = True
            db.commit()

            results.append({
                "filename": safe_filename,
                "status": "success",
                "document_id": document.id,
                "content_length": len(content),
                "content_type": up.content_type
            })

        except Exception as e:
            logger.error(f"處理文件 {up.filename} 失敗: {e}")
            try:
                if 'file_path' in locals() and os.path.exists(file_path):
                    os.remove(file_path)
            except:
                pass
            results.append({
                "filename": up.filename,
                "status": "failed",
                "detail": str(e)
            })

    return {"results": results}

@router.get("/")
async def get_documents(
    db: Session = Depends(get_db)
):
    """獲取文件列表"""
    # 返回所有文件
    documents = db.query(Document).all()
    return documents

@router.delete("/{document_id}")
async def delete_document(
    document_id: int,
    db: Session = Depends(get_db)
):
    """刪除文件"""
    # Acquire global deletion lock or return 409
    await _acquire_deletion_lock_or_409()
    try:
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise HTTPException(status_code=404, detail="文件不存在")

        # Remove from RAG system (synchronous, serialized to avoid concurrent reindex)
        try:
            await asyncio.to_thread(rag_system.remove_document_by_id, document_id)
        except Exception as e:
            logger.warning(f"Failed to remove document from RAG system: {e}")

        # Delete document chunks for this document
        try:
            db.query(DocumentChunk).filter(DocumentChunk.document_id == document_id).delete()
        except Exception as e:
            logger.warning(f"Failed to delete document chunks for {document_id}: {e}")

        # Delete physical file
        try:
            import os
            upload_dir = "data/uploads"
            file_path = os.path.join(upload_dir, document.filename)
            if os.path.exists(file_path):
                await asyncio.to_thread(os.remove, file_path)
        except Exception as e:
            logger.warning(f"Failed to remove physical file: {e}")

        # Delete document record (commit per-document)
        try:
            db.delete(document)
            db.commit()
        except Exception as e:
            logger.error(f"Failed to delete document record {document_id}: {e}")
            try:
                db.rollback()
            except Exception:
                pass
            raise HTTPException(status_code=500, detail="DB 刪除失敗")

        return {"message": "文件刪除成功"}
    finally:
        # Release deletion lock
        try:
            if _deletion_lock.locked():
                _deletion_lock.release()
        except Exception:
            pass


class BulkDeleteRequest(BaseModel):
    ids: List[int]


@router.post("/bulk_delete")
async def bulk_delete_documents(
    request: BulkDeleteRequest,
    db: Session = Depends(get_db)
):
    """一次刪除多個文件，返回每個 id 的刪除結果。

    流程：
    1. 以單次查詢找出存在的 Document
    2. 對每個存在的 Document 並行處理：從 RAG 移除、刪除實體檔案（使用 asyncio.to_thread 執行阻塞 I/O）
    3. 以批次 SQL 刪除 DocumentChunk 與 Document
    4. 回傳每個 id 的結果，含錯誤細節
    """
    ids = list(dict.fromkeys(request.ids or []))
    results: List[Dict[str, Any]] = []
    if not ids:
        return {"results": results}

    # Acquire global deletion lock or return 409
    await _acquire_deletion_lock_or_409()
    try:
        # Process ids in input order, sequentially
        for document_id in ids:
            doc = db.query(Document).filter(Document.id == document_id).first()
            if not doc:
                results.append({"id": document_id, "status": "not_found", "detail": "文件不存在"})
                continue

            detail_msgs: List[str] = []

            # Remove from RAG (synchronously, serialized)
            try:
                await asyncio.to_thread(rag_system.remove_document_by_id, document_id)
            except Exception as e:
                msg = f"RAG remove failed: {e}"
                logger.warning(msg)
                detail_msgs.append(msg)

            # Remove physical file
            try:
                upload_dir = "data/uploads"
                file_path = os.path.join(upload_dir, doc.filename)
                if os.path.exists(file_path):
                    await asyncio.to_thread(os.remove, file_path)
            except Exception as e:
                msg = f"File remove failed: {e}"
                logger.warning(msg)
                detail_msgs.append(msg)

            # Delete DB records for this document (chunks + document) with per-doc commit/rollback
            try:
                db.query(DocumentChunk).filter(DocumentChunk.document_id == document_id).delete()
                db.delete(doc)
                db.commit()
                # success
                if detail_msgs:
                    results.append({"id": document_id, "status": "deleted_with_warnings", "detail": "; ".join(detail_msgs)})
                else:
                    results.append({"id": document_id, "status": "deleted"})
            except Exception as e:
                logger.error(f"DB delete failed for {document_id}: {e}")
                try:
                    db.rollback()
                except Exception:
                    pass
                results.append({"id": document_id, "status": "failed", "detail": f"DB delete failed: {e}; details: {'; '.join(detail_msgs)}"})

    finally:
        # Always release the global deletion lock
        try:
            if _deletion_lock.locked():
                _deletion_lock.release()
        except Exception:
            pass

    return {"results": results}
