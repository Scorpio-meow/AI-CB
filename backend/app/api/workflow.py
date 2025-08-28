# -*- coding: utf-8 -*-
"""
workflow.py (Refactored v5: Plain Text Responses)

This version removes the requirement for LLMs to respond in JSON format.
1.  System prompts have been updated to ask for raw text responses.
2.  The LLM response handling logic now treats the entire response as the
    content, removing all JSON parsing.
"""

import asyncio
import json
import os
from typing import List, Dict, Any, Optional

import httpx
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.chat import manager
from app.models.database import get_db
from app.services.chat_service import ChatService

# --- Constants and System Prompts ---
OLLAMA_HOST = os.getenv("LLM_API_BASE", "https://b6838af9164c.ngrok-free.app")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-oss:20b")

# ✅ 更新：移除所有 JSON 格式要求
PROFESSION_PROMPTS = {
    # PM: 專案管理顧問，強調結構、風險和具體方案
    "PM": "你是一位高效的AI專案管理顧問。你的任務是根據收到的內容，生成一份結構清晰、可執行的專案計畫或分析報告。在產出時，你必須做到：1. **結構化思考**：使用列表、里程碑和時程呈現資訊。2. **風險意識**：主動識別潛在風險並提出緩解策略。3. **提供建議**：針對模糊不清的部分，提出具體選項與下一步行動。4. **方法彈性**：考量敏捷(Agile)或瀑布(Waterfall)方法的適用性。",
    
    # RD: 軟體架構師，強調可行性、擴展性和技術債
    "RD": "你是一位務實的資深軟體架構師(RD)。你的任務是從技術角度審核收到的內容，並優化其設計。在修改內容時，你必須考量以下四個面向：1. **技術可行性**：評估需求的實現難度與時程。2. **系統架構**：確保設計具備良好的擴展性、穩定性和可維護性。3. **開發成本**：在效率與品質之間尋求最佳平衡。4. **潛在風險**：點出可能的技術債、安全漏洞或效能瓶頸。",
    
    # BD: 業務開發策略師，強調市場、對手和商業模式
    "BD": "你是一位敏銳的業務開發策略師(BD)。你的任務是從商業價值角度審核收到的內容，並強化其市場競爭力。在修改內容時，你必須聚焦於以下四個面向：1. **市場機會**：分析目標客群(TA)與市場切入點。2. **競爭格局**：找出差異化優勢(USP)與競爭壁壘。3. **商業模式**：明確價值主張與可行的營收模式。4. **行動方案**：提出具體的市場推廣(Go-To-Market)或合作夥伴建議。",
    
    # DEFAULT: 資深編輯與溝通專家，強調清晰、邏輯和說服力
    "DEFAULT": "你是一位資深編輯與溝通專家。你的任務是將收到的內容優化得更清晰、更有邏輯且具說服力。在修改內容時，你必須執行以下三項檢查：1. **核心論點**：確保核心訊息明確，並移除冗餘、模糊的描述。2. **結構邏輯**：調整段落順序與用詞，使整體論述流暢且易於理解。3. **目標受眾**：根據內容判斷可能的讀者，並優化語氣與風格以達成最佳溝通效果。最好用表格呈現內容}。"
}

CYCLE_LIMIT = 2

router = APIRouter()
chat_service = ChatService()

# =================================================================
# 1. 數據模型 (Data Models)
# =================================================================

class AgentInfo(BaseModel):
    ID: str
    profession: str
    gate: bool
    input: List[str]
    output: List[str]

class WorkflowProcess(BaseModel):
    agents: List[AgentInfo]
    initialPrompt: str

# =================================================================
# 2. 節點執行器 (Node Executor)
# =================================================================

