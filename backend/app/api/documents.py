from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from app.models.database import get_db
from app.models import Document as DBDocument
from app.core.rag_manager import get_rag_system
from app.core.user_context import get_current_user_id, get_default_user_id
from app.core.jwt_auth import get_current_admin_user
from app.services.document_processor import DocumentProcessor
from app.core.input_validator import InputValidator
from pydantic import BaseModel
import re
import asyncio
from langchain_core.documents import Document as LangChainDocument
import os
from typing import List
import logging
from datetime import datetime
from app.core.config import settings
logger = logging.getLogger(__name__)
router = APIRouter()
MAX_FILE_SIZE_MB = settings.MAX_FILE_SIZE_MB
UPLOAD_DIR = settings.UPLOAD_DIR
ALLOWED_EXTENSIONS = DocumentProcessor.SUPPORTED_EXTENSIONS
QA_PATTERN = re.compile(r"(?:^|\n)\s*[QＱ]\s*[：:]\s*(.*?)\s*[\r\n]+\s*[AＡ]\s*[：:]\s*(.*?)(?=(?:\n\s*[QＱ]\s*[：:]|\Z))",
                        re.DOTALL)
def validate_filename(filename: str) -> str:
    dangerous_chars = ['/', '\\', '..', '<', '>', ':', '"', '|', '?', '*', '\0']
    for char in dangerous_chars:
        if char in filename:
            raise ValueError(f"檔名包含不允許的字符: {char}")
    from pathlib import Path
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"不允許的檔案類型: {ext}")
    if len(filename) > 255:
        raise ValueError("檔名過長")
    return filename.replace(" ", "_")
def split_faq(text: str):
    pairs = []
    for m in QA_PATTERN.finditer(text):
        q = m.group(1).strip()
        a = m.group(2).strip()
        if q and a:
            pairs.append((q, a))
    return pairs
def process_document_for_rag(content: str, metadata: dict, rag_system) -> tuple:
    try:
        qa_pairs = split_faq(content)
    except Exception:
        qa_pairs = []
    if qa_pairs:
        langchain_docs = []
        for i, (q, a) in enumerate(qa_pairs):
            chunk_content = f"Q：{q}\nA：{a}"
            qa_metadata = {
                **metadata,
                "qa_index": i,
                "question": q[:2000],
                "preserve_whole": True
            }
            langchain_docs.append(LangChainDocument(
                page_content=chunk_content,
                metadata=qa_metadata
            ))
        logger.info(f"檢測到 {len(qa_pairs)} 個 Q&A 對，將作為完整塊處理")
        return langchain_docs, len(qa_pairs)
    try:
        structured_records = DocumentProcessor.split_structured_records(content)
    except Exception as e:
        logger.warning(f"結構化切分檢測失敗: {e}")
        structured_records = []
    if structured_records:
        langchain_docs = []
        for i, (chunk_text, extra_meta) in enumerate(structured_records):
            doc_meta = {
                **metadata,
                **extra_meta,
                "record_index": extra_meta.get("record_index", i + 1),
                "preserve_whole": True
            }
            langchain_docs.append(LangChainDocument(
                page_content=chunk_text,
                metadata=doc_meta
            ))
        logger.info(f"檢測到 {len(structured_records)} 條結構化/JSON 記錄，已建立為獨立原子分塊 (Atomic Record Chunks)")
        return langchain_docs, len(structured_records)
    langchain_docs = [LangChainDocument(
        page_content=content,
        metadata=metadata
    )]
    return langchain_docs, 0
