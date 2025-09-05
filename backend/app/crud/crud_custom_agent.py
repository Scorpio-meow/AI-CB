from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.models.custom_agent import CustomAgent
from app.schemas.custom_agent import CustomAgentCreate, CustomAgentUpdate
from typing import List, Optional

# 創建自訂 Agent
def create_custom_agent(db: Session, agent: CustomAgentCreate) -> CustomAgent:
    """
    在資料庫中新增一個自訂 Agent。

    :param db: 資料庫 session。
    :param agent: 要新增的 Agent 的資料，遵從 CustomAgentCreate schema。
    :return: 已新增的 Agent 物件。
    """
    db_agent = CustomAgent(**agent.model_dump()) # Pydantic V2 使用 model_dump()
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
    return db.query(CustomAgent).filter(CustomAgent.id == agent_id).first()

# 根據名稱或角色讀取單一自訂 Agent
def get_custom_agent_by_name_or_role(db: Session, name_or_role: str) -> Optional[CustomAgent]:
    """
    根據名稱 (name) 或角色 (role) 從資料庫中讀取單一自訂 Agent。
    會同時查詢 name 和 role 欄位。

    :param db: 資料庫 session。
    :param name_or_role: 要查詢的名稱或角色。
    :return: 找到的 Agent 物件，如果不存在則返回 None。
    """
    return db.query(CustomAgent).filter(
        or_(CustomAgent.name == name_or_role, CustomAgent.role == name_or_role)
    ).first()

# 讀取所有自訂 Agent
def get_custom_agents(db: Session, skip: int = 0, limit: int = 100) -> List[CustomAgent]:
    """
    從資料庫中讀取自訂 Agent 列表，支援分頁。

    :param db: 資料庫 session。
    :param skip: 跳過的紀錄數量。
    :param limit: 返回的紀錄最大數量。
    :return: Agent 物件的列表。
    """
    return db.query(CustomAgent).offset(skip).limit(limit).all()

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