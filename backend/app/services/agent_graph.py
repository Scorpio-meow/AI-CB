import logging
from typing import List, Dict, Any, Optional, TypedDict
from langgraph.graph import StateGraph, END
import anyio
from app.core.llm_provider import get_llm_provider

logger = logging.getLogger(__name__)

# 定義 LangGraph 的狀態結構
class AgentState(TypedDict):
    messages: List[Dict[str, Any]]
    task: str
    node_id_map: Dict[str, str]
    current_node: str
    final_result: Optional[str]
    reviewer_approved: bool
    review_comments: Optional[str]

# --- 節點定義 ---

async def planner_node(state: AgentState) -> Dict[str, Any]:
    logger.info("[LangGraph] 執行 Planner 節點")
    # 這裡可以透過 llm_provider 進行調用
    provider = get_llm_provider()
    
    system_prompt = "你是一位專案規劃專家。請為使用者的任務做詳細的分解與規劃。"
    user_prompt = f"任務目標: {state['task']}\n\n請給出實作步驟規劃。"
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    
    # 呼叫並傳入 tools (支援 RAG 搜尋)
    from app.tools.registry import TOOL_SCHEMAS
    result = await provider.chat_with_tools(messages, TOOL_SCHEMAS)
    
    return {
        "messages": [{"role": "assistant", "content": result}],
        "final_result": result,
        "current_node": "planner_node"
    }

async def writer_node(state: AgentState) -> Dict[str, Any]:
    logger.info("[LangGraph] 執行 Writer 節點")
    provider = get_llm_provider()
    
    planner_output = state.get("final_result", "")
    review_comments = state.get("review_comments", "")
    
    system_prompt = "你是一位專業的文字與方案撰寫專家。請根據規劃案與審查意見完成文字內容。"
    user_prompt = f"規劃案:\n{planner_output}\n\n審查意見:\n{review_comments}\n\n請生成正式內容。"
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    
    result = await provider.chat_with_tools(messages)
    return {
        "messages": [{"role": "assistant", "content": result}],
        "final_result": result,
        "current_node": "writer_node"
    }

async def reviewer_node(state: AgentState) -> Dict[str, Any]:
    logger.info("[LangGraph] 執行 Reviewer 節點")
    provider = get_llm_provider()
    
    writer_output = state.get("final_result", "")
    
    system_prompt = "你是一位嚴格的內容評估與審查專家。請評估內容是否合格，並給予是(PASS)或否(FAIL)的判定。"
    user_prompt = f"請審查以下內容，如果完全合格請包含字串 'PASS'，否則請說明原因並給予 'FAIL'：\n\n{writer_output}"
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    
    result = await provider.chat_with_tools(messages)
    approved = "PASS" in result.upper()
    
    return {
        "messages": [{"role": "assistant", "content": result}],
        "reviewer_approved": approved,
        "review_comments": result if not approved else None,
        "current_node": "reviewer_node"
    }

# --- 條件邊判定 ---
def should_continue(state: AgentState) -> str:
    if state.get("reviewer_approved", False):
        return "end"
    else:
        logger.info("[LangGraph] 審查未通過，返回 Writer 進行修正")
        return "rewrite"

# --- 構建 StateGraph ---
def build_agent_graph() -> StateGraph:
    workflow = StateGraph(AgentState)
    
    # 新增節點
    workflow.add_node("planner_node", planner_node)
    workflow.add_node("writer_node", writer_node)
    workflow.add_node("reviewer_node", reviewer_node)
    
    # 設定起點
    workflow.set_entry_point("planner_node")
    
    # 建立邊
    workflow.add_edge("planner_node", "writer_node")
    workflow.add_edge("writer_node", "reviewer_node")
    
    # 建立條件邊 (分流)
    workflow.add_conditional_edges(
        "reviewer_node",
        should_continue,
        {
            "end": END,
            "rewrite": "writer_node"
        }
    )
    
    return workflow.compile()

# --- React Flow WebSocket 事件橋接器 ---
class LangGraphEventBridge:
    def __init__(self, manager, node_id_map: Dict[str, str]):
        """
        :param manager: DynamicWorkflowManager 實例
        :param node_id_map: 映射關係 (e.g., {"planner_node": "agent-1", "writer_node": "agent-2"})
        """
        self.manager = manager
        self.node_id_map = node_id_map

    async def run_and_stream(self, graph, initial_state: Dict[str, Any]):
        """
        執行 LangGraph 並將節點執行狀態透過 WebSocket 橋接串流到前端。
        """
        # 使用 astream_events 攔截事件
        async for event in graph.astream_events(initial_state, version="v2"):
            kind = event.get("event")
            name = event.get("name")
            
            # 只處理在映射表中的節點
            if name in self.node_id_map:
                node_id = self.node_id_map[name]
                
                if kind == "on_chain_start":
                    await self.manager.send_update({
                        "nodeId": node_id,
                        "status": "thinking",
                        "message": f"{name} 正在執行中..."
                    })
                elif kind == "on_chain_end":
                    # 取得執行結果
                    output = event.get("data", {}).get("output", {})
                    # 依據節點回傳的 state 更新前端畫面
                    response_text = output.get("final_result", "") or output.get("review_comments", "") or "已完成"
                    await self.manager.send_update({
                        "nodeId": node_id,
                        "status": "completed",
                        "response": response_text
                    })
