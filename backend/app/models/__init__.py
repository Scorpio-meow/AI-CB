from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from .database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    role = Column(String, default="user")  # user, admin, moderator
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)  # 追蹤最後登入時間
    
    conversations = relationship("Conversation", back_populates="user")

class Conversation(Base):
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    title = Column(String, default="New Conversation")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation")

class Message(Base):
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), index=True)
    content = Column(Text)
    is_user = Column(Boolean)  # True if from user, False if from bot
    created_at = Column(DateTime, default=datetime.utcnow)
    context_used = Column(Text)  # Store RAG context used
    model_name = Column(String, nullable=True)  # 選用模型名稱（兼容舊資料）
    
    conversation = relationship("Conversation", back_populates="messages")

class Document(Base):
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String)
    content = Column(Text)
    file_type = Column(String)
    description = Column(Text, nullable=True)
    uploaded_by = Column(Integer, ForeignKey("users.id"), index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_processed = Column(Boolean, default=False)

# Pydantic models for API
class UserCreate(BaseModel):
    username: str
    email: str
    password: str

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    is_active: bool
    is_admin: bool
    created_at: datetime

class FileAttachment(BaseModel):
    filename: str
    file_type: str
    file_size: Optional[int] = None
    data_url: Optional[str] = None  # Base64 Data URL (如 data:image/png;base64,...)
    content: Optional[str] = None   # 預先抽取或解析後的文本內容

class MessageCreate(BaseModel):
    content: str
    conversation_id: Optional[int] = None
    model_name: Optional[str] = None
    reasoning_effort: Optional[str] = "medium"
    attachments: Optional[List[FileAttachment]] = []

class MessageResponse(BaseModel):
    id: int
    content: str
    is_user: bool
    created_at: datetime
    context_used: Optional[str] = None
    model_name: Optional[str] = None
    reasoning_effort: Optional[str] = None
    attachments: Optional[List[FileAttachment]] = None
    sources: Optional[List[str]] = None
    sources_detail: Optional[List[Dict[str, Any]]] = None
    research_trace: Optional[List[Dict[str, Any]]] = None

class ConversationResponse(BaseModel):
    id: int
    title: str
    created_at: datetime
    updated_at: datetime
    messages: List[MessageResponse] = []

class ChatResponse(BaseModel):
    message: MessageResponse
    conversation_id: int
