import logging
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from app.services.chat_service import ChatService
logger = logging.getLogger(__name__)
chat_service = ChatService()
async def save_workflow_history(db: Session, user_id: int, initial_prompt: str, master_history: List[Dict[str, str]]) -> int:
    logger.info(f"Saving workflow history for user {user_id}...")
    title = f"工作流: {initial_prompt[:30]}..."
    
    conversation = await chat_service.create_conversation(db, user_id, title)
    
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
