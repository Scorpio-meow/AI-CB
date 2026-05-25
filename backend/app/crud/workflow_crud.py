import logging
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from app.services.chat_service import ChatService

logger = logging.getLogger(__name__)
chat_service = ChatService()

async def save_workflow_history(db: Session, user_id: int, initial_prompt: str, master_history: List[Dict[str, str]]) -> int:
    """
    將工作流的執行歷史記錄保存到對話和消息數據庫表中。
    
    :param db: 數據庫 session
    :param user_id: 用戶 ID
    :param initial_prompt: 初始工作流 prompt
    :param master_history: 節點執行的完整歷史列表
    :return: 創建的 conversation ID
    """
    logger.info(f"Saving workflow history for user {user_id}...")
    title = f"工作流: {initial_prompt[:30]}..."
    
    # 創建一個新的對話紀錄
    conversation = await chat_service.create_conversation(db, user_id, title)
    
    # 保存工作流中所有節點的對話訊息
    for msg in master_history:
        role = msg.get("role", "Unknown")
        content = msg.get("content", "")
        
        is_user = role == "User"
        formatted_content = f"**【{role}】**\n\n{content}"
        
        await chat_service.save_message(
            db, 
            user_id, 
            formatted_content, 
            is_user, 
            conversation.id
        )
        
    logger.info(f"Workflow history successfully saved to conversation ID: {conversation.id}")
    return conversation.id
