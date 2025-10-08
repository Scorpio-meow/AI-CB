from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, and_
from app.models.custom_agent import CustomAgent
from app.schemas.custom_agent import CustomAgentCreate, CustomAgentUpdate
from typing import List, Optional

# 創建自訂 Agent
def create_custom_agent(db: Session, agent: CustomAgentCreate, user_id: int) -> CustomAgent:
    """
    在資料庫中新增一個自訂 Agent。

    :param db: 資料庫 session。
    :param agent: 要新增的 Agent 的資料，遵從 CustomAgentCreate schema。
    :param user_id: 創建者的用戶 ID。
    :return: 已新增的 Agent 物件。
    """
    agent_data = agent.model_dump()
    agent_data['created_by'] = user_id  # 設置創建者
    db_agent = CustomAgent(**agent_data)
    db.add(db_agent)
    db.commit()
    db.refresh(db_agent)
    return db_agent

# 讀取單一自訂 Agent
def get_custom_agent(db: Session, agent_id: int) -> Optional[CustomAgent]:
    """
    根據 ID 從資料庫中讀取單一自訂 Agent。

    :param db: 資料庫 session。
    :param agent_id: 要讀取的 Agent 的 ID。
    :return: 找到的 Agent 物件，如果不存在則返回 None。
    """
    return db.query(CustomAgent).options(joinedload(CustomAgent.creator)).filter(CustomAgent.id == agent_id).first()

# 根據名稱或角色讀取單一自訂 Agent
def get_custom_agent_by_name_or_role(db: Session, name_or_role: str, user_id: Optional[int] = None) -> Optional[CustomAgent]:
    """
    根據名稱 (name) 或角色 (role) 從資料庫中讀取單一自訂 Agent。
    會同時查詢 name 和 role 欄位。
    
    如果提供 user_id，將只返回用戶可見的 Agent（公開 + 自己的私人）。

    :param db: 資料庫 session。
    :param name_or_role: 要查詢的名稱或角色。
    :param user_id: 可選的用戶 ID，用於過濾可見性。
    :return: 找到的 Agent 物件，如果不存在則返回 None。
    """
    query = db.query(CustomAgent).filter(
        or_(CustomAgent.name == name_or_role, CustomAgent.role == name_or_role)
    )
    
    # 如果提供了 user_id，添加可見性過濾
    if user_id is not None:
        query = query.filter(
            or_(
                CustomAgent.is_public == True,
                and_(CustomAgent.created_by == user_id, CustomAgent.is_public == False)
            )
        )
    else:
        # 只返回公開的 Agent
        query = query.filter(CustomAgent.is_public == True)
    
    return query.first()

# 讀取所有自訂 Agent（支援用戶過濾）
def get_custom_agents(db: Session, skip: int = 0, limit: int = 100, user_id: Optional[int] = None) -> List[CustomAgent]:
    """
    從資料庫中讀取自訂 Agent 列表，支援分頁和用戶過濾。
    
    如果提供 user_id，將返回：
    - 所有公開的 Agent (is_public=True)
    - 該用戶創建的私人 Agent (created_by=user_id and is_public=False)
    
    如果不提供 user_id，只返回公開的 Agent。

    :param db: 資料庫 session。
    :param skip: 跳過的紀錄數量。
    :param limit: 返回的紀錄最大數量。
    :param user_id: 可選的用戶 ID，用於過濾私人 Agent。
    :return: Agent 物件的列表。
    """
    query = db.query(CustomAgent).options(joinedload(CustomAgent.creator))
    
    if user_id is not None:
        # 返回公開 Agent 或用戶自己的私人 Agent
        query = query.filter(
            or_(
                CustomAgent.is_public == True,
                and_(CustomAgent.created_by == user_id, CustomAgent.is_public == False)
            )
        )
    else:
        # 只返回公開 Agent
        query = query.filter(CustomAgent.is_public == True)
    
    return query.offset(skip).limit(limit).all()

# 更新自訂 Agent
def update_custom_agent(db: Session, agent_id: int, agent_update: CustomAgentUpdate) -> Optional[CustomAgent]:
    """
    更新資料庫中現有的自訂 Agent。

    :param db: 資料庫 session。
    :param agent_id: 要更新的 Agent 的 ID。
    :param agent_update: 包含要更新欄位的資料，遵從 CustomAgentUpdate schema。
    :return: 更新後的 Agent 物件，如果不存在則返回 None。
    """
    db_agent = get_custom_agent(db, agent_id)
    if db_agent:
        update_data = agent_update.model_dump(exclude_unset=True) # 只獲取有被設定的欄位
        for key, value in update_data.items():
            setattr(db_agent, key, value)
        db.commit()
        db.refresh(db_agent)
    return db_agent

# 刪除自訂 Agent
def delete_custom_agent(db: Session, agent_id: int) -> Optional[CustomAgent]:
    """
    根據 ID 從資料庫中刪除一個自訂 Agent。

    :param db: 資料庫 session。
    :param agent_id: 要刪除的 Agent 的 ID。
    :return: 被刪除的 Agent 物件，如果不存在則返回 None。
    """
    db_agent = get_custom_agent(db, agent_id)
    if db_agent:
        db.delete(db_agent)
        db.commit()
    return db_agent
