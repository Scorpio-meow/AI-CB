from pydantic import BaseModel, Extra
from typing import List, Dict, Any, Optional
class NodeData(BaseModel):
    """
    定義了 React Flow 節點中 'data' 物件的結構。
    這包含了節點的核心資訊。
    """
    originalLabel: str
    label: str
    response: Optional[str] = None
    isEntryPoint: bool
    class Config:
        extra = Extra.ignore
class Node(BaseModel):
    """
    定義了單個節點（AI 代理人方塊）的完整結構。
    """
    id: str
    type: str
    position: Dict[str, float]
    data: NodeData
    class Config:
        extra = Extra.ignore
class Edge(BaseModel):
    """
    定義了單條邊線（箭頭）的結構，代表節點之間的關係。
    """
    id: str
    source: str
    target: str
    class Config:
        extra = Extra.ignore
class WorkflowPayload(BaseModel):
    """
    這是從前端發送到後端 `/workflow/ws/execute` 的主要資料結構。
    它像一份完整的「作戰計畫書」，描述了整個 AI 工作流的所有細節。
    """
    
    nodes: List[Node]
    
    edges: List[Edge]
    
    entryPointId: str
    
    initialPrompt: str
    
    class Config:
        extra = Extra.ignore