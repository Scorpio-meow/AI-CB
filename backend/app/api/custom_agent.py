from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.models.database import get_db
from app.schemas.custom_agent import CustomAgent, CustomAgentCreate, CustomAgentUpdate
from app.crud import crud_custom_agent
from app.core.jwt_auth import get_current_active_user  # JWT 認證

# 建立一個新的 FastAPI 路由器
router = APIRouter()

# --- 輔助函數 --- #

def _populate_creator_username(agent) -> dict:
    """
    將 SQLAlchemy CustomAgent 對象轉換為字典，並填充 creator_username
    """
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

# --- API Endpoints --- #

@router.get("/all_with_details", response_model=List[CustomAgent], summary="獲取所有自訂 Agent 詳情")
def read_all_agents_with_details(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_active_user)
):
    """
    獲取所有自訂 Agent 的完整列表。
    返回所有公開的 Agent 和當前用戶的私人 Agent。
    - **db**: 資料庫 session 依賴。
    - **current_user**: 當前登入的用戶（JWT 認證）。
    """
    user_id = current_user.get("user_id")
    custom_agents = crud_custom_agent.get_custom_agents(db, limit=1000, user_id=user_id)
    # 填充 creator_username
    return [_populate_creator_username(agent) for agent in custom_agents]


@router.post("/", response_model=CustomAgent, summary="創建新的自訂 Agent")
def create_custom_agent(
    agent: CustomAgentCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_active_user)
):
    """
    創建一個新的自訂 Agent。
    - **agent**: 包含新 Agent 資訊的請求主體。
    - **db**: 資料庫 session 依賴。
    - **current_user**: 當前登入的用戶（JWT 認證）。
    """
    user_id = current_user.get("user_id")
    db_agent = crud_custom_agent.create_custom_agent(db=db, agent=agent, user_id=user_id)
    # 重新加載以獲取創建者信息
    db_agent = crud_custom_agent.get_custom_agent(db, db_agent.id)
    return _populate_creator_username(db_agent)

@router.get("/", response_model=List[CustomAgent], summary="獲取所有自訂 Agent")
def read_custom_agents(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_active_user)
):
    """
    獲取所有自訂 Agent 的列表，支援分頁。
    返回所有公開的 Agent 和當前用戶的私人 Agent。
    - **skip**: 跳過的項目數量。
    - **limit**: 每頁的項目數量。
    - **db**: 資料庫 session 依賴。
    - **current_user**: 當前登入的用戶（JWT 認證）。
    """
    user_id = current_user.get("user_id")
    agents = crud_custom_agent.get_custom_agents(db, skip=skip, limit=limit, user_id=user_id)
    return [_populate_creator_username(agent) for agent in agents]

@router.get("/{agent_id}", response_model=CustomAgent, summary="根據 ID 獲取單一自訂 Agent")
def read_custom_agent(
    agent_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_active_user)
):
    """
    根據提供的 ID 獲取單一自訂 Agent 的詳細資訊。
    - **agent_id**: 要獲取的 Agent 的 ID。
    - **db**: 資料庫 session 依賴。
    - **current_user**: 當前登入的用戶（JWT 認證）。
    """
    db_agent = crud_custom_agent.get_custom_agent(db, agent_id=agent_id)
    if db_agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # 檢查權限：如果是私人 Agent，只有創建者可以查看
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
    """
    更新指定 ID 的自訂 Agent。
    只有 Agent 的創建者可以更新。
    - **agent_id**: 要更新的 Agent 的 ID。
    - **agent**: 包含要更新欄位的請求主體。
    - **db**: 資料庫 session 依賴。
    - **current_user**: 當前登入的用戶（JWT 認證）。
    """
    db_agent = crud_custom_agent.get_custom_agent(db, agent_id=agent_id)
    if db_agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # 檢查權限：只有創建者可以更新
    user_id = current_user.get("user_id")
    is_admin = current_user.get("is_admin", False)
    
    # 特殊規則：只有創建者可以修改 is_public 狀態
    if agent.is_public is not None and agent.is_public != db_agent.is_public:
        if db_agent.created_by != user_id:
            raise HTTPException(
                status_code=403, 
                detail="Access denied: Only the creator can change the public/private status"
            )
    
    # 一般更新權限：創建者或管理員
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
    """
    刪除指定 ID 的自訂 Agent。
    只有 Agent 的創建者或管理員可以刪除。
    - **agent_id**: 要刪除的 Agent 的 ID。
    - **db**: 資料庫 session 依賴。
    - **current_user**: 當前登入的用戶（JWT 認證）。
    """
    db_agent = crud_custom_agent.get_custom_agent(db, agent_id=agent_id)
    if db_agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # 檢查權限：只有創建者或管理員可以刪除
    user_id = current_user.get("user_id")
    is_admin = current_user.get("is_admin", False)
    if db_agent.created_by != user_id and not is_admin:
        raise HTTPException(status_code=403, detail="Access denied: You can only delete your own agents")
    
    db_agent = crud_custom_agent.delete_custom_agent(db, agent_id=agent_id)
    return db_agent



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