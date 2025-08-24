from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from app.models.database import get_db
from app.models import Document, DocumentChunk
from app.rag.contextual_rag import ContextualRAG
from langchain.schema import Document as LangchainDocument
import os
import shutil
from typing import List

router = APIRouter()
rag_system = ContextualRAG()

@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """上傳文件到知識庫"""
    # 檢查文件類型
    allowed_types = ["text/plain", "application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="不支援的文件類型")
    
    try:
        # 保存文件
        upload_dir = "data/uploads"
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, file.filename)
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # 讀取文件內容
        content = ""
        if file.content_type == "text/plain":
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        # 這裡可以添加 PDF 和 DOCX 的處理邏輯
        
        # 保存到數據庫
        document = Document(
            filename=file.filename,
            content=content,
            file_type=file.content_type,
            uploaded_by=1
        )
        
        db.add(document)
        db.commit()
        db.refresh(document)
        
        # 添加到 RAG 系統
        langchain_doc = LangchainDocument(
            page_content=content,
            metadata={
                "source": file.filename,
                "document_id": document.id,
                "uploaded_by": 1
            }
        )
        
        rag_system.add_documents([langchain_doc])
        
        # 標記為已處理
        document.is_processed = True
        db.commit()
        
        return {"message": "文件上傳成功", "document_id": document.id}
        
    except Exception as e:
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
    
    # 刪除文件塊
    db.query(DocumentChunk).filter(DocumentChunk.document_id == document_id).delete()
    
    # 刪除文件記錄
    db.delete(document)
    db.commit()
    
    return {"message": "文件刪除成功"}