class WorkflowNode:
    def __init__(self, agent_info: AgentInfo, manager: 'DynamicWorkflowManager'):
        self.id = agent_info.ID
        self.profession = agent_info.profession
        self.is_gate = agent_info.gate
        self.input_ids = [i.rsplit('_',1)[0] for i in agent_info.input]
        self.output_ids = [o.rsplit('_',1)[0] for o in agent_info.output]
        self.manager = manager
        self.system_prompt = PROFESSION_PROMPTS.get(self.profession, PROFESSION_PROMPTS["DEFAULT"])
        self.status = "PENDING"
        self.received_inputs: Dict[str, str] = {}
        self.output_content: Optional[str] = None
        self.log_prefix = f"[節點: {self.id} ({self.profession})]"
        self.activation_counts: Dict[str, int] = {input_id: 0 for input_id in self.input_ids}

        if self.is_gate:
            print(f"{self.log_prefix} 被指定為入口(gate)，將忽略其所有輸入連線。")
            self.input_ids = []
            self.activation_counts = {}

        print(f"{self.log_prefix} 已初始化。輸入源: {self.input_ids}, 輸出目標: {self.output_ids}")

    async def check_and_run(self, sender_id: str):
        print(f"{self.log_prefix} 由 {sender_id} 觸發檢查... (收到 {len(self.received_inputs)} / 需要 {len(self.input_ids)})")
        if self.status == "COMPLETED":
            count = self.activation_counts.get(sender_id, 0)
            print(f"{self.log_prefix} 已完成，但收到來自 {sender_id} 的循環激活。當前計數: {count}/{CYCLE_LIMIT}")
            if count < CYCLE_LIMIT:
                self.activation_counts[sender_id] = count + 1
                self.status = "PENDING"
                print(f"{self.log_prefix} 循環次數未達上限，重置狀態為 PENDING。")
            else:
                print(f"{self.log_prefix} 已達到循環次數上限，忽略來自 {sender_id} 的激活。")
                await self.manager.check_completion()
                return

        if self.status != "PENDING":
            print(f"{self.log_prefix} 狀態為 {self.status}，跳過執行。")
            return

        if all(input_id in self.received_inputs for input_id in self.input_ids):
            print(f"{self.log_prefix} ✅ 所有依賴項均已滿足，準備執行。")
            await self.run()
        else:
            print(f"{self.log_prefix} 依賴項未完全滿足，繼續等待。")

    async def run(self):
        print(f"{self.log_prefix} 開始執行 `run` 函數。")
        self.status = "RUNNING"
        await self.manager.send_update({
            "nodeId": self.id,
            "status": "thinking",
            "message": f"{self.profession} 正在思考..."
        })

        input_parts = []
        for sender_id, content in self.received_inputs.items():
            sender_node = self.manager.nodes.get(sender_id)
            sender_role = sender_node.profession if sender_node else "User (初始指令)"
            input_parts.append(f"--- 來自「{sender_role}」的輸入 ---\n{content}")
        
        combined_input = "\n\n".join(input_parts)
        task_description = f"請基於以下全部內容，從你「{self.profession}」的角度出發，完成你的任務。\n\n{combined_input}"

        try:
            # ✅ 正確的邏輯：直接接收純文本回應
            raw_response = await self.manager.execute_llm_call(self.system_prompt, task_description)
            self.output_content = raw_response if raw_response else "(內容生成失敗)"
            self.status = "COMPLETED"
            print(f"{self.log_prefix} 執行成功。")

            await self.manager.send_update({
                "nodeId": self.id,
                "status": "completed",
                "response": self.output_content
            })

            await self.manager.propagate_result(self.id, self.output_content)

        except Exception as e:
            self.status = "FAILED"
            error_msg = f"{self.profession} 執行失敗: {e}"
            print(f"{self.log_prefix} {error_msg}")
            await self.manager.handle_failure(error_msg)

# =================================================================
# 3. 工作流管理器 (Workflow Manager)
# =================================================================

