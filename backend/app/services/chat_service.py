from sqlalchemy.orm import Session, joinedload
from app.models import User, Conversation, Message, MessageResponse, ConversationResponse
from app.core.rag_manager import get_rag_system
from typing import List, Optional
from datetime import datetime

class ChatService:
    def __init__(self):
        # Use global RAG instance for memory management
        pass
    
    def _get_rag_system(self):
        """Get the global RAG system instance."""
        return get_rag_system()
    
    async def create_conversation(self, db: Session, user_id: int, title: str = "新對話"):
        """創建新對話"""
        conversation = Conversation(
            user_id=user_id,
            title=title,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
        
        return conversation
    
    async def save_message(
        self, 
        db: Session, 
        user_id: int, 
        content: str, 
        is_user: bool, 
        conversation_id: Optional[int] = None,
        context_used: Optional[str] = None
    ):
        """保存消息到對話中"""
        # 如果沒有提供對話 ID，創建新對話
        if conversation_id is None:
            conversation = await self.create_conversation(db, user_id)
            conversation_id = conversation.id
        else:
            # 驗證對話是否屬於該用戶
            conversation = db.query(Conversation).filter(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id
            ).first()
            
            if not conversation:
                # 如果對話不存在或不屬於該用戶，創建新對話
                conversation = await self.create_conversation(db, user_id)
                conversation_id = conversation.id
        
        # 創建消息
        message = Message(
            conversation_id=conversation_id,
            content=content,
            is_user=is_user,
            created_at=datetime.utcnow(),
            context_used=context_used
        )
        
        db.add(message)
        
        # 更新對話的最後更新時間
        conversation.updated_at = datetime.utcnow()
        if is_user and len(content) > 0:
            # 如果是用戶消息且不為空，可以更新對話標題
            if conversation.title == "新對話":
                conversation.title = content[:50] + "..." if len(content) > 50 else content
        
        db.commit()
        db.refresh(message)
        
        return message
    
    async def get_user_conversations(self, db: Session, user_id: int) -> List[ConversationResponse]:
        """獲取用戶的所有對話 (優化版 - 使用 subquery 避免 N+1)"""
        # 使用 joinedload 預載入最近的消息，避免 N+1 查詢問題
        from sqlalchemy import select, and_
        from sqlalchemy.orm import aliased
        
        # 先獲取所有對話
        conversations = db.query(Conversation).filter(
            Conversation.user_id == user_id
        ).order_by(Conversation.updated_at.desc()).all()
        
        # 批次獲取所有對話的最近消息（單次查詢）
        conv_ids = [conv.id for conv in conversations]
        if not conv_ids:
            return []
        
        # 使用窗口函數或子查詢獲取每個對話的最近5條消息
        from sqlalchemy import func
        
        # 獲取所有相關消息並在 Python 中處理（比多次查詢更高效）
        all_messages = db.query(Message).filter(
            Message.conversation_id.in_(conv_ids)
        ).order_by(Message.conversation_id, Message.created_at.desc()).all()
        
        # 將消息按對話分組
        messages_by_conv = {}
        for msg in all_messages:
            if msg.conversation_id not in messages_by_conv:
                messages_by_conv[msg.conversation_id] = []
            if len(messages_by_conv[msg.conversation_id]) < 5:
                messages_by_conv[msg.conversation_id].append(msg)
        
        result = []
        for conv in conversations:
            # 獲取該對話的最近消息
            recent_messages = messages_by_conv.get(conv.id, [])
            
            messages = [
                MessageResponse(
                    id=msg.id,
                    content=msg.content,
                    is_user=msg.is_user,
                    created_at=msg.created_at,
                    context_used=msg.context_used
                ) for msg in reversed(recent_messages)
            ]
            
            result.append(ConversationResponse(
                id=conv.id,
                title=conv.title,
                created_at=conv.created_at,
                updated_at=conv.updated_at,
                messages=messages
            ))
        
        return result
    
    async def get_conversation_with_messages(
        self, 
        db: Session, 
        conversation_id: int, 
        user_id: int
    ) -> Optional[ConversationResponse]:
        """獲取對話及其所有消息"""
        conversation = db.query(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id
        ).first()
        
        if not conversation:
            return None
        
        messages = db.query(Message).filter(
            Message.conversation_id == conversation_id
        ).order_by(Message.created_at.asc()).all()
        
        message_responses = [
            MessageResponse(
                id=msg.id,
                content=msg.content,
                is_user=msg.is_user,
                created_at=msg.created_at,
                context_used=msg.context_used
            ) for msg in messages
        ]
        
        return ConversationResponse(
            id=conversation.id,
            title=conversation.title,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
            messages=message_responses
        )
    
    async def delete_conversation(self, db: Session, conversation_id: int, user_id: int) -> bool:
        """刪除對話"""
        conversation = db.query(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id
        ).first()
        
        if not conversation:
            return False
        
        # 刪除對話中的所有消息
        db.query(Message).filter(Message.conversation_id == conversation_id).delete()
        
        # 刪除對話
        db.delete(conversation)
        db.commit()
        
        # 清理 RAG 系統中的對話上下文記憶
        rag_system = self._get_rag_system()
        # 清理新格式的記憶體 key (user_id:conversation_id)
        memory_key = f"{user_id}:{conversation_id}"
        if hasattr(rag_system, 'context_memory') and memory_key in rag_system.context_memory:
            del rag_system.context_memory[memory_key]
        
        # 清理舊格式的記憶體 key (conversation_id only) - 向後兼容
        if hasattr(rag_system, 'context_memory') and conversation_id in rag_system.context_memory:
            del rag_system.context_memory[conversation_id]
        
        return True
    
    async def get_conversation_messages(
        self, 
        db: Session, 
        conversation_id: int, 
        user_id: int,
        limit: int = 20,
        offset: int = 0
    ) -> List[MessageResponse]:
        """分頁獲取對話消息"""
        # 驗證對話所有權
        conversation = db.query(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id
        ).first()
        
        if not conversation:
            return []
        
        messages = db.query(Message).filter(
            Message.conversation_id == conversation_id
        ).order_by(Message.created_at.desc()).offset(offset).limit(limit).all()
        
        return [
            MessageResponse(
                id=msg.id,
                content=msg.content,
                is_user=msg.is_user,
                created_at=msg.created_at,
                context_used=msg.context_used
            ) for msg in reversed(messages)
        ]
