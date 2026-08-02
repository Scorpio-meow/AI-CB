from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from app.models.database import get_db
from app.models import User, Conversation, Message, Document
from app.core.rag_manager import get_rag_system
from app.core.jwt_auth import get_current_admin_user
from app.core.cache import cache_response, invalidate_cache
from typing import List, Dict, Any
from datetime import datetime, timedelta
from pydantic import BaseModel
from functools import lru_cache
router = APIRouter()
class UserUpdate(BaseModel):
    username: str = None
    email: str = None
    is_active: bool = None
    is_admin: bool = None
@router.get("/users")
async def get_users(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user)
):
    users = db.query(User).all()
    return users
@router.get("/statistics")
@cache_response(ttl=180, key_prefix="admin_stats")
async def get_statistics(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user)
) -> Dict[str, Any]:
    from sqlalchemy import case
    
    user_stats = db.query(
        func.count(User.id).label('total'),
        func.sum(case((User.is_active == True, 1), else_=0)).label('active'),
        func.sum(case((User.is_admin == True, 1), else_=0)).label('admins')
    ).first()
    
    total_users = user_stats.total or 0
    active_users = user_stats.active or 0
    admin_users = user_stats.admins or 0
    
    total_conversations = db.query(func.count(Conversation.id)).scalar()
    total_messages = db.query(func.count(Message.id)).scalar()
    
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    recent_messages = db.query(func.count(Message.id)).filter(
        Message.created_at >= seven_days_ago
    ).scalar()
    
    doc_stats = db.query(
        func.count(Document.id).label('total'),
        func.sum(case((Document.is_processed == True, 1), else_=0)).label('processed')
    ).first()
    
    total_documents = doc_stats.total or 0
    processed_documents = doc_stats.processed or 0
    
    daily_query = db.query(
        func.date(Message.created_at).label('date'),
        func.count(Message.id).label('count')
    ).filter(
        Message.created_at >= seven_days_ago
    ).group_by(func.date(Message.created_at)).all()
    
    daily_counts = {str(row.date): row.count for row in daily_query}
    
    daily_stats = []
    for i in range(7):
        date = datetime.utcnow() - timedelta(days=i)
        date_str = date.strftime("%Y-%m-%d")
        daily_stats.append({
            "date": date_str,
            "messages": daily_counts.get(date_str, 0)
        })
    
    return {
        "users": {
            "total": total_users,
            "active": active_users,
            "admins": admin_users
        },
        "conversations": {
            "total": total_conversations,
        },
        "messages": {
            "total": total_messages,
            "recent_7_days": recent_messages
        },
        "documents": {
            "total": total_documents,
            "processed": processed_documents
        },
        "daily_stats": daily_stats
    }
@router.get("/conversations")
async def get_conversations(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user)
):
    conversations = db.query(Conversation).order_by(
        Conversation.updated_at.desc()
    ).limit(50).all()
    
    return conversations
@router.get("/conversations/{conversation_id}/messages")
async def get_conversation_messages(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user)
):
    messages = db.query(Message).filter(
        Message.conversation_id == conversation_id
    ).order_by(Message.created_at.asc()).all()
    
    return messages
@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user)
):
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="對話不存在")
    
    user_id = conversation.user_id
    
    db.query(Message).filter(Message.conversation_id == conversation_id).delete()
    
    db.delete(conversation)
    db.commit()
    
    rag_system = get_rag_system()
    memory_key = f"{user_id}:{conversation_id}"
    if hasattr(rag_system, 'context_memory') and memory_key in rag_system.context_memory:
        del rag_system.context_memory[memory_key]
    
    if hasattr(rag_system, 'context_memory') and conversation_id in rag_system.context_memory:
        del rag_system.context_memory[conversation_id]
    
    return {"message": "對話刪除成功"}
@router.get("/documents")
async def get_documents(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user)
):
    documents = db.query(Document).order_by(Document.created_at.desc()).all()
    return documents