class DynamicWorkflowManager:
    def __init__(self, workflow_process: WorkflowProcess, websocket: WebSocket, user_id: int, db: Session):
        self.process = workflow_process
        self.websocket = websocket
        self.user_id = user_id
        self.db = db
        self.master_history: List[Dict[str, str]] = []
        self.is_failed = False
        self.log_prefix = "[管理器]"
        
        print(f"{self.log_prefix} 正在從 payload 初始化節點...")
        self.nodes: Dict[str, WorkflowNode] = {
            agent.ID: WorkflowNode(agent, self) for agent in self.process.agents
        }
        print(f"{self.log_prefix} 所有節點初始化完畢。 ")

    async def start(self):
        print(f"{self.log_prefix} 開始執行 `start` 函數。 ")
        try:
            await self.send_update({"status": "started", "message": "工作流啟動..."})
            self.master_history.append({"role": "User", "content": self.process.initialPrompt})

            gate_nodes = [node for node in self.nodes.values() if node.is_gate]
            
            if len(gate_nodes) != 1:
                raise ValueError(f"錯誤：工作流必須有且僅有一個入口節點(gate)，但找到了 {len(gate_nodes)} 個。 ")
            
            gate_node = gate_nodes[0]
            print(f"{self.log_prefix} 找到唯一起始節點: {gate_node.id}。 ")

            gate_node.received_inputs["user_prompt"] = self.process.initialPrompt
            await gate_node.check_and_run(sender_id="_start_workflow")

        except Exception as e:
            await self.handle_failure(f"工作流初始化失敗: {e}")

    async def propagate_result(self, completed_node_id: str, result: str):
        print(f"\n{self.log_prefix} ===== 開始傳播結果 (來源: {completed_node_id}) =====")
        if self.is_failed: return

        self.master_history.append({
            "role": self.nodes[completed_node_id].profession,
            "content": result
        })

        output_target_ids = self.nodes[completed_node_id].output_ids
        if not output_target_ids:
            print(f"{self.log_prefix} 節點 {completed_node_id} 沒有下游，檢查工作流是否結束。 ")
            await self.check_completion()
            return

        downstream_tasks = []
        for target_id in output_target_ids:
            downstream_node = self.nodes.get(target_id)
            if downstream_node:
                print(f"{self.log_prefix} ✅ 找到下游: 將結果從 {completed_node_id} 傳遞到 {downstream_node.id}。 ")
                downstream_node.received_inputs[completed_node_id] = result
                downstream_tasks.append(downstream_node.check_and_run(sender_id=completed_node_id))
        
        if downstream_tasks:
            print(f"{self.log_prefix} 觸發了 {len(downstream_tasks)} 個下游節點的檢查。 ")
            await asyncio.gather(*downstream_tasks)
        else:
            print(f"{self.log_prefix} 警告：節點 {completed_node_id} 有輸出目標但未找到對應節點實例。 ")
            await self.check_completion()
        
        print(f"{self.log_prefix} ===== 結果傳播完畢 =====\n")

    async def check_completion(self):
        print(f"{self.log_prefix} 開始執行 `check_completion` 函數。 ")
        all_settled = all(node.status in ["COMPLETED", "FAILED"] for node in self.nodes.values())
        
        if all_settled and not self.is_failed:
            print(f"{self.log_prefix} 所有節點均已穩定，準備進行最終總結。 ")
            final_node = self._find_final_node()
            content_to_summarize = final_node.output_content if final_node else "(未能確定用於總結的內容)"

            await self.send_update({"status": "info", "message": "所有流程已完成，正在進行最終總結..."})
            
            summary_task = f"請將以下全部內容，做一個全面、完整、有條理的最終總結報告。\n\n---\n{content_to_summarize}\n---"
            default_system_prompt = PROFESSION_PROMPTS["DEFAULT"]
            
            try:
                final_summary = await self.execute_llm_call(default_system_prompt, summary_task)
                print(f"{self.log_prefix} DEFAULT Agent 總結完成。 ")
                self.master_history.append({"role": "最終總結 (DEFAULT)", "content": final_summary})
            except Exception as e:
                print(f"{self.log_prefix} DEFAULT Agent 總結失敗: {e}")
                final_summary = f"最終總結步驟失敗: {e}"

            conv_id = await self._save_workflow_history()

            await self.send_update({
                "status": "finished",
                "response": "工作流執行完畢",
                "final_artical": final_summary,
                "conversation_id": conv_id
            })
        else:
            print(f"{self.log_prefix} 尚有 PENDING 或 RUNNING 的節點，工作流繼續。 ")

    def _find_final_node(self) -> Optional[WorkflowNode]:
        for node in self.nodes.values():
            if not node.output_ids:
                return node
        return list(self.nodes.values())[-1]

    async def handle_failure(self, error_message: str):
        if not self.is_failed:
            self.is_failed = True
            print(f"{self.log_prefix} 工作流失敗: {error_message}")
            await self.send_update({"status": "error", "response": error_message})

    async def send_update(self, data: dict):
        await self.websocket.send_json(data)

    async def execute_llm_call(self, system_prompt: str, task_description: str) -> str:
        """獨立的 LLM 調用函數，返回純文本。"""
        print(f"{self.log_prefix} 開始執行 `execute_llm_call`。 ")
        full_prompt = f"System Prompt: {system_prompt}\n\n--- 對話歷史與當前任務 ---\n{task_description}"
        try:
            async with httpx.AsyncClient() as client:
                url = f"{OLLAMA_HOST}/api/generate"
                payload = {"model": MODEL_NAME, "prompt": full_prompt, "stream": False}
                response = await client.post(url, json=payload, timeout=180.0)
                response.raise_for_status()
                data = response.json()
                response_text = data.get("response", "").strip()
            print(f"{self.log_prefix} LLM API 調用成功。 ")
            return response_text
        except httpx.RequestError as e:
            raise Exception(f"請求 LLM API 失敗: {e}")
        except Exception as e:
            raise Exception(f"處理 LLM 回應時出錯: {e}")

    async def _save_workflow_history(self) -> int:
        print(f"{self.log_prefix} 開始執行 `_save_workflow_history`。 ")
        title = f"工作流: {self.process.initialPrompt[:30]}..."
        conversation = await chat_service.create_conversation(self.db, self.user_id, title)
        for msg in self.master_history:
            is_user = msg["role"] == "User"
            formatted_content = f"**【{msg['role']}】**\n\n{msg['content']}"
            await chat_service.save_message(self.db, self.user_id, formatted_content, is_user, conversation.id)
        print(f"{self.log_prefix} 工作流歷史已存入對話 ID: {conversation.id} ")
        return conversation.id

