from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
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
from app.core.config import settings
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
    from app.core.llm_client import get_available_models as get_configured_models
    configured_models = get_configured_models()
    if not configured_models:
        from app.api.tags import _fetch_remote_models
        try:
            remote_models, _ = _fetch_remote_models()
            if remote_models:
                configured_models = remote_models
        except Exception:
            pass
    azure_dep = settings.AZURE_OPENAI_DEPLOYMENT.split(',')[0].strip() if settings.AZURE_OPENAI_DEPLOYMENT else None
    default_model = settings.MODEL_NAME or azure_dep or (configured_models[0] if configured_models else "")
    if default_model and configured_models and default_model not in configured_models:
        default_model = configured_models[0]
    return {
        "models": configured_models or [],
        "default": default_model
    }
@router.get("/tools")
async def get_available_tools():
    """獲取 AI 系統當前已註冊並啟用的所有工具定義清單與說明"""
    try:
        rag_system = get_rag_system()
        if hasattr(rag_system, "agent_coordinator") and rag_system.agent_coordinator:
            tool_defs = rag_system.agent_coordinator.tool_registry.get_tool_definitions()
        else:
            from app.rag.tools import ResearchToolRegistry
            tool_defs = ResearchToolRegistry(getattr(rag_system, "retriever", None)).get_tool_definitions()
        return {
            "status": "success",
            "tools": tool_defs
        }
    except Exception as e:
        logger.error(f"取得可用工具清單失敗: {e}")
        from app.rag.tools import ResearchToolRegistry
        tool_defs = ResearchToolRegistry().get_tool_definitions()
        return {
            "status": "partial",
            "tools": tool_defs,
            "error": str(e)
        }
@router.post("/send")
async def send_message(
    message_data: MessageCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    user_context = None
    if message_data.attachments:
        user_context = json.dumps({
            "attachments": [att.dict() for att in message_data.attachments]
        }, ensure_ascii=False)
    user_message = await chat_service.save_message(
        db,
        user_id,
        message_data.content,
        True,
        message_data.conversation_id,
        context_used=user_context,
        model_name=message_data.model_name,
    )
    conv_id = user_message.conversation_id
    async def sse_generator():
        yield f"event: start\ndata: {json.dumps({'conversation_id': conv_id, 'user_message_id': user_message.id}, ensure_ascii=False)}\n\n"
        rag_system = get_rag_system()
        collected_tokens = ""
        collected_sources = []
        collected_sources_detail = []
        collected_research_trace = []
        try:
            async for event_item in rag_system.generate_response_stream(
                message_data.content,
                conv_id,
                message_data.model_name,
                user_id,
                reasoning_effort=message_data.reasoning_effort,
                attachments=message_data.attachments
            ):
                ev = event_item.get("event")
                data = event_item.get("data", {})
                if ev == "step_start":
                    yield f"event: step_start\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
                elif ev == "step_end":
                    collected_research_trace.append(data)
                    yield f"event: step_end\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
                elif ev == "token":
                    collected_tokens += data.get("content", "")
                    yield f"event: token\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
                elif ev == "sources":
                    collected_sources = data.get("sources", [])
                    collected_sources_detail = data.get("sources_detail", [])
                    yield f"event: sources\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
                elif ev == "done":
                    if not collected_tokens:
                        collected_tokens = data.get("answer", "")
                    if not collected_sources:
                        collected_sources = data.get("sources", [])
                        collected_sources_detail = data.get("sources_detail", [])
                    if not collected_research_trace:
                        collected_research_trace = data.get("research_trace", [])
            context_payload = json.dumps({
                "sources": collected_sources,
                "sources_detail": collected_sources_detail,
                "research_trace": collected_research_trace
            }, ensure_ascii=False)
            bot_message = await chat_service.save_message(
                db,
                user_id,
                collected_tokens,
                False,
                conv_id,
                context_payload,
                model_name=message_data.model_name,
            )
            done_payload = {
                "message_id": bot_message.id,
                "conversation_id": conv_id,
                "answer": collected_tokens,
                "sources": collected_sources,
                "sources_detail": collected_sources_detail,
                "research_trace": collected_research_trace
            }
            yield f"event: done\ndata: {json.dumps(done_payload, ensure_ascii=False)}\n\n"
        except Exception as e:
            logger.exception("處理訊息串流時發生錯誤")
            err_payload = {"detail": f"處理訊息時發生錯誤: {str(e)}"}
            yield f"event: error\ndata: {json.dumps(err_payload, ensure_ascii=False)}\n\n"
    return StreamingResponse(
        sse_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
@router.get("/conversations", response_model=List[ConversationResponse])
async def get_conversations(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    conversations = await chat_service.get_user_conversations(db, user_id)
    return conversations
@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
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
    messages = await chat_service.get_conversation_messages(db, conversation_id, user_id, limit=limit, offset=offset)
    return messages
@router.post("/conversations", response_model=ConversationResponse)
async def create_conversation(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
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
    success = await chat_service.delete_conversation(db, conversation_id, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="找不到該對話")
    
    return {"message": "對話已刪除"}
@router.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int):
    try:
        await manager.connect(websocket, user_id)
        
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            response = {
                "type": "message",
                "content": f"收到消息: {message_data['content']}",
                "timestamp": "now"
            }
            
            await manager.send_personal_message(json.dumps(response), user_id)
            
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)
    except Exception as e:
        print(f"WebSocket 錯誤: {e}")
        manager.disconnect(websocket, user_id)