@router.post("/upload")
async def upload_document(
    file: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
    current_user: dict = Depends(get_current_admin_user)
):
    if not file or len(file) == 0:
        raise HTTPException(status_code=400, detail="請上傳至少一個文件")
    MAX_FILES_PER_UPLOAD = 10
    if len(file) > MAX_FILES_PER_UPLOAD:
        raise HTTPException(
            status_code=400, 
            detail=f"單次最多只能上傳 {MAX_FILES_PER_UPLOAD} 個檔案"
        )
    upload_dir = UPLOAD_DIR
    os.makedirs(upload_dir, exist_ok=True)
    results = []
    for up in file:
        try:
            try:
                is_valid, error_msg = InputValidator.validate_filename(up.filename)
                if not is_valid:
                    raise ValueError(error_msg)
                safe_filename = validate_filename(up.filename)
            except ValueError as e:
                logger.warning(f"檔名驗證失敗: {up.filename} - {str(e)}")
                results.append({
                    "filename": up.filename,
                    "status": "failed",
                    "detail": "檔名驗證失敗: 無效的檔名或不允許的副檔名",
                    "http_status": 400
                })
                continue
            if not DocumentProcessor.validate_file_type(up.content_type, up.filename):
                results.append({
                    "filename": up.filename,
                    "status": "failed",
                    "detail": f"不支援的文件類型: {up.content_type}",
                    "http_status": 400
                })
                continue
            max_size = MAX_FILE_SIZE_MB * 1024 * 1024
            base_name, ext = os.path.splitext(safe_filename)
            file_path = os.path.join(upload_dir, safe_filename)
            counter = 1
            while os.path.exists(file_path):
                safe_filename = f"{base_name}_{counter}{ext}"
                file_path = os.path.join(upload_dir, safe_filename)
                counter += 1
            bytes_written = 0
            with open(file_path, "wb") as buffer:
                while True:
                    chunk = await up.read(1024 * 1024)
                    if not chunk:
                        break
                    buffer.write(chunk)
                    bytes_written += len(chunk)
                    if bytes_written > max_size:
                        buffer.close()
                        if os.path.exists(file_path):
                            os.remove(file_path)
                        results.append({
                            "filename": up.filename,
                            "status": "failed",
                            "detail": f"文件大小不能超過 {MAX_FILE_SIZE_MB}MB",
                            "http_status": 400
                        })
                        break
            if bytes_written > max_size:
                continue
            file_hash = DocumentProcessor.calculate_file_hash(file_path)
            logger.info(f"Uploaded file hash: {file_hash}")
            try:
                content = await asyncio.to_thread(DocumentProcessor.extract_text_from_file, file_path, up.content_type)
            except ValueError as ve:
                if os.path.exists(file_path):
                    os.remove(file_path)
                logger.warning("File security validation failed for %s: %s", up.filename, str(ve))
                results.append({
                    "filename": safe_filename,
                    "status": "failed",
                    "detail": "安全驗證失敗: 上傳的檔案未通過安全檢查",
                    "http_status": 400
                })
                continue
            except Exception as e:
                if os.path.exists(file_path):
                    os.remove(file_path)
                logger.exception("File processing error for %s", up.filename)
                results.append({
                    "filename": safe_filename,
                    "status": "failed",
                    "detail": "檔案處理錯誤: 內部錯誤，請聯繫系統管理員",
                    "http_status": 500
                })
                continue
            if not content or not content.strip():
                if os.path.exists(file_path):
                    os.remove(file_path)
                results.append({
                    "filename": safe_filename,
                    "status": "failed",
                    "detail": "無法從文件中提取文本內容",
                    "http_status": 400
                })
                continue
            try:
                normalized_content = content.strip()
                existing = db.query(DBDocument).filter(DBDocument.content == normalized_content).first()
            except Exception:
                existing = None
            if existing:
                logger.info(f"Duplicate upload detected for file {up.filename}; existing document id={existing.id}")
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                except Exception:
                    pass
                results.append({
                    "filename": safe_filename,
                    "status": "duplicate",
                    "detail": "內容已存在",
                    "existing_document_id": existing.id,
                    "http_status": 409
                })
                continue
            doc_desc = await DocumentProcessor.generate_document_summary_async(safe_filename, content, up.content_type or "")
            document = DBDocument(
                filename=safe_filename,
                content=content,
                file_type=up.content_type,
                description=doc_desc,
                uploaded_by=user_id
            )
            db.add(document)
            db.commit()
            db.refresh(document)
            rag_system = get_rag_system()
            base_metadata = {
                "source": safe_filename,
                "document_id": document.id,
                "uploaded_by": user_id,
                "content_type": up.content_type,
                "original_filename": up.filename
            }
            logger.info(f"正在對文件 {safe_filename} ({len(content)} 字元) 進行分塊處理...")
            langchain_docs, qa_count = await asyncio.to_thread(
                process_document_for_rag, content, base_metadata, rag_system
            )
            logger.info(f"正在將文件 {safe_filename} 提交至 RAG 引擎進行分塊與向量化...")
            added_chunks = await asyncio.to_thread(rag_system.add_documents, langchain_docs)
            document.is_processed = True
            db.commit()
            logger.info(f"文件 {safe_filename} 成功入庫並完成向量索引 (共 {added_chunks} 塊)")
            results.append({
                "filename": safe_filename,
                "status": "success",
                "document_id": document.id,
                "content_length": len(content),
                "content_type": up.content_type,
                "qa_detected": qa_count > 0,
                "qa_pairs": qa_count,
                "http_status": 201
            })
        except Exception as e:
            logger.exception("處理文件 %s 失敗", up.filename)
            try:
                if 'file_path' in locals() and os.path.exists(file_path):
                    os.remove(file_path)
            except:
                pass
            results.append({
                "filename": up.filename,
                "status": "failed",
                "detail": "内部錯誤，處理失敗。請聯繫系統管理員。",
                "http_status": 500
            })
    return {"results": results}
@router.get("/")
async def get_documents(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user)
):
    try:
        documents = db.query(DBDocument).all()
        updated = False
        for doc in documents:
            if (not doc.description or not doc.description.strip()) and doc.content:
                doc.description = await DocumentProcessor.generate_document_summary_async(doc.filename, doc.content, doc.file_type or "")
                db.add(doc)
                updated = True
        if updated:
            db.commit()
        return documents
    except Exception:
        logger.exception("獲取文件列表失敗")
        raise HTTPException(status_code=500, detail="Internal server error")
class DocumentSummaryUpdate(BaseModel):
    description: str