# =================================================================
# WebSocket 端點 (Endpoint)
# =================================================================

def get_db_session():
    db = next(get_db())
    try:
        yield db
    finally:
        db.close()

@router.websocket("/ws")
async def workflow_websocket_endpoint(websocket: WebSocket, db: Session = Depends(get_db_session)):
    user_id = 1
    await manager.connect(websocket, user_id)
    print(f"使用者 {user_id} 的 Workflow WebSocket 連線成功 (驗證已繞過)。 ")
    
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            msg_type = message.get("type")

            if msg_type == "start_workflow":
                payload_data = message.get("payload")
                if not payload_data:
                    await websocket.send_json({"status": "error", "response": "Payload 不得為空"})
                    continue
                
                workflow_process = WorkflowProcess(**payload_data)
                
                manager_instance = DynamicWorkflowManager(workflow_process, websocket, user_id, db)
                asyncio.create_task(manager_instance.start())

    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)
        print(f"使用者 {user_id} 的 WebSocket 連線已斷開。 ")
    except Exception as e:
        print(f"WebSocket 發生錯誤: {e}")
        if websocket.client_state.value != 3:
            try:
                await websocket.send_json({"status": "error", "response": f"伺服器內部錯誤: {e}"})
            except Exception as send_e:
                print(f"傳送錯誤訊息時失敗: {send_e}")
        manager.disconnect(websocket, user_id)
