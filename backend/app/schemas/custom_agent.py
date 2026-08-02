
from pydantic import BaseModel, Field
from typing import Optional, List
class CustomAgentBase(BaseModel):
    name: str = Field(..., description="Agent 的名稱，例如 '產品經理'")
    role: str = Field(..., description="Agent 的角色，例如 'Product Manager'")
    expertise: str = Field(..., description="Agent 的專業領域描述")
    prompt: str = Field(..., description="用於指導 Agent 行為的核心 Prompt")
    tools: Optional[List[str]] = Field([], description="Agent 可以使用的工具列表，例如 ['File', 'Search']")
    is_public: bool = Field(True, description="是否為公開 Agent，公開則所有用戶可見，否則僅創建者可見")
class CustomAgentCreate(CustomAgentBase):
    pass
class CustomAgentUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    expertise: Optional[str] = None
    prompt: Optional[str] = None
    tools: Optional[List[str]] = None
    is_public: Optional[bool] = None
class CustomAgent(CustomAgentBase):
    id: int
    created_by: Optional[int] = None
    creator_username: Optional[str] = None
    model_config = {
        "from_attributes": True,
    }
