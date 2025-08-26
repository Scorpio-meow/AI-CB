from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from app.models.database import get_db
from app.models import Document, DocumentChunk
from app.rag.contextual_rag import HybridContextualRAG
from app.tasks.rag_tasks import add_documents_task, remove_document_task
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
rag_system = HybridContextualRAG()


def _enqueue_task_safe(task, *args, **kwargs):
    """Try to enqueue a Celery task; if Redis or Celery is not available, return None."""
    try:
        import redis as _redis  # check redis python client availability
    except Exception:
        logger.debug("redis python package not available; will fallback to inline execution")
        return None

    try:
        return task.delay(*args, **kwargs)
    except Exception as e:
        logger.warning(f"Failed to enqueue task {getattr(task, '__name__', str(task))}: {e}")
        return None

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

            # 添加到 RAG 系統 via Celery background worker
            langchain_doc = {
                'page_content': content,
                'metadata': {
                    "source": safe_filename,
                    "document_id": document.id,
                    "uploaded_by": 1,
                    "content_type": up.content_type,
                    "original_filename": up.filename
                }
            }
            task = _enqueue_task_safe(add_documents_task, [langchain_doc])
            if task is not None:
                task_id = getattr(task, 'id', None)
            else:
                try:
                    await rag_system.add_documents([LangchainDocument(page_content=content, metadata=langchain_doc['metadata'])])
                except Exception as e:
                    logger.warning(f"Fallback add_documents failed: {e}")
                task_id = None

            # 標記為已處理
            document.is_processed = True
            db.commit()

            results.append({
                "filename": safe_filename,
                "status": "success",
                "document_id": document.id,
                "content_length": len(content),
                "content_type": up.content_type,
                "rag_task_id": task_id
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
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="文件不存在")
    
    # 從 RAG 系統中移除文檔（可能會重建 FAISS 索引）
    task = _enqueue_task_safe(remove_document_task, document_id)
    if task is None:
        try:
            await asyncio.to_thread(rag_system.remove_document_by_id, document_id)
        except Exception as e2:
            logger.warning(f"Fallback remove_document_by_id failed: {e2}")
    
    # 刪除文件塊
    db.query(DocumentChunk).filter(DocumentChunk.document_id == document_id).delete()
    
    # 刪除實際文件（如果存在）
    try:
        import os
        upload_dir = "data/uploads"
        file_path = os.path.join(upload_dir, document.filename)
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception as e:
        print(f"Warning: Failed to remove physical file: {e}")
    
    # 刪除文件記錄
    db.delete(document)
    db.commit()
    
    return {"message": "文件刪除成功"}


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

    # 查出存在的 documents
    documents = db.query(Document).filter(Document.id.in_(ids)).all()
    present_ids = [d.id for d in documents]
    missing_ids = [i for i in ids if i not in present_ids]

    # 標記不存在的 id
    for mid in missing_ids:
        results.append({"id": mid, "status": "not_found", "detail": "文件不存在"})

    # 並行處理 RAG 移除與實體檔案刪除
    async def handle_doc_removal(doc: Document) -> Dict[str, Any]:
        doc_id = doc.id
        detail_msgs = []
        # 移除 RAG 索引（可能為阻塞）
        try:
            await asyncio.to_thread(rag_system.remove_document_by_id, doc_id)
        except Exception as e:
            msg = f"RAG remove failed: {e}"
            logger.warning(msg)
            detail_msgs.append(msg)

        # 刪除實體檔案
        try:
            upload_dir = "data/uploads"
            file_path = os.path.join(upload_dir, doc.filename)
            if os.path.exists(file_path):
                await asyncio.to_thread(os.remove, file_path)
        except Exception as e:
            msg = f"File remove failed: {e}"
            logger.warning(msg)
            detail_msgs.append(msg)

        return {"id": doc_id, "detail_msgs": detail_msgs}

    tasks = [handle_doc_removal(d) for d in documents]
    per_doc_results = []
    if tasks:
        per_doc_results = await asyncio.gather(*tasks, return_exceptions=False)

    # 批次刪除 DocumentChunk 與 Document
    try:
        if present_ids:
            db.query(DocumentChunk).filter(DocumentChunk.document_id.in_(present_ids)).delete(synchronize_session=False)
            db.query(Document).filter(Document.id.in_(present_ids)).delete(synchronize_session=False)
            db.commit()
            db_operation_ok = True
        else:
            db_operation_ok = True
    except Exception as e:
        logger.error(f"Batch DB delete failed: {e}")
        try:
            db.rollback()
        except Exception:
            pass
        db_operation_ok = False

    # 撰寫最終結果
    for r in per_doc_results:
        doc_id = r.get('id')
        msgs = r.get('detail_msgs') or []
        if not db_operation_ok:
            results.append({"id": doc_id, "status": "failed", "detail": "DB delete failed" + (": " + "; ".join(msgs) if msgs else "")})
        else:
            if msgs:
                results.append({"id": doc_id, "status": "deleted_with_warnings", "detail": "; ".join(msgs)})
            else:
                results.append({"id": doc_id, "status": "deleted"})

    return {"results": results}
