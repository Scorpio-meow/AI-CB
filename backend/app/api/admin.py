from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from app.models.database import get_db
from app.models import User, Conversation, Message, Document
from app.core.rag_manager import get_rag_system
from app.core.jwt_auth import get_current_admin_user  # 改用 JWT 認證
from app.core.cache import cache_response, invalidate_cache  # 快取支援
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
    current_user: dict = Depends(get_current_admin_user)  # JWT 管理員認證
):
    """獲取所有用戶列表 - 需要管理員權限"""
    users = db.query(User).all()
    return users

@router.get("/statistics")
@cache_response(ttl=180, key_prefix="admin_stats")  # 快取 3 分鐘
async def get_statistics(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user)  # JWT 管理員認證
) -> Dict[str, Any]:
    """獲取系統統計信息 (優化版 - 使用批次查詢)"""
    # 使用單次查詢獲取多個計數，避免多次往返資料庫
    from sqlalchemy import case
    
    # 優化：使用一次查詢獲取用戶統計
    user_stats = db.query(
        func.count(User.id).label('total'),
        func.sum(case((User.is_active == True, 1), else_=0)).label('active'),
        func.sum(case((User.is_admin == True, 1), else_=0)).label('admins')
    ).first()
    
    total_users = user_stats.total or 0
    active_users = user_stats.active or 0
    admin_users = user_stats.admins or 0
    
    # 優化：批次獲取對話和消息統計
    total_conversations = db.query(func.count(Conversation.id)).scalar()
    total_messages = db.query(func.count(Message.id)).scalar()
    
    # 最近7天的消息統計 - 優化為單次查詢
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    recent_messages = db.query(func.count(Message.id)).filter(
        Message.created_at >= seven_days_ago
    ).scalar()
    
    # 優化：使用單次查詢獲取文檔統計
    doc_stats = db.query(
        func.count(Document.id).label('total'),
        func.sum(case((Document.is_processed == True, 1), else_=0)).label('processed')
    ).first()
    
    total_documents = doc_stats.total or 0
    processed_documents = doc_stats.processed or 0
    
    # 優化：使用單次 GROUP BY 查詢獲取每日統計
    daily_query = db.query(
        func.date(Message.created_at).label('date'),
        func.count(Message.id).label('count')
    ).filter(
        Message.created_at >= seven_days_ago
    ).group_by(func.date(Message.created_at)).all()
    
    # 創建日期到計數的映射
    daily_counts = {str(row.date): row.count for row in daily_query}
    
    # 填充所有7天的數據
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
            "total_messages": total_messages,
            "recent_messages": recent_messages
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
    """獲取所有對話列表 - 需要管理員權限"""
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
    """獲取特定對話的消息 - 需要管理員權限"""
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
    """刪除對話 - 需要管理員權限"""
    # 獲取對話信息用於清理記憶體
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="對話不存在")
    
    user_id = conversation.user_id
    
    # 刪除對話中的所有消息
    db.query(Message).filter(Message.conversation_id == conversation_id).delete()
    
    # 刪除對話
    db.delete(conversation)
    db.commit()
    
    # 清理 RAG 系統中的對話上下文記憶
    rag_system = get_rag_system()
    # 清理新格式的記憶體 key (user_id:conversation_id)
    memory_key = f"{user_id}:{conversation_id}"
    if hasattr(rag_system, 'context_memory') and memory_key in rag_system.context_memory:
        del rag_system.context_memory[memory_key]
    
    # 清理舊格式的記憶體 key (conversation_id only) - 向後兼容
    if hasattr(rag_system, 'context_memory') and conversation_id in rag_system.context_memory:
        del rag_system.context_memory[conversation_id]
    
    return {"message": "對話刪除成功"}

@router.get("/documents")
async def get_documents(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user)
):
    """獲取所有文檔列表 - 需要管理員權限"""
    documents = db.query(Document).order_by(Document.created_at.desc()).all()
    return documents

@router.delete("/documents/{document_id}")
async def delete_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user)
):
    """刪除文檔 - 需要管理員權限"""
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
    """更新用戶信息 - 需要管理員權限"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用戶不存在")
    
    # 更新用戶信息
    if user_update.username is not None:
        # 檢查用戶名是否已存在
        existing_user = db.query(User).filter(
            User.username == user_update.username, 
            User.id != user_id
        ).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="用戶名已存在")
        user.username = user_update.username
    
    if user_update.email is not None:
        # 檢查郵箱是否已存在
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
    
    return {"message": "用戶更新成功", "user": user}

@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user)
):
    """刪除用戶 - 需要管理員權限"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用戶不存在")
    
    # 刪除用戶的所有對話和消息，並清理對應的記憶體
    rag_system = get_rag_system()
    conversations = db.query(Conversation).filter(Conversation.user_id == user_id).all()
    for conv in conversations:
        db.query(Message).filter(Message.conversation_id == conv.id).delete()
        
        # 清理 RAG 系統中的對話上下文記憶
        # 清理新格式的記憶體 key (user_id:conversation_id)
        memory_key = f"{user_id}:{conv.id}"
        if hasattr(rag_system, 'context_memory') and memory_key in rag_system.context_memory:
            del rag_system.context_memory[memory_key]
        
        # 清理舊格式的記憶體 key (conversation_id only) - 向後兼容
        if hasattr(rag_system, 'context_memory') and conv.id in rag_system.context_memory:
            del rag_system.context_memory[conv.id]
        
        db.delete(conv)
    
    # 刪除用戶
    db.delete(user)
    db.commit()
    
    return {"message": "用戶刪除成功"}

@router.get("/vector-store/info")
async def get_vector_store_info(
    current_user: dict = Depends(get_current_admin_user)
):
    """獲取向量庫信息 - 需要管理員權限"""
    rag_system = get_rag_system()
    return rag_system.get_vector_store_info()

@router.get("/vector-store/statistics")
async def get_vector_store_statistics(
    current_user: dict = Depends(get_current_admin_user)
):
    """獲取向量庫統計信息 - 需要管理員權限"""
    rag_system = get_rag_system()
    return rag_system.get_statistics()

@router.delete("/vector-store/clear")
async def clear_vector_store(
    current_user: dict = Depends(get_current_admin_user)
):
    """清空向量庫 - 需要管理員權限"""
    rag_system = get_rag_system()
    rag_system.clear_vector_store()
    return {"message": "向量庫已清空"}

@router.post("/vector-store/reindex")
async def force_reindex(
    current_user: dict = Depends(get_current_admin_user)
):
    """重建向量與BM25索引（基於現有 documents.pkl）- 需要管理員權限"""
    try:
        rag_system = get_rag_system()
        ok = rag_system.force_reindex()
        return {"message": "索引重建已觸發", "ok": bool(ok), "info": rag_system.get_vector_store_info()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"重建失敗: {e}")
