from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.models.database import get_db
from app.schemas.custom_agent import CustomAgent, CustomAgentCreate, CustomAgentUpdate
from app.crud import crud_custom_agent
from app.core.jwt_auth import get_current_active_user
router = APIRouter()
def _populate_creator_username(agent) -> dict:
    agent_dict = {
        "id": agent.id,
        "name": agent.name,
        "role": agent.role,
        "expertise": agent.expertise,
        "prompt": agent.prompt,
        "tools": agent.tools,
        "is_public": agent.is_public,
        "created_by": agent.created_by,
        "creator_username": agent.creator.username if agent.creator else None
    }
    return agent_dict
@router.get("/all_with_details", response_model=List[CustomAgent], summary="獲取所有自訂 Agent 詳情")
def read_all_agents_with_details(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_active_user)
):
    user_id = current_user.get("user_id")
    custom_agents = crud_custom_agent.get_custom_agents(db, limit=1000, user_id=user_id)
    return [_populate_creator_username(agent) for agent in custom_agents]
@router.post("/", response_model=CustomAgent, summary="創建新的自訂 Agent")
def create_custom_agent(
    agent: CustomAgentCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_active_user)
):
    user_id = current_user.get("user_id")
    db_agent = crud_custom_agent.create_custom_agent(db=db, agent=agent, user_id=user_id)
    db_agent = crud_custom_agent.get_custom_agent(db, db_agent.id)
    return _populate_creator_username(db_agent)
@router.get("/", response_model=List[CustomAgent], summary="獲取所有自訂 Agent")
def read_custom_agents(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_active_user)
):
    user_id = current_user.get("user_id")
    agents = crud_custom_agent.get_custom_agents(db, skip=skip, limit=limit, user_id=user_id)
    return [_populate_creator_username(agent) for agent in agents]
@router.get("/{agent_id}", response_model=CustomAgent, summary="根據 ID 獲取單一自訂 Agent")
def read_custom_agent(
    agent_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_active_user)
):
    db_agent = crud_custom_agent.get_custom_agent(db, agent_id=agent_id)
    if db_agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    user_id = current_user.get("user_id")
    if not db_agent.is_public and db_agent.created_by != user_id:
        raise HTTPException(status_code=403, detail="Access denied: This is a private agent")
    
    return _populate_creator_username(db_agent)
@router.put("/{agent_id}", response_model=CustomAgent, summary="更新指定的自訂 Agent")
def update_custom_agent(
    agent_id: int,
    agent: CustomAgentUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_active_user)
):
    db_agent = crud_custom_agent.get_custom_agent(db, agent_id=agent_id)
    if db_agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    user_id = current_user.get("user_id")
    is_admin = current_user.get("is_admin", False)
    
    if agent.is_public is not None and agent.is_public != db_agent.is_public:
        if db_agent.created_by != user_id:
            raise HTTPException(
                status_code=403, 
                detail="Access denied: Only the creator can change the public/private status"
            )
    
    if db_agent.created_by != user_id and not is_admin:
        raise HTTPException(status_code=403, detail="Access denied: You can only update your own agents")
    
    db_agent = crud_custom_agent.update_custom_agent(db, agent_id=agent_id, agent_update=agent)
    return _populate_creator_username(db_agent)
@router.delete("/{agent_id}", response_model=CustomAgent, summary="刪除指定的自訂 Agent")
def delete_custom_agent(
    agent_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_active_user)
):
    db_agent = crud_custom_agent.get_custom_agent(db, agent_id=agent_id)
    if db_agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    user_id = current_user.get("user_id")
    is_admin = current_user.get("is_admin", False)
    if db_agent.created_by != user_id and not is_admin:
        raise HTTPException(status_code=403, detail="Access denied: You can only delete your own agents")
    
    db_agent = crud_custom_agent.delete_custom_agent(db, agent_id=agent_id)
    return db_agent
