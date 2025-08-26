from pydantic import BaseModel, Extra
from typing import List, Dict, Any, Optional

# --- 子模型定義 ---
# 我們先定義組成 WorkflowPayload 的各個小部分

class NodeData(BaseModel):
    """
    定義了 React Flow 節點中 'data' 物件的結構。
    這包含了節點的核心資訊。
    """
    originalLabel: str  # 節點的原始標籤，例如 "PM" 或 "工程師"
    label: str          # 顯示在前端的標籤，可能會包含額外資訊，例如 "PM (入口)"
    response: Optional[str] = None  # 用於存放 AI 回應的欄位，初始時為 None
    isEntryPoint: bool    # 一個布林值，標記此節點是否為工作流的入口點

    class Config:
        extra = Extra.ignore

class Node(BaseModel):
    """
    定義了單個節點（AI 代理人方塊）的完整結構。
    """
    id: str               # 節點的唯一識別碼
    type: str             # 節點的類型，例如我們自訂的 'agent'
    position: Dict[str, float]  # 節點在前端畫布上的 x, y 座標
    data: NodeData        # 包含節點詳細資訊的巢狀物件

    class Config:
        extra = Extra.ignore

class Edge(BaseModel):
    """
    定義了單條邊線（箭頭）的結構，代表節點之間的關係。
    """
    id: str     # 邊線的唯一識別碼
    source: str # 箭頭起始節點的 id
    target: str # 箭頭指向節點的 id

    class Config:
        extra = Extra.ignore

# --- 主模型定義 ---

class WorkflowPayload(BaseModel):
    """
    這是從前端發送到後端 `/workflow/ws/execute` 的主要資料結構。
    它像一份完整的「作戰計畫書」，描述了整個 AI 工作流的所有細節。
    """
    
    # 包含了畫布上所有的 AI 代理人方塊
    nodes: List[Node]
    
    # 包含了所有連接方塊的箭頭，定義了工作流程
    edges: List[Edge]
    
    # 被指定為「入口」的那個節點的 ID，是整個流程的起點
    entryPointId: str
    
    # 使用者在主輸入框中輸入的、啟動整個工作流的初始指令
    initialPrompt: str
    
    class Config:
        extra = Extra.ignore