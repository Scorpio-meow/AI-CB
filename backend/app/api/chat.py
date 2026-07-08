from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from app.models.database import get_db
from app.models import MessageCreate, MessageResponse, ChatResponse, ConversationResponse
from app.services.chat_service import ChatService
from app.core.rag_manager import get_rag_system
from app.core.user_context import get_current_user_id, get_default_user_id
from typing import List
import logging

logger = logging.getLogger(__name__)
import json
import os

router = APIRouter()
chat_service = ChatService()

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.user_connections: dict = {}

    async def connect(self, websocket: WebSocket, user_id: int):
        await websocket.accept()
        self.active_connections.append(websocket)
        self.user_connections[user_id] = websocket

    def disconnect(self, websocket: WebSocket, user_id: int = None):
        self.active_connections.remove(websocket)
        if user_id and user_id in self.user_connections:
            del self.user_connections[user_id]

    async def send_personal_message(self, message: str, user_id: int):
        if user_id in self.user_connections:
            await self.user_connections[user_id].send_text(message)

manager = ConnectionManager()

@router.get("/models")
async def get_available_models():
    """獲取可用的模型列表"""
    from app.core.llm_client import get_available_models as get_configured_models
    configured_models = get_configured_models()
    if configured_models:
        default_model = os.getenv("MODEL_NAME") or os.getenv("AZURE_OPENAI_DEPLOYMENT") or configured_models[0]
        if default_model not in configured_models:
            default_model = configured_models[0]
        return {
            "models": configured_models,
            "default": default_model
        }
        
    available_models_str = os.getenv("AVAILABLE_MODELS", "gemma4:26b,qwen3.6:27b,glm-5.2,laguna-xs-2.1")
    models = [model.strip() for model in available_models_str.split(",")]
    default_model = os.getenv("MODEL_NAME", "gemma4:26b")
    
    return {
        "models": models,
        "default": default_model
    }

@router.post("/send", response_model=ChatResponse)
async def send_message(
    message_data: MessageCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """發送聊天消息"""
    try:
        # 保存用戶消息（使用從header獲取的用戶ID，默認為1）
        user_message = await chat_service.save_message(
            db,
            user_id,
            message_data.content,
            True,
            message_data.conversation_id,
            model_name=message_data.model_name,
        )
        
        # 使用 RAG 系統生成回應（支援模型選擇）
        # Pass user_id into RAG so context is scoped per-user+conversation
        rag_system = get_rag_system()
        rag_response = await rag_system.generate_response(
            message_data.content,
            user_message.conversation_id,
            message_data.model_name,
            user_id
        )
        
        # 保存機器人回應
        bot_message = await chat_service.save_message(
            db,
            user_id,
            rag_response["answer"],
            False,
            user_message.conversation_id,
            rag_response["context_used"],
            model_name=message_data.model_name,
        )
        
        return ChatResponse(
            message=MessageResponse(
                id=bot_message.id,
                content=bot_message.content,
                is_user=bot_message.is_user,
                created_at=bot_message.created_at,
                context_used=bot_message.context_used,
                model_name=getattr(bot_message, "model_name", None)
            ),
            conversation_id=user_message.conversation_id
        )
        
    except Exception as e:
        logger.exception("處理消息時發生錯誤")
        raise HTTPException(status_code=500, detail="處理消息時發生錯誤: 內部錯誤，請聯繫系統管理員")

@router.get("/conversations", response_model=List[ConversationResponse])
async def get_conversations(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """獲取所有對話"""
    conversations = await chat_service.get_user_conversations(db, user_id)
    return conversations

@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """獲取特定對話的詳細信息"""
    conversation = await chat_service.get_conversation_with_messages(db, conversation_id, user_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="找不到該對話")
    
    return conversation


@router.get("/conversations/{conversation_id}/messages")
async def get_conversation_messages_endpoint(
    conversation_id: int,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """分頁獲取單個對話的消息（避免一次載入大量訊息）"""
    messages = await chat_service.get_conversation_messages(db, conversation_id, user_id, limit=limit, offset=offset)
    return messages

@router.post("/conversations", response_model=ConversationResponse)
async def create_conversation(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """建立新對話"""
    conversation = await chat_service.create_conversation(db, user_id)
    return ConversationResponse(
        id=conversation.id,
        title=conversation.title,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        messages=[]
    )

@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """刪除對話"""
    success = await chat_service.delete_conversation(db, conversation_id, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="找不到該對話")
    
    return {"message": "對話已刪除"}

@router.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int):
    """WebSocket 連接用於即時聊天（不使用 JWT 驗證）"""
    try:
        await manager.connect(websocket, user_id)
        
        while True:
            # 接收消息
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            # 處理消息（這裡可以集成 RAG 系統）
            response = {
                "type": "message",
                "content": f"收到消息: {message_data['content']}",
                "timestamp": "now"
            }
            
            # 發送回應
            await manager.send_personal_message(json.dumps(response), user_id)
            
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)
    except Exception as e:
        print(f"WebSocket 錯誤: {e}")
        manager.disconnect(websocket, user_id)
