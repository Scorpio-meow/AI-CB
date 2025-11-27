from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from app.models.database import get_db
from app.models import Document, DocumentChunk
from app.core.rag_manager import get_rag_system
from app.core.user_context import get_current_user_id, get_default_user_id
from app.core.jwt_auth import get_current_admin_user
from app.services.document_processor import DocumentProcessor
from app.core.input_validator import InputValidator
import re
from langchain.schema import Document as LangchainDocument
import os
from typing import List
import logging
from datetime import datetime

logger = logging.getLogger(__name__)
router = APIRouter()

# Get configuration from environment
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "10"))  # 降低到 10MB
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "data/uploads")

# 允許的副檔名（白名單）
ALLOWED_EXTENSIONS = {'.txt', '.pdf', '.docx'}

# QA detection pattern (supports Q/A or Ｑ/Ａ with Chinese/fullwidth punctuation)
QA_PATTERN = re.compile(r"(?:^|\n)\s*[QＱ]\s*[：:]\s*(.*?)\s*[\r\n]+\s*[AＡ]\s*[：:]\s*(.*?)(?=(?:\n\s*[QＱ]\s*[：:]|\Z))",
                        re.DOTALL)


def validate_filename(filename: str) -> str:
    """
    驗證並清理檔名，防止路徑遍歷攻擊
    
    Args:
        filename: 原始檔名
        
    Returns:
        str: 清理後的安全檔名
        
    Raises:
        ValueError: 如果檔名包含危險字符
    """
    # 移除路徑分隔符和其他危險字符
    dangerous_chars = ['/', '\\', '..', '<', '>', ':', '"', '|', '?', '*', '\0']
    for char in dangerous_chars:
        if char in filename:
            raise ValueError(f"檔名包含不允許的字符: {char}")
    
    # 檢查副檔名
    from pathlib import Path
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"不允許的檔案類型: {ext}")
    
    # 限制檔名長度
    if len(filename) > 255:
        raise ValueError("檔名過長")
    
    return filename.replace(" ", "_")


def split_faq(text: str):
    """分割 FAQ/Q&A 格式文本"""
    pairs = []
    for m in QA_PATTERN.finditer(text):
        q = m.group(1).strip()
        a = m.group(2).strip()
        if q and a:
            pairs.append((q, a))
    return pairs


def process_document_for_rag(content: str, metadata: dict, rag_system) -> tuple:
    """
    統一的文檔處理邏輯，自動檢測 QA 格式
    
    Returns:
        tuple: (langchain_docs, qa_count)
    """
    # 檢測 QA 格式
    try:
        qa_pairs = split_faq(content)
    except Exception:
        qa_pairs = []
    
    langchain_docs = []
    
    if qa_pairs:
        # QA 格式：每個 Q&A 對作為獨立塊
        for i, (q, a) in enumerate(qa_pairs):
            chunk_content = f"Q：{q}\nA：{a}"
            qa_metadata = {
                **metadata,
                "qa_index": i,
                "question": q[:2000],
                "preserve_whole": True  # 標記為完整保留，不再分塊
            }
            langchain_docs.append(LangchainDocument(
                page_content=chunk_content,
                metadata=qa_metadata
            ))
        logger.info(f"檢測到 {len(qa_pairs)} 個 Q&A 對，將作為完整塊處理")
    else:
        # 正常格式：使用標準分塊
        langchain_docs.append(LangchainDocument(
            page_content=content,
            metadata=metadata
        ))
    
    return langchain_docs, len(qa_pairs)


