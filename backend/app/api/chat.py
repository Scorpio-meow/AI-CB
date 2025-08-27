from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.models.database import get_db
from app.models import MessageCreate, MessageResponse, ChatResponse, ConversationResponse
from app.services.auth_service import AuthService
from app.services.chat_service import ChatService
from app.rag.contextual_rag import HybridContextualRAG
from typing import List
import json

router = APIRouter()
security = HTTPBearer()
auth_service = AuthService()
chat_service = ChatService()
rag_system = HybridContextualRAG()

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

@router.post("/send", response_model=ChatResponse)
async def send_message(
    message_data: MessageCreate,
    db: Session = Depends(get_db)
):
    """發送聊天消息"""
    try:
        # 保存用戶消息（使用預設用戶 ID 1）
        user_message = await chat_service.save_message(
            db, 1, message_data.content, True, message_data.conversation_id
        )
        
        # 使用 RAG 系統生成回應
        rag_response = await rag_system.generate_response(
            message_data.content, 
            user_message.conversation_id
        )
        
        # 保存機器人回應
        bot_message = await chat_service.save_message(
            db, 1, rag_response["answer"], False, 
            user_message.conversation_id, rag_response["context_used"]
        )
        
        return ChatResponse(
            message=MessageResponse(
                id=bot_message.id,
                content=bot_message.content,
                is_user=bot_message.is_user,
                created_at=bot_message.created_at,
                context_used=bot_message.context_used
            ),
            conversation_id=user_message.conversation_id
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"處理消息時發生錯誤: {str(e)}")

@router.get("/conversations", response_model=List[ConversationResponse])
async def get_conversations(
    db: Session = Depends(get_db)
):
    """獲取所有對話"""
    conversations = await chat_service.get_user_conversations(db, 1)
    return conversations

@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: int,
    db: Session = Depends(get_db)
):
    """獲取特定對話的詳細信息"""
    conversation = await chat_service.get_conversation_with_messages(db, conversation_id, 1)
    if not conversation:
        raise HTTPException(status_code=404, detail="找不到該對話")
    
    return conversation

@router.post("/conversations", response_model=ConversationResponse)
async def create_conversation(
    db: Session = Depends(get_db)
):
    """建立新對話"""
    conversation = await chat_service.create_conversation(db, 1)
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
    db: Session = Depends(get_db)
):
    """刪除對話"""
    success = await chat_service.delete_conversation(db, conversation_id, 1)
    if not success:
        raise HTTPException(status_code=404, detail="找不到該對話")
    
    return {"message": "對話已刪除"}

@router.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int, token: str):
    """WebSocket 連接用於即時聊天"""
    # 驗證 token（簡化版本）
    try:
        # 這裡應該驗證 JWT token，但為了簡化，我們跳過
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
