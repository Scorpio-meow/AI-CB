from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.models.database import get_db
from app.schemas.custom_agent import CustomAgent, CustomAgentCreate, CustomAgentUpdate
from app.crud import crud_custom_agent

# 建立一個新的 FastAPI 路由器
router = APIRouter()

# --- API Endpoints --- #

@router.get("/all_with_details", response_model=List[CustomAgent], summary="獲取所有自訂 Agent 詳情")
def read_all_agents_with_details(db: Session = Depends(get_db)):
    """
    獲取所有自訂 Agent 的完整列表。
    注意：預設 Agent 已被移除，此端點只返回使用者自訂的 Agent。
    - **db**: 資料庫 session 依賴。
    """
    # 只返回自訂 Agents，不再載入預設 Agent
    custom_agents = crud_custom_agent.get_custom_agents(db, limit=1000)
    return custom_agents


@router.post("/", response_model=CustomAgent, summary="創建新的自訂 Agent")
def create_custom_agent(agent: CustomAgentCreate, db: Session = Depends(get_db)):
    """
    創建一個新的自訂 Agent。
    - **agent**: 包含新 Agent 資訊的請求主體。
    - **db**: 資料庫 session 依賴。
    """
    return crud_custom_agent.create_custom_agent(db=db, agent=agent)

@router.get("/", response_model=List[CustomAgent], summary="獲取所有自訂 Agent")
def read_custom_agents(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    獲取所有自訂 Agent 的列表，支援分頁。
    - **skip**: 跳過的項目數量。
    - **limit**: 每頁的項目數量。
    - **db**: 資料庫 session 依賴。
    """
    agents = crud_custom_agent.get_custom_agents(db, skip=skip, limit=limit)
    return agents

@router.get("/{agent_id}", response_model=CustomAgent, summary="根據 ID 獲取單一自訂 Agent")
def read_custom_agent(agent_id: int, db: Session = Depends(get_db)):
    """
    根據提供的 ID 獲取單一自訂 Agent 的詳細資訊。
    - **agent_id**: 要獲取的 Agent 的 ID。
    - **db**: 資料庫 session 依賴。
    """
    db_agent = crud_custom_agent.get_custom_agent(db, agent_id=agent_id)
    if db_agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    return db_agent

@router.put("/{agent_id}", response_model=CustomAgent, summary="更新指定的自訂 Agent")
def update_custom_agent(agent_id: int, agent: CustomAgentUpdate, db: Session = Depends(get_db)):
    """
    更新指定 ID 的自訂 Agent。
    - **agent_id**: 要更新的 Agent 的 ID。
    - **agent**: 包含要更新欄位的請求主體。
    - **db**: 資料庫 session 依賴。
    """
    db_agent = crud_custom_agent.update_custom_agent(db, agent_id=agent_id, agent_update=agent)
    if db_agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    return db_agent

@router.delete("/{agent_id}", response_model=CustomAgent, summary="刪除指定的自訂 Agent")
def delete_custom_agent(agent_id: int, db: Session = Depends(get_db)):
    """
    刪除指定 ID 的自訂 Agent。
    - **agent_id**: 要刪除的 Agent 的 ID。
    - **db**: 資料庫 session 依賴。
    """
    db_agent = crud_custom_agent.delete_custom_agent(db, agent_id=agent_id)
    if db_agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    return db_agent