@router.delete("/documents/{document_id}")
async def delete_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user)
):
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="文檔不存在")
    
    db.delete(document)
    db.commit()
    
    return {"message": "文檔刪除成功"}
@router.put("/users/{user_id}")
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用戶不存在")
    
    if user_update.username is not None:
        existing_user = db.query(User).filter(
            User.username == user_update.username, 
            User.id != user_id
        ).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="用戶名已存在")
        user.username = user_update.username
    
    if user_update.email is not None:
        existing_user = db.query(User).filter(
            User.email == user_update.email, 
            User.id != user_id
        ).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="郵箱已存在")
        user.email = user_update.email
    
    if user_update.is_active is not None:
        user.is_active = user_update.is_active
    
    if user_update.is_admin is not None:
        user.is_admin = user_update.is_admin
    
    db.commit()
    db.refresh(user)
    
    invalidate_cache("admin_stats")
    
    return {"message": "用戶更新成功", "user": user}
@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用戶不存在")
    
    rag_system = get_rag_system()
    conversations = db.query(Conversation).filter(Conversation.user_id == user_id).all()
    for conv in conversations:
        db.query(Message).filter(Message.conversation_id == conv.id).delete()
        
        memory_key = f"{user_id}:{conv.id}"
        if hasattr(rag_system, 'context_memory') and memory_key in rag_system.context_memory:
            del rag_system.context_memory[memory_key]
        
        if hasattr(rag_system, 'context_memory') and conv.id in rag_system.context_memory:
            del rag_system.context_memory[conv.id]
        
        db.delete(conv)
    
    db.delete(user)
    db.commit()
    
    invalidate_cache("admin_stats")
    
    return {"message": "用戶刪除成功"}
@router.get("/vector-store/info")
async def get_vector_store_info(
    current_user: dict = Depends(get_current_admin_user)
):
    rag_system = get_rag_system()
    return rag_system.get_vector_store_info()
@router.get("/rag-config")
async def get_rag_config(
    current_user: dict = Depends(get_current_admin_user)
):
    rag_system = get_rag_system()
    return {
        "chunk_size": rag_system.chunk_size,
        "chunk_overlap": rag_system.chunk_overlap,
        "top_k": rag_system.top_k,
        "similarity_threshold": rag_system.similarity_threshold,
        "rerank_top_k": rag_system.rerank_top_k,
        "final_k": rag_system.final_k,
        "hybrid_alpha": rag_system.hybrid_alpha,
        "rerank_weight": rag_system.rerank_weight,
        "final_threshold": rag_system.final_threshold,
        "normalization": rag_system.normalization,
        "batch_size": rag_system.batch_size,
        "embedding_dimension": rag_system.embedding_dimension,
        "reindex_threshold_hours": rag_system.reindex_threshold_hours,
        "device": str(rag_system.device),
        "use_faiss_gpu": rag_system.use_faiss_gpu
    }
@router.get("/vector-store/statistics")
async def get_vector_store_statistics(
    current_user: dict = Depends(get_current_admin_user)
):
    rag_system = get_rag_system()
    return rag_system.get_statistics()
@router.delete("/vector-store/clear")
async def clear_vector_store(
    current_user: dict = Depends(get_current_admin_user)
):
    rag_system = get_rag_system()
    rag_system.clear_vector_store()
    return {"message": "向量庫已清空"}
@router.post("/vector-store/reindex")
async def force_reindex(
    current_user: dict = Depends(get_current_admin_user)
):
    try:
        rag_system = get_rag_system()
        ok = rag_system.force_reindex()
        return {"message": "索引重建已觸發", "ok": bool(ok), "info": rag_system.get_vector_store_info()}
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.exception("強制索引重建失敗")
        raise HTTPException(status_code=500, detail="重建失敗: 內部錯誤，請聯繫系統管理員")
