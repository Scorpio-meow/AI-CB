import json
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Union

from app.models.database import get_db
from app.schemas.custom_agent import CustomAgent, CustomAgentCreate, CustomAgentUpdate
from app.crud import crud_custom_agent

# 建立一個新的 FastAPI 路由器
router = APIRouter()

# --- 動態載入 Agents --- #

def load_default_agents() -> List[Dict[str, Any]]:
    """從 JSON 文件中載入預設 agents。"""
    agents_path = Path(__file__).parent.parent / "data" / "agents.json"
    if not agents_path.exists():
        return []
    with open(agents_path, 'r', encoding='utf-8') as f:
        return json.load(f)

# --- API Endpoints --- #

@router.get("/all_with_details", response_model=List[CustomAgent], summary="獲取所有(包含預設)的 Agent 詳情")
def read_all_agents_with_details(db: Session = Depends(get_db)):
    """
    獲取一個包含預設 Agent 和自訂 Agent 的完整列表。
    - **db**: 資料庫 session 依賴。
    """
    all_agents: Dict[str, CustomAgent] = {}
    default_agents = load_default_agents()

    # 1. 處理預設 Agents
    for i, agent_def in enumerate(default_agents):
        if agent_def["role"] == 'DEFAULT':
            continue

        agent_data = {
            "id": -(i + 1),  # 使用負數 ID 以避免與資料庫中的 ID 衝突
            "name": agent_def["name"],
            "role": agent_def["role"],
            "prompt": agent_def["prompt"],
            "expertise": "預設",
            "tools": []
        }
        if agent_def["role"] not in all_agents:
            # 直接使用 agent_data 創建 CustomAgent 模型實例
            all_agents[agent_def["role"]] = CustomAgent(**agent_data)

    # 2. 讀取並合併自訂 Agents
    custom_agents = crud_custom_agent.get_custom_agents(db, limit=1000)
    for agent in custom_agents:
        all_agents[agent.role] = agent

    return list(all_agents.values())


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