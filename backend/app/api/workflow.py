# -*- coding: utf-8 -*-
"""
workflow.py (Refactored v3: Dependency Resolution Fix)

This version adds:
1.  Extremely detailed logging inside propagate_result to debug dependencies.
2.  A fix in the node initialization logic to correctly parse dependencies.
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
OLLAMA_HOST = os.getenv("LLM_API_BASE", "https://fc5d1d0fc900.ngrok-free.app")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-oss:20b")

PROFESSION_PROMPTS = {
    "PM": "你是一位經驗豐富的專案經理。你的任務是根據收到的內容，生成或優化一份專案計畫。且輸出必須是中文為主，且不管使用者輸入甚麼都已你這角色角度去做思考，你的所有輸出都必須是一個 JSON 物件。格式為 {\"artical\": \"你的完整專案計畫\"}。",
    "RD": "你是一位務實的資深軟體工程師(RD)。你的任務是審核收到的內容，並從技術可行性、系統穩定性與開發成本的角度，直接修改內容使其更完善。且輸出必須是中文為主，且不管使用者輸入甚麼都已你這角色角度去做思考，你的所有輸出都必須是一個 JSON 物件。格式為 {\"artical\": \"修改後的完整內文\"}。",
    "BD": "你是一位敏銳的業務分析師(BD)。你的任務是審核收到的內容，並從市場趨勢、競爭對手與營收模式的角度，直接修改內容使其更完善。且輸出必須是中文為主，且不管使用者輸入甚麼都已你這角色角度去做思考，你的所有輸出都必須是一個 JSON 物件。格式為 {\"artical\": \"修改後的完整內文\"}。",
    "DEFAULT": "你是一個通用的 AI 助理。你的任務是審核收到的內容，並直接修改使其更完善。你的所有輸出都必須是一個 JSON 物件，格式為 {\"artical\": \"修改後的完整內文\"}。"
}

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
        
        # ✅ 修正：確保從 agent_info 正確解析依賴
        self.is_gate = agent_info.gate
        
        self.input_ids = [i.rsplit('_',1)[0] for i in agent_info.input]
        self.output_ids = [o.rsplit('_',1)[0] for o in agent_info.output]

        # ✅ 核心修正：如果一個節點被指定為 gate，則程序性地忽略其所有上游輸入依賴
        if self.is_gate:
            print(f"[節點: {agent_info.ID}] 被指定為入口(gate)，將忽略其所有輸入連線。")
            self.input_ids = []
        
        self.manager = manager
        self.system_prompt = PROFESSION_PROMPTS.get(self.profession, PROFESSION_PROMPTS["DEFAULT"])
        self.status = "PENDING"  # PENDING, RUNNING, COMPLETED, FAILED
        self.received_inputs: Dict[str, str] = {}
        self.output_content: Optional[str] = None
        self.log_prefix = f"[節點: {self.id} ({self.profession})]"
        print(f"{self.log_prefix} 已初始化。輸入源: {self.input_ids}, 輸出目標: {self.output_ids}")

    async def check_and_run(self):
        # ✅ 修正日誌，使其更清晰
        print(f"{self.log_prefix} 正在檢查依賴項... (收到 {len(self.received_inputs)} / 需要 {len(self.input_ids)})")
        
        if self.status != "PENDING":
            print(f"{self.log_prefix} 狀態為 {self.status}，跳過執行。")
            return

        # 核心檢查邏輯：所有在 input_ids 中定義的依賴，都必須是 received_inputs 的 key
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
            "message": f"{self.profession} 正在基於 {len(self.received_inputs)} 個輸入源進行思考..."
        })

        # ✅ 優化：構建帶有來源標識的 Prompt
        input_parts = []
        for sender_id, content in self.received_inputs.items():
            # 如果是初始指令，來源標示為 "User"
            sender_node = self.manager.nodes.get(sender_id)
            sender_role = sender_node.profession if sender_node else "User (初始指令)"
            input_parts.append(f"--- 來自「{sender_role}」的輸入 ---\n{content}")
        
        combined_input = "\n\n".join(input_parts)
        task_description = f"請基於以下全部內容，從你「{self.profession}」的角度出發，完成你的任務。\n\n{combined_input}"
        print(f"{self.log_prefix} 構建的任務描述: \n{task_description[:200]}...")

        try:
            response_data = await self.manager.execute_llm_call(self.system_prompt, task_description)
            self.output_content = response_data.get("artical", "(內容生成失敗)")
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
        # ✅ 修正：直接在初始化時就創建好節點，確保依賴關係正確
        self.nodes: Dict[str, WorkflowNode] = {
            agent.ID: WorkflowNode(agent, self) for agent in self.process.agents
        }
        print(f"{self.log_prefix} 所有節點初始化完畢。")

    async def start(self):
        print(f"{self.log_prefix} 開始執行 `start` 函數。")
        try:
            await self.send_update({"status": "started", "message": "工作流啟動，正在尋找入口節點..."})
            self.master_history.append({"role": "User", "content": self.process.initialPrompt})

            # ✅ 最終版邏輯：只尋找被使用者明確指定的 gate 節點
            gate_nodes = [node for node in self.nodes.values() if node.is_gate]
            
            # 嚴格檢查入口節點的數量
            if len(gate_nodes) == 0:
                raise ValueError("錯誤：工作流中未指定任何入口節點 (gate)。請左鍵點擊一個節點將其設為入口。")
            if len(gate_nodes) > 1:
                raise ValueError(f"錯誤：工作流中指定了 {len(gate_nodes)} 個入口節點，只能有唯一一個。")
            
            gate_node = gate_nodes[0]
            print(f"{self.log_prefix} 找到唯一起始節點: {gate_node.id} ({gate_node.profession})。")

            # 將初始指令傳遞給該入口節點並啟動
            print(f"{self.log_prefix} 將初始指令傳遞給起始節點 {gate_node.id}")
            gate_node.received_inputs["user_prompt"] = self.process.initialPrompt
            await gate_node.check_and_run()

        except Exception as e:
            await self.handle_failure(f"工作流初始化失敗: {e}")

    async def propagate_result(self, completed_node_id: str, result: str):
        print(f"\n{self.log_prefix} ===== 開始執行 `propagate_result` (來源: {completed_node_id}) =====")
        if self.is_failed: return

        # ✅ 新增：超詳細日誌，打印出所有節點當前的依賴狀態
        print(f"{self.log_prefix} 當前所有節點的依賴列表:")
        for nid, n in self.nodes.items():
            print(f"  - 節點 {nid} ({n.profession}) 需要輸入: {n.input_ids}")

        self.master_history.append({
            "role": self.nodes[completed_node_id].profession,
            "content": result
        })

        downstream_tasks = []
        for downstream_node in self.nodes.values():
            # 核心檢查邏輯不變
            if completed_node_id in downstream_node.input_ids:
                print(f"{self.log_prefix} ✅ 找到下游: 節點 {downstream_node.id} 需要 {completed_node_id} 的輸出。 ")
                downstream_node.received_inputs[completed_node_id] = result
                downstream_tasks.append(downstream_node.check_and_run())
        
        if downstream_tasks:
            print(f"{self.log_prefix} 觸發了 {len(downstream_tasks)} 個下游節點的檢查。")
            await asyncio.gather(*downstream_tasks)
        else:
            print(f"{self.log_prefix} 節點 {completed_node_id} 沒有找到任何下游，檢查工作流是否結束。")
            await self.check_completion()
        print(f"{self.log_prefix} ===== `propagate_result` 執行完畢 =====\n")

    async def check_completion(self):
        print(f"{self.log_prefix} 開始執行 `check_completion` 函數。")
        all_completed = all(node.status in ["COMPLETED", "FAILED"] for node in self.nodes.values())
        
        if all_completed and not self.is_failed:
            print(f"{self.log_prefix} 所有節點均已完成，工作流結束。 ")
            final_node = self._find_final_node()
            final_artical = final_node.output_content if final_node else "(未能確定最終輸出)"
            
            conv_id = await self._save_workflow_history()

            await self.send_update({
                "status": "finished",
                "response": "工作流執行完畢",
                "final_artical": final_artical,
                "conversation_id": conv_id
            })
        else:
            print(f"{self.log_prefix} 尚有未完成的節點，工作流繼續。 সন")

    def _find_final_node(self) -> Optional[WorkflowNode]:
        for node in self.nodes.values():
            if not node.output_ids:
                return node
        return list(self.nodes.values())[-1] # Fallback

    async def handle_failure(self, error_message: str):
        if not self.is_failed:
            self.is_failed = True
            print(f"{self.log_prefix} 工作流失敗: {error_message}")
            await self.send_update({"status": "error", "response": error_message})

    async def send_update(self, data: dict):
        await self.websocket.send_json(data)

    async def execute_llm_call(self, system_prompt: str, task_description: str) -> Dict[str, Any]:
        print(f"{self.log_prefix} 開始執行 `execute_llm_call`。 সন")
        full_prompt = f"System Prompt: {system_prompt}\n\n--- 對話歷史與當前任務 ---\n{task_description}"
        response_content = ""
        try:
            async with httpx.AsyncClient() as client:
                url = f"{OLLAMA_HOST}/api/generate"
                payload = {"model": MODEL_NAME, "prompt": full_prompt, "stream": False}
                response = await client.post(url, json=payload, timeout=180.0)
                response.raise_for_status()
                data = response.json()
                response_content = data.get("response", "{} ").strip()
            print(f"{self.log_prefix} LLM API 調用成功。 সন")
            return json.loads(response_content)
        except httpx.RequestError as e:
            raise Exception(f"請求 LLM API 失敗: {e}")
        except json.JSONDecodeError:
            raise Exception(f"模型未回傳有效的 JSON。收到內容: {response_content[:200]}...")

    async def _save_workflow_history(self) -> int:
        print(f"{self.log_prefix} 開始執行 `_save_workflow_history`。 সন")
        title = f"工作流: {self.process.initialPrompt[:30]}..."
        conversation = await chat_service.create_conversation(self.db, self.user_id, title)
        for msg in self.master_history:
            is_user = msg["role"] == "User"
            formatted_content = f"**【{msg['role']}】**\n\n{msg['content']}"
            await chat_service.save_message(self.db, self.user_id, formatted_content, is_user, conversation.id)
        print(f"{self.log_prefix} 工作流歷史已存入對話 ID: {conversation.id}")
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
    user_id = 1  # 繞過驗證
    await manager.connect(websocket, user_id)
    print(f"使用者 {user_id} 的 Workflow WebSocket 連線成功 (驗證已繞過)。 সন")
    
    try:
        while True:
            data = await websocket.receive_text()
            print(f"收到的數據:{data} ")
            message = json.loads(data)
            msg_type = message.get("type")

            if msg_type == "start_workflow":
                payload_data = message.get("payload")
                if not payload_data:
                    await websocket.send_json({"status": "error", "response": "Payload 不得為空"})
                    continue
                
                # 使用新的 Pydantic 模型驗證 payload
                print(f"payload_data: {payload_data} ")

                workflow_process = WorkflowProcess(**payload_data)
                
                # 創建並啟動新的管理器
                manager_instance = DynamicWorkflowManager(workflow_process, websocket, user_id, db)
                asyncio.create_task(manager_instance.start())
            
            # 注意：此版本暫未實現運行中的 rollback，因為動態圖的回滾邏輯更複雜
            # 需要考慮狀態重置和依賴重新觸發，可在未來版本中添加。

    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)
        print(f"使用者 {user_id} 的 WebSocket 連線已斷開。 সন")
    except Exception as e:
        print(f"WebSocket 發生錯誤: {e}")
        if websocket.client_state.value != 3:
            try:
                await websocket.send_json({"status": "error", "response": f"伺服器內部錯誤: {e}"})
            except Exception as send_e:
                print(f"傳送錯誤訊息時失敗: {send_e}")
        manager.disconnect(websocket, user_id)