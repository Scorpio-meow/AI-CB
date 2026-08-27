import json
from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from app.models import User, Conversation, Message, MessageResponse, ConversationResponse
from app.core.rag_manager import get_rag_system
from app.core.config import settings
DEFAULT_CONVERSATION_TITLE = settings.DEFAULT_CONVERSATION_TITLE
MAX_TITLE_PREVIEW_LENGTH = 50
def _build_message_response(msg: Message) -> MessageResponse:
    sources = []
    sources_detail = []
    research_trace = []
    attachments = []
    if msg.context_used:
        try:
            parsed = json.loads(msg.context_used)
            if isinstance(parsed, dict):
                sources = parsed.get("sources", [])
                sources_detail = parsed.get("sources_detail", [])
                research_trace = parsed.get("research_trace", [])
                attachments = parsed.get("attachments", [])
            elif isinstance(parsed, list):
                sources = parsed
        except Exception:
            pass
    return MessageResponse(
        id=msg.id,
        content=msg.content,
        is_user=msg.is_user,
        created_at=msg.created_at,
        context_used=msg.context_used,
        model_name=getattr(msg, "model_name", None),
        attachments=attachments,
        sources=sources,
        sources_detail=sources_detail,
        research_trace=research_trace
    )
class ChatService:
    def __init__(self):
        pass
    def _get_rag_system(self):
        return get_rag_system()
    async def create_conversation(self, db: Session, user_id: int, title: Optional[str] = None):
        conversation = Conversation(
            user_id=user_id,
            title=title or DEFAULT_CONVERSATION_TITLE,
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
        context_used: Optional[str] = None,
        model_name: Optional[str] = None
    ):
        if conversation_id is None:
            conversation = await self.create_conversation(db, user_id)
            conversation_id = conversation.id
        else:
            conversation = db.query(Conversation).filter(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id
            ).first()
            if not conversation:
                conversation = await self.create_conversation(db, user_id)
                conversation_id = conversation.id
        message = Message(
            conversation_id=conversation_id,
            content=content,
            is_user=is_user,
            created_at=datetime.utcnow(),
            context_used=context_used,
            model_name=model_name
        )
        db.add(message)
        conversation.updated_at = datetime.utcnow()
        if is_user and len(content) > 0:
            if conversation.title == DEFAULT_CONVERSATION_TITLE:
                conversation.title = content[:MAX_TITLE_PREVIEW_LENGTH] + "..." if len(content) > MAX_TITLE_PREVIEW_LENGTH else content
        db.commit()
        db.refresh(message)
        return message
    async def get_user_conversations(self, db: Session, user_id: int) -> List[ConversationResponse]:
        conversations = db.query(Conversation).filter(
            Conversation.user_id == user_id
        ).order_by(Conversation.updated_at.desc()).all()
        conv_ids = [conv.id for conv in conversations]
        if not conv_ids:
            return []
        all_messages = db.query(Message).filter(
            Message.conversation_id.in_(conv_ids)
        ).order_by(Message.conversation_id, Message.created_at.desc()).all()
        messages_by_conv = {}
        for msg in all_messages:
            if msg.conversation_id not in messages_by_conv:
                messages_by_conv[msg.conversation_id] = []
            if len(messages_by_conv[msg.conversation_id]) < 5:
                messages_by_conv[msg.conversation_id].append(msg)
        result = []
        for conv in conversations:
            recent_messages = messages_by_conv.get(conv.id, [])
            messages = [_build_message_response(msg) for msg in reversed(recent_messages)]
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
        conversation = db.query(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id
        ).first()
        if not conversation:
            return None
        messages = db.query(Message).filter(
            Message.conversation_id == conversation_id
        ).order_by(Message.created_at.asc()).all()
        message_responses = [_build_message_response(msg) for msg in messages]
        return ConversationResponse(
            id=conversation.id,
            title=conversation.title,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
            messages=message_responses
        )
    async def delete_conversation(self, db: Session, conversation_id: int, user_id: int) -> bool:
        conversation = db.query(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id
        ).first()
        if not conversation:
            return False
        db.query(Message).filter(Message.conversation_id == conversation_id).delete()
        db.delete(conversation)
        db.commit()
        rag_system = self._get_rag_system()
        memory_key = f"{user_id}:{conversation_id}"
        if hasattr(rag_system, 'context_memory') and memory_key in rag_system.context_memory:
            del rag_system.context_memory[memory_key]
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
        conversation = db.query(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id
        ).first()
        if not conversation:
            return []
        messages = db.query(Message).filter(
            Message.conversation_id == conversation_id
        ).order_by(Message.created_at.desc()).offset(offset).limit(limit).all()
        return [_build_message_response(msg) for msg in reversed(messages)]