@router.post("/upload")
async def upload_document(
    file: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
    current_user: dict = Depends(get_current_admin_user)
):
    """上傳文件到知識庫（需要管理員權限）"""
    # 支援多檔案上傳
    if not file or len(file) == 0:
        raise HTTPException(status_code=400, detail="請上傳至少一個文件")
    
    # 限制單次上傳的檔案數量
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
            # 安全檢查 1: 驗證並清理檔名
            try:
                # 使用增強的檔名驗證
                is_valid, error_msg = InputValidator.validate_filename(up.filename)
                if not is_valid:
                    raise ValueError(error_msg)
                safe_filename = validate_filename(up.filename)
            except ValueError as e:
                logger.warning(f"檔名驗證失敗: {up.filename} - {str(e)}")
                results.append({
                    "filename": up.filename,
                    "status": "failed",
                    "detail": f"檔名驗證失敗: {str(e)}",
                    "http_status": 400
                })
                continue
            
            # 安全檢查 2: 檢查文件類型
            if not DocumentProcessor.validate_file_type(up.content_type):
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
                            "detail": f"文件大小不能超過 {MAX_FILE_SIZE_MB}MB",
                            "http_status": 400
                        })
                        break

            if bytes_written > max_size:
                continue
            
            # 安全檢查 3: 計算檔案雜湊值（用於重複檢測和追蹤）
            file_hash = DocumentProcessor.calculate_file_hash(file_path)
            logger.info(f"Uploaded file hash: {file_hash}")

            # 使用文檔處理器提取文本內容（包含檔案頭部驗證）
            try:
                content = DocumentProcessor.extract_text_from_file(file_path, up.content_type)
            except ValueError as ve:
                # 檔案頭部驗證失敗或其他安全問題
                if os.path.exists(file_path):
                    os.remove(file_path)
                logger.warning(f"File security validation failed for {up.filename}: {ve}")
                results.append({
                    "filename": safe_filename,
                    "status": "failed",
                    "detail": f"安全驗證失敗: {str(ve)}",
                    "http_status": 400
                })
                continue
            except Exception as e:
                # 其他處理錯誤
                if os.path.exists(file_path):
                    os.remove(file_path)
                # Log the full stacktrace on the server for troubleshooting
                logger.exception("File processing error for %s", up.filename)
                results.append({
                    "filename": safe_filename,
                    "status": "failed",
                    "detail": "檔案處理錯誤: 內部錯誤，請聯繫系統管理員",
                    "http_status": 500
                })
                continue
            
            if not content or not content.strip():
                # 清理已上傳的文件
                if os.path.exists(file_path):
                    os.remove(file_path)
                results.append({
                    "filename": safe_filename,
                    "status": "failed",
                    "detail": "無法從文件中提取文本內容",
                    "http_status": 400
                })
                continue

            # ===== 重複檢查：以抽取出的文本內容比對是否已存在相同文件 =====
            try:
                normalized_content = content.strip()
                existing = db.query(Document).filter(Document.content == normalized_content).first()
            except Exception:
                existing = None

            if existing:
                logger.info(f"Duplicate upload detected for file {up.filename}; existing document id={existing.id}")
                # 刪除剛寫入的實體檔案，並回傳 duplicate 狀態（拒絕重複上傳）
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
                # 不再將文件加入 DB 或 RAG
                continue
            # ==========================================================

            # 保存到數據庫
            document = Document(
                filename=safe_filename,
                content=content,
                file_type=up.content_type,
                uploaded_by=user_id  # Use dynamic user_id
            )
            db.add(document)
            db.commit()
            db.refresh(document)

            # 使用統一的文檔處理邏輯（自動檢測 QA 格式）
            rag_system = get_rag_system()
            base_metadata = {
                "source": safe_filename,
                "document_id": document.id,
                "uploaded_by": user_id,
                "content_type": up.content_type,
                "original_filename": up.filename
            }
            
            langchain_docs, qa_count = process_document_for_rag(content, base_metadata, rag_system)
            await rag_system.add_documents(langchain_docs)

            # 標記為已處理
            document.is_processed = True
            db.commit()

            # 回傳處理結果
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
            # Log full stack trace on the server, but do not expose exception details to the client.
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
    """獲取文件列表（需要管理員權限）"""
    try:
        # 返回所有文件
        documents = db.query(Document).all()
        return documents
    except Exception:
        # 不暴露堆棧追蹤到客戶端，僅記錄服務端日誌
        logger.exception("獲取文件列表失敗")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.delete("/{document_id}")
