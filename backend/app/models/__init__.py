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
    role = Column(String, default="user")
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    
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
    is_user = Column(Boolean)
    created_at = Column(DateTime, default=datetime.utcnow)
    context_used = Column(Text)
    model_name = Column(String, nullable=True)
    
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
class CustomApiTool(Base):
    __tablename__ = "custom_api_tools"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    display_name = Column(String)
    description = Column(Text)
    category = Column(String, default="custom_api")
    method = Column(String, default="GET")
    url = Column(String)
    base_url = Column(String, nullable=True)
    path = Column(String, nullable=True)
    headers = Column(Text, nullable=True)
    auth_type = Column(String, default="none")
    auth_config = Column(Text, nullable=True)
    parameters_schema = Column(Text, nullable=True)
    request_body_schema = Column(Text, nullable=True)
    param_locations = Column(Text, nullable=True)
    response_mapping = Column(Text, nullable=True)
    is_enabled = Column(Boolean, default=True)
    timeout = Column(Integer, default=15)
    spec_version = Column(String, nullable=True)
    raw_spec = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
class McpServer(Base):
    __tablename__ = "mcp_servers"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    display_name = Column(String)
    description = Column(Text, nullable=True)
    transport_type = Column(String, default="stdio")
    command = Column(String, nullable=True)
    args = Column(Text, nullable=True)
    env_vars = Column(Text, nullable=True)
    url = Column(String, nullable=True)
    headers = Column(Text, nullable=True)
    is_enabled = Column(Boolean, default=True)
    status = Column(String, default="disconnected")
    last_error = Column(Text, nullable=True)
    discovered_tools = Column(Text, nullable=True)
    timeout = Column(Integer, default=30)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
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
    data_url: Optional[str] = None
    content: Optional[str] = None
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
class CustomApiToolCreate(BaseModel):
    name: str
    display_name: str
    description: str
    category: Optional[str] = "custom_api"
    method: Optional[str] = "GET"
    url: str
    base_url: Optional[str] = None
    path: Optional[str] = None
    headers: Optional[Dict[str, str]] = None
    auth_type: Optional[str] = "none"
    auth_config: Optional[Dict[str, Any]] = None
    parameters_schema: Optional[Dict[str, Any]] = None
    request_body_schema: Optional[Dict[str, Any]] = None
    param_locations: Optional[Dict[str, str]] = None
    response_mapping: Optional[str] = None
    is_enabled: Optional[bool] = True
    timeout: Optional[int] = 15
    spec_version: Optional[str] = "manual"
    raw_spec: Optional[str] = None
class CustomApiToolUpdate(BaseModel):
    name: Optional[str] = None
    display_name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    method: Optional[str] = None
    url: Optional[str] = None
    base_url: Optional[str] = None
    path: Optional[str] = None
    headers: Optional[Dict[str, str]] = None
    auth_type: Optional[str] = None
    auth_config: Optional[Dict[str, Any]] = None
    parameters_schema: Optional[Dict[str, Any]] = None
    request_body_schema: Optional[Dict[str, Any]] = None
    param_locations: Optional[Dict[str, str]] = None
    response_mapping: Optional[str] = None
    is_enabled: Optional[bool] = None
    timeout: Optional[int] = None
class CustomApiToolResponse(BaseModel):
    id: int
    name: str
    display_name: str
    description: str
    category: str
    method: str
    url: str
    base_url: Optional[str] = None
    path: Optional[str] = None
    headers: Optional[Dict[str, str]] = None
    auth_type: str
    auth_config: Optional[Dict[str, Any]] = None
    parameters_schema: Optional[Dict[str, Any]] = None
    request_body_schema: Optional[Dict[str, Any]] = None
    param_locations: Optional[Dict[str, str]] = None
    response_mapping: Optional[str] = None
    is_enabled: bool
    timeout: int
    spec_version: Optional[str] = None
    created_at: datetime
    updated_at: datetime
class OpenApiParseRequest(BaseModel):
    spec_content_or_url: str
    default_base_url: Optional[str] = None
class OpenApiImportItem(BaseModel):
    name: str
    display_name: str
    description: str
    method: str
    path: str
    base_url: Optional[str] = None
    full_url: str
    headers: Optional[Dict[str, str]] = None
    auth_type: Optional[str] = "none"
    auth_config: Optional[Dict[str, Any]] = None
    parameters_schema: Optional[Dict[str, Any]] = None
    request_body_schema: Optional[Dict[str, Any]] = None
    param_locations: Optional[Dict[str, str]] = None
    spec_version: Optional[str] = None
class OpenApiImportRequest(BaseModel):
    tools: List[OpenApiImportItem]
    global_base_url: Optional[str] = None
    global_headers: Optional[Dict[str, str]] = None
    global_auth_type: Optional[str] = "none"
    global_auth_config: Optional[Dict[str, Any]] = None
class ToolTestRequest(BaseModel):
    arguments: Optional[Dict[str, Any]] = {}
class McpServerCreate(BaseModel):
    name: str
    display_name: str
    description: Optional[str] = None
    transport_type: Optional[str] = "stdio"
    command: Optional[str] = None
    args: Optional[List[str]] = None
    env_vars: Optional[Dict[str, str]] = None
    url: Optional[str] = None
    headers: Optional[Dict[str, str]] = None
    is_enabled: Optional[bool] = True
    timeout: Optional[int] = 30
class McpServerUpdate(BaseModel):
    display_name: Optional[str] = None
    description: Optional[str] = None
    transport_type: Optional[str] = None
    command: Optional[str] = None
    args: Optional[List[str]] = None
    env_vars: Optional[Dict[str, str]] = None
    url: Optional[str] = None
    headers: Optional[Dict[str, str]] = None
    is_enabled: Optional[bool] = None
    timeout: Optional[int] = None
class McpServerResponse(BaseModel):
    id: int
    name: str
    display_name: str
    description: Optional[str] = None
    transport_type: str
    command: Optional[str] = None
    args: Optional[List[str]] = None
    env_vars: Optional[Dict[str, str]] = None
    url: Optional[str] = None
    headers: Optional[Dict[str, str]] = None
    is_enabled: bool
    status: str
    last_error: Optional[str] = None
    discovered_tools: Optional[List[Dict[str, Any]]] = None
    timeout: int
    created_at: datetime
    updated_at: datetime
class McpToolTestRequest(BaseModel):
    arguments: Optional[Dict[str, Any]] = {}