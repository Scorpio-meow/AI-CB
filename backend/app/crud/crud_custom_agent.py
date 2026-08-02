from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, and_
from app.models.custom_agent import CustomAgent
from app.schemas.custom_agent import CustomAgentCreate, CustomAgentUpdate
from typing import List, Optional
def create_custom_agent(db: Session, agent: CustomAgentCreate, user_id: int) -> CustomAgent:
    agent_data = agent.model_dump()
    agent_data['created_by'] = user_id
    db_agent = CustomAgent(**agent_data)
    db.add(db_agent)
    db.commit()
    db.refresh(db_agent)
    return db_agent
def get_custom_agent(db: Session, agent_id: int) -> Optional[CustomAgent]:
    return db.query(CustomAgent).options(joinedload(CustomAgent.creator)).filter(CustomAgent.id == agent_id).first()
def get_custom_agent_by_name_or_role(db: Session, name_or_role: str, user_id: Optional[int] = None) -> Optional[CustomAgent]:
    query = db.query(CustomAgent).filter(
        or_(CustomAgent.name == name_or_role, CustomAgent.role == name_or_role)
    )
    
    if user_id is not None:
        query = query.filter(
            or_(
                CustomAgent.is_public == True,
                and_(CustomAgent.created_by == user_id, CustomAgent.is_public == False)
            )
        )
    else:
        query = query.filter(CustomAgent.is_public == True)
    
    return query.first()
def get_custom_agents(db: Session, skip: int = 0, limit: int = 100, user_id: Optional[int] = None) -> List[CustomAgent]:
    query = db.query(CustomAgent).options(joinedload(CustomAgent.creator))
    
    if user_id is not None:
        query = query.filter(
            or_(
                CustomAgent.is_public == True,
                and_(CustomAgent.created_by == user_id, CustomAgent.is_public == False)
            )
        )
    else:
        query = query.filter(CustomAgent.is_public == True)
    
    return query.offset(skip).limit(limit).all()
def update_custom_agent(db: Session, agent_id: int, agent_update: CustomAgentUpdate) -> Optional[CustomAgent]:
    db_agent = get_custom_agent(db, agent_id)
    if db_agent:
        update_data = agent_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_agent, key, value)
        db.commit()
        db.refresh(db_agent)
    return db_agent
def delete_custom_agent(db: Session, agent_id: int) -> Optional[CustomAgent]:
    db_agent = get_custom_agent(db, agent_id)
    if db_agent:
        db.delete(db_agent)
        db.commit()
    return db_agent
