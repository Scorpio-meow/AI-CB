from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from app.models.database import get_db
from app.models import Document, DocumentChunk
from app.rag.contextual_rag import ContextualRAG
from app.services.document_processor import DocumentProcessor
import re
from langchain.schema import Document as LangchainDocument
import os
import shutil
from typing import List
import logging

logger = logging.getLogger(__name__)
router = APIRouter()
rag_system = ContextualRAG()

# Get configuration from environment
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "50"))
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "data/uploads")

# QA detection pattern (supports Q/A or Ｑ/Ａ with Chinese/fullwidth punctuation)
QA_PATTERN = re.compile(r"(?:^|\n)\s*[QＱ]\s*[：:]\s*(.*?)\s*[\r\n]+\s*[AＡ]\s*[：:]\s*(.*?)(?=(?:\n\s*[QＱ]\s*[：:]|\Z))",
                        re.DOTALL)


def split_faq(text: str):
    pairs = []
    for m in QA_PATTERN.finditer(text):
        q = m.group(1).strip()
        a = m.group(2).strip()
        if q and a:
            pairs.append((q, a))
    return pairs

@router.post("/upload")
async def upload_document(
    file: List[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    """上傳文件到知識庫"""
    # 支援多檔案上傳
    if not file or len(file) == 0:
        raise HTTPException(status_code=400, detail="請上傳至少一個文件")

    upload_dir = UPLOAD_DIR
    os.makedirs(upload_dir, exist_ok=True)

    results = []
    for up in file:
        # 檢查文件類型
        if not DocumentProcessor.validate_file_type(up.content_type):
            results.append({
                "filename": up.filename,
                "status": "failed",
                "detail": f"不支援的文件類型: {up.content_type}",
                "http_status": 400
            })
            continue

        max_size = MAX_FILE_SIZE_MB * 1024 * 1024

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
                            "detail": f"文件大小不能超過 {MAX_FILE_SIZE_MB}MB",
                            "http_status": 400
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
                uploaded_by=1
            )
            db.add(document)
            db.commit()
            db.refresh(document)

            # Detect FAQ/Q&A pairs and add as individual QA chunks when appropriate
            try:
                qa_pairs = split_faq(content)
            except Exception:
                qa_pairs = []

            if qa_pairs:
                langchain_docs = []
                for i, (q, a) in enumerate(qa_pairs):
                    chunk_content = f"Q：{q}\nA：{a}"
                    md = {
                        "source": safe_filename,
                        "document_id": document.id,
                        "uploaded_by": 1,
                        "content_type": up.content_type,
                        "original_filename": up.filename,
                        "qa_index": i,
                        "question": q[:2000],
                        "preserve_whole": True
                    }
                    langchain_docs.append(LangchainDocument(page_content=chunk_content, metadata=md))
                await rag_system.add_documents(langchain_docs)
            else:
                # 添加整個文件到 RAG
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

            # include QA detection info for traceability
            qa_count = len(qa_pairs) if 'qa_pairs' in locals() and qa_pairs else 0
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
            logger.error(f"處理文件 {up.filename} 失敗: {e}")
            try:
                if 'file_path' in locals() and os.path.exists(file_path):
                    os.remove(file_path)
            except:
                pass
            results.append({
                "filename": up.filename,
                "status": "failed",
                "detail": str(e),
                "http_status": 500
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
    
    # 從 RAG 系統中移除文檔；不立即重建 BM25（Windows 上檔案可能被鎖定）
    try:
        # skip BM25 rebuild here to avoid Whoosh file lock errors on Windows.
        rag_system.remove_document_by_id(document_id, rebuild_bm25=False)
    except Exception as e:
        print(f"Warning: Failed to remove document from RAG system: {e}")
    
    # 刪除文件塊
    db.query(DocumentChunk).filter(DocumentChunk.document_id == document_id).delete()
    
    # 刪除實際文件（如果存在）
    try:
        import os
        upload_dir = UPLOAD_DIR
        file_path = os.path.join(upload_dir, document.filename)
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception as e:
        print(f"Warning: Failed to remove physical file: {e}")
    
    # 刪除文件記錄
    db.delete(document)
    db.commit()
    
    return {"message": "文件刪除成功"}