@router.post("/{document_id}/regenerate-summary")
async def regenerate_document_summary(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user)
):
    """手動或一鍵重新生成該文件的 AI 智能大綱與摘要"""
    document = db.query(DBDocument).filter(DBDocument.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="文件不存在")
    new_desc = await DocumentProcessor.generate_document_summary_async(
        document.filename, document.content, document.file_type or "text/plain"
    )
    document.description = new_desc
    db.add(document)
    db.commit()
    db.refresh(document)
    return {
        "message": "文件大綱與摘要重新生成成功",
        "document_id": document.id,
        "description": new_desc
    }
@router.put("/{document_id}/summary")
async def update_document_summary(
    document_id: int,
    payload: DocumentSummaryUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user)
):
    """手動編輯儲存該文件的大綱描述"""
    document = db.query(DBDocument).filter(DBDocument.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="文件不存在")
    document.description = payload.description.strip()
    db.add(document)
    db.commit()
    db.refresh(document)
    return {
        "message": "文件大綱更新成功",
        "document_id": document.id,
        "description": document.description
    }
@router.delete("/{document_id}")
async def delete_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user)
):
    document = db.query(DBDocument).filter(DBDocument.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="文件不存在")
    try:
        rag_system = get_rag_system()
        rag_system.remove_document_by_id(document_id, rebuild_bm25=False)
    except Exception as e:
        logger.warning("Failed to remove document from RAG system: %s", str(e))
    try:
        upload_dir = UPLOAD_DIR
        file_path = os.path.join(upload_dir, document.filename)
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception as e:
        logger.warning("Failed to remove physical file: %s", str(e))
    db.delete(document)
    db.commit()
    return {"message": "文件刪除成功"}
@router.post("/rebuild-index")
async def rebuild_index(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user)
):
    try:
        logger.info(f"管理員 {current_user.get('username', 'unknown')} 觸發完整索引重建（含重新分塊與摘要升級）")
        rag_system = get_rag_system()
        logger.info("清空現有索引...")
        rag_system.documents = []
        rag_system.index.reset()
        logger.info("從數據庫重新載入文檔...")
        documents_from_db = db.query(DBDocument).all()
        if not documents_from_db:
            logger.warning("數據庫中沒有文檔")
            return {
                "message": "索引重建完成（沒有文檔）",
                "document_count": 0,
                "chunk_count": 0,
                "timestamp": datetime.now().isoformat()
            }
        logger.info(f"用新配置重新處理 {len(documents_from_db)} 個文檔（chunk_size={rag_system.chunk_size}, chunk_overlap={rag_system.chunk_overlap}）...")
        total_chunks = 0
        total_qa_pairs = 0
        for doc in documents_from_db:
            try:
 
                file_path = os.path.join(UPLOAD_DIR, doc.filename)
                content_to_process = doc.content
                if os.path.exists(file_path):
                    try:
                        fresh_content = DocumentProcessor.extract_text_from_file(file_path, doc.file_type or "text/plain")
                        if fresh_content and fresh_content.strip():
                            content_to_process = fresh_content.strip()
                            doc.content = content_to_process
                    except Exception as e:
                        logger.warning(f"重新提取檔案 {doc.filename} 失敗，使用資料庫快取: {e}")
 
                doc.description = await DocumentProcessor.generate_document_summary_async(
                    doc.filename, content_to_process, doc.file_type or "text/plain"
                )
                db.add(doc)
                db.commit()
                base_metadata = {
                    "source": doc.filename,
                    "document_id": doc.id,
                    "uploaded_by": doc.uploaded_by,
                    "content_type": doc.file_type,
                    "original_filename": doc.filename
                }
                langchain_docs, qa_count = process_document_for_rag(content_to_process, base_metadata, rag_system)
                chunks_added = rag_system.add_documents(langchain_docs)
                
                total_chunks += chunks_added or 0
                if qa_count > 0:
                    total_qa_pairs += qa_count
                    logger.info(f"處理文檔 {doc.id} ({doc.filename}): {qa_count} 個 Q&A 對")
                else:
                    logger.info(f"處理文檔 {doc.id} ({doc.filename}): {chunks_added} 個分塊")
            except Exception as e:
                logger.exception(f"處理文檔 {doc.id} ({doc.filename}) 失敗")
                continue
        doc_count = len(documents_from_db)
        vector_count = rag_system.index.ntotal
        logger.info(f"索引重建完成: {doc_count} 個文檔 -> {vector_count} 個向量塊 (含 {total_qa_pairs} 個 Q&A 對)")
        return {
            "message": "索引重建成功（已用新配置重新分塊，並重新生成 AI 智能大綱）",
            "document_count": doc_count,
            "chunk_count": vector_count,
            "qa_pairs_detected": total_qa_pairs,
            "chunk_size": rag_system.chunk_size,
            "chunk_overlap": rag_system.chunk_overlap,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.exception("索引重建失敗")
        raise HTTPException(status_code=500, detail="索引重建失敗: 內部錯誤，請聯繫系統管理員")