async def delete_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user)
):
    """刪除文件（需要管理員權限）"""
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="文件不存在")
    
    # 從 RAG 系統中移除文檔；不立即重建 BM25（Windows 上檔案可能被鎖定）
    try:
        # skip BM25 rebuild here to avoid Whoosh file lock errors on Windows.
        rag_system = get_rag_system()
        rag_system.remove_document_by_id(document_id, rebuild_bm25=False)
    except Exception as e:
        logger.warning("Failed to remove document from RAG system: %s", str(e))
    
    # 刪除文件塊
    db.query(DocumentChunk).filter(DocumentChunk.document_id == document_id).delete()
    
    # 刪除實際文件（如果存在）
    try:
        upload_dir = UPLOAD_DIR
        file_path = os.path.join(upload_dir, document.filename)
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception as e:
        logger.warning("Failed to remove physical file: %s", str(e))
    
    # 刪除文件記錄
    db.delete(document)
    db.commit()
    
    return {"message": "文件刪除成功"}

@router.post("/rebuild-index")
async def rebuild_index(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user)
):
    """重建知識庫索引（需要管理員權限）- 從數據庫重新載入並用新配置重新分塊"""
    try:
        logger.info(f"管理員 {current_user.get('username', 'unknown')} 觸發完整索引重建（含重新分塊）")
        
        # 獲取 RAG 系統
        rag_system = get_rag_system()
        
        # 清空現有索引和文檔
        logger.info("清空現有索引...")
        rag_system.documents = []
        rag_system.index.reset()
        
        # 從數據庫重新載入所有文檔
        logger.info("從數據庫重新載入文檔...")
        documents_from_db = db.query(Document).all()
        
        if not documents_from_db:
            logger.warning("數據庫中沒有文檔")
            return {
                "message": "索引重建完成（沒有文檔）",
                "document_count": 0,
                "chunk_count": 0,
                "timestamp": datetime.now().isoformat()
            }
        
        # 用新配置重新分塊並添加到 RAG
        logger.info(f"用新配置重新處理 {len(documents_from_db)} 個文檔（chunk_size={rag_system.chunk_size}, chunk_overlap={rag_system.chunk_overlap}）...")
        
        total_chunks = 0
        total_qa_pairs = 0
        for doc in documents_from_db:
            try:
                base_metadata = {
                    "source": doc.filename,
                    "document_id": doc.id,
                    "uploaded_by": doc.uploaded_by,
                    "content_type": doc.file_type,
                    "original_filename": doc.filename
                }
                
                # 🔑 使用統一處理邏輯，自動檢測 QA 格式
                langchain_docs, qa_count = process_document_for_rag(doc.content, base_metadata, rag_system)
                chunks_added = await rag_system.add_documents(langchain_docs)
                
                total_chunks += chunks_added or 0
                if qa_count > 0:
                    total_qa_pairs += qa_count
                    logger.info(f"處理文檔 {doc.id} ({doc.filename}): {qa_count} 個 Q&A 對")
                else:
                    logger.info(f"處理文檔 {doc.id} ({doc.filename}): {chunks_added} 個分塊")
            except Exception as e:
                logger.error(f"處理文檔 {doc.id} ({doc.filename}) 失敗: {e}")
                continue
        
        # 獲取統計信息
        doc_count = len(documents_from_db)
        vector_count = rag_system.index.ntotal
        
        logger.info(f"索引重建完成: {doc_count} 個文檔 -> {vector_count} 個向量塊 (含 {total_qa_pairs} 個 Q&A 對)")
        
        return {
            "message": "索引重建成功（已用新配置重新分塊，並重新檢測 QA 格式）",
            "document_count": doc_count,
            "chunk_count": vector_count,
            "qa_pairs_detected": total_qa_pairs,
            "chunk_size": rag_system.chunk_size,
            "chunk_overlap": rag_system.chunk_overlap,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"索引重建失敗: {e}")
        raise HTTPException(status_code=500, detail=f"索引重建失敗: {str(e)}")
