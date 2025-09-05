
from pydantic import BaseModel, Field
from typing import Optional, List

# 基礎模型，定義了自訂 Agent 的所有基本欄位
class CustomAgentBase(BaseModel):
    """
    自訂 Agent 的基礎 Pydantic 模型。
    """
    name: str = Field(..., description="Agent 的名稱，例如 '產品經理'")
    role: str = Field(..., description="Agent 的角色，例如 'Product Manager'")
    expertise: str = Field(..., description="Agent 的專業領域描述")
    prompt: str = Field(..., description="用於指導 Agent 行為的核心 Prompt")
    tools: Optional[List[str]] = Field([], description="Agent 可以使用的工具列表，例如 ['File', 'Search']")

# 用於創建新 Agent 的模型，繼承自基礎模型
class CustomAgentCreate(CustomAgentBase):
    """
    用於創建新的自訂 Agent 的模型。
    """
    pass

# 用於更新現有 Agent 的模型，所有欄位都是可選的
class CustomAgentUpdate(BaseModel):
    """
    用於更新自訂 Agent 的模型，所有欄位皆為可選。
    """
    name: Optional[str] = None
    role: Optional[str] = None
    expertise: Optional[str] = None
    prompt: Optional[str] = None
    tools: Optional[List[str]] = None

# 用於從資料庫讀取並返回給客戶端的模型，包含 id
class CustomAgent(CustomAgentBase):
    """
    用於 API 回應的自訂 Agent 模型，包含資料庫 ID。
    """
    id: int
    # 使用 Pydantic V2 建議的 model_config 風格，保留 from_attributes 行為
    model_config = {
        "from_attributes": True,  # 允許模型從 ORM 物件 (如 SQLAlchemy 模型) 進行轉換
    }

