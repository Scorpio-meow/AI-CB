from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from app.models.database import get_db
from app.models import Document, DocumentChunk
from app.rag.contextual_rag import ContextualRAG
from app.services.document_processor import DocumentProcessor
from langchain.schema import Document as LangchainDocument
import os
import shutil
from typing import List
import logging

logger = logging.getLogger(__name__)
router = APIRouter()
rag_system = ContextualRAG()

@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """上傳文件到知識庫"""
    # 檢查文件類型
    if not DocumentProcessor.validate_file_type(file.content_type):
        raise HTTPException(
            status_code=400, 
            detail=f"不支援的文件類型: {file.content_type}。支援的類型: TXT, PDF, DOCX"
        )
    
    # 檢查文件大小 (最大 50MB)
    max_size = 50 * 1024 * 1024  # 50MB
    if hasattr(file, 'size') and file.size > max_size:
        raise HTTPException(status_code=400, detail="文件大小不能超過 50MB")
    
    try:
        # 保存文件
        upload_dir = "data/uploads"
        os.makedirs(upload_dir, exist_ok=True)
        
        # 生成安全的文件名
        safe_filename = file.filename.replace(" ", "_").replace("..", "")
        file_path = os.path.join(upload_dir, safe_filename)
        
        # 如果文件已存在，添加序號
        base_name, ext = os.path.splitext(safe_filename)
        counter = 1
        while os.path.exists(file_path):
            safe_filename = f"{base_name}_{counter}{ext}"
            file_path = os.path.join(upload_dir, safe_filename)
            counter += 1
        
        # 保存文件
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        logger.info(f"文件已保存到: {file_path}")
        
        # 使用文檔處理器提取文本內容
        content = DocumentProcessor.extract_text_from_file(file_path, file.content_type)
        
        if not content or not content.strip():
            # 清理已上傳的文件
            if os.path.exists(file_path):
                os.remove(file_path)
            raise HTTPException(status_code=400, detail="無法從文件中提取文本內容")
        
        logger.info(f"成功提取文本，長度: {len(content)} 字符")
        
        # 保存到數據庫
        document = Document(
            filename=safe_filename,  # 使用安全的文件名
            content=content,
            file_type=file.content_type,
            uploaded_by=1
        )
        
        db.add(document)
        db.commit()
        db.refresh(document)
        
        logger.info(f"文檔已保存到數據庫，ID: {document.id}")
        
        # 添加到 RAG 系統
        langchain_doc = LangchainDocument(
            page_content=content,
            metadata={
                "source": safe_filename,
                "document_id": document.id,
                "uploaded_by": 1,
                "content_type": file.content_type,
                "original_filename": file.filename
            }
        )
        
        await rag_system.add_documents([langchain_doc])
        logger.info(f"文檔已添加到 RAG 系統")
        
        # 標記為已處理
        document.is_processed = True
        db.commit()
        
        return {
            "message": "文件上傳成功", 
            "document_id": document.id,
            "filename": safe_filename,
            "content_length": len(content),
            "content_type": file.content_type
        }
        
    except HTTPException:
        # 重新拋出 HTTP 異常
        raise
    except Exception as e:
        logger.error(f"文件上傳失敗: {e}")
        # 清理可能已創建的文件
        try:
            if 'file_path' in locals() and os.path.exists(file_path):
                os.remove(file_path)
        except:
            pass
        raise HTTPException(status_code=500, detail=f"文件處理失敗: {str(e)}")

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
    
    # 從 RAG 系統中移除文檔（這會重建 FAISS 索引）
    try:
        rag_system.remove_document_by_id(document_id)
    except Exception as e:
        print(f"Warning: Failed to remove document from RAG system: {e}")
    
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
