
from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.types import JSON
from app.models.database import Base

class CustomAgent(Base):
    """
    自訂 Agent 的資料庫模型 (SQLAlchemy Model)。
    對應到資料庫中的 'custom_agents' 表格。
    """
    __tablename__ = "custom_agents"

    # --- 表格欄位定義 ---

    # Agent 的唯一識別碼，為主鍵
    id = Column(Integer, primary_key=True, index=True, comment="Agent 的唯一識別碼")

    # Agent 的顯示名稱，例如: "產品經理"
    name = Column(String, index=True, nullable=False, comment="Agent 的顯示名稱")

    # Agent 的角色，例如: "Product Manager"
    role = Column(String, index=True, nullable=False, comment="Agent 的角色")

    # Agent 的專業領域描述
    expertise = Column(Text, nullable=False, comment="Agent 的專業領域描述")

    # 用於指導 Agent 行為的核心 Prompt
    prompt = Column(Text, nullable=False, comment="指導 Agent 行為的核心 Prompt")

    # Agent 可用的工具列表，以 JSON 格式儲存
    tools = Column(JSON, nullable=True, comment="Agent 可用的工具列表")

    # Agent 是否為公開（所有用戶可見）或私人（僅創建者可見）
    is_public = Column(Boolean, default=True, nullable=False, comment="是否為公開 Agent")

    # 創建此 Agent 的用戶 ID
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True, comment="創建者用戶 ID")

    # 關聯到創建者（User 模型）
    creator = relationship("User", foreign_keys=[created_by])
