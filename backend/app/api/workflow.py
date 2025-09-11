# -*- coding: utf-8 -*-
"""
workflow.py (Refactored v6: Dynamic Agent Loading)

This version refactors agent prompt loading to be dynamic.
1.  Removes global loading of custom agent prompts at startup.
2.  The WorkflowNode now fetches the agent's prompt from the database
    dynamically upon initialization.
3.  The /professions endpoint also fetches dynamically to ensure the list is always up-to-date.
"""

import asyncio
import json
import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

import httpx
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.chat import manager
from app.models.database import get_db, SessionLocal
from app.services.chat_service import ChatService
from app.crud import crud_custom_agent

# --- Constants and System Prompts ---
try:
    OLLAMA_HOST = os.environ["LLM_API_BASE"]
except KeyError:
    raise RuntimeError("Environment variable LLM_API_BASE is required. Please set it in .env or environment.")

try:
    MODEL_NAME = os.environ["MODEL_NAME"]
except KeyError:
    raise RuntimeError("Environment variable MODEL_NAME is required. Please set it in .env or environment.")


WORKFLOW_TIMEOUT = float(os.getenv("WORKFLOW_TIMEOUT", "180"))

CYCLE_LIMIT = 2

def get_default_prompt():
    """獲取預設的 prompt。"""
    return "你是一位資深編輯與溝通專家。請將內容優化得更清晰、結構化且具說服力：1) 核心訊息、2) 結構邏輯、3) 受眾語氣。盡量使用小節與條列；適合時用簡短表格輔助呈現。"

router = APIRouter()
chat_service = ChatService()

@router.get("/professions", response_model=List[str], summary="獲取所有可用的專業角色")
def get_professions(db: Session = Depends(get_db)):
    """
    返回所有可用的專業角色列表，僅包含自訂的角色。
    會對列表進行去重和排序。
    """
    unique_professions: set[str] = set()

    try:
        custom_agents = crud_custom_agent.get_custom_agents(db)
        for agent in custom_agents:
            unique_professions.add(agent.name)
            unique_professions.add(agent.role)
    except Exception as e:
        print(f"從資料庫載入自訂 Agent 列表失敗: {e}")

    return sorted(list(unique_professions))

# 檔案輸出目錄設定
OUTPUT_DIR = (Path(__file__).resolve().parents[2] / "data" / "workflow_outputs").resolve()
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def _sanitize_filename(name: str) -> str:
    safe = "".join(c for c in name if c.isalnum() or c in ("-", "_", "+", ".", " "))
    return (safe.strip().replace(" ", "_") or "output")[:120]

def _save_text_file(basename: str, content: str) -> Path:
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    filename = f"{ts}_{_sanitize_filename(basename)}.md"
    path = OUTPUT_DIR / filename
    path.write_text(content or "", encoding="utf-8")
    return path

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
        self.status = "PENDING"
        self.received_inputs: Dict[str, str] = {}
        self.output_content: Optional[str] = None
        self.log_prefix = f"[節點: {self.id} ({self.profession})]"
        self.activation_counts: Dict[str, int] = {input_id: 0 for input_id in self.input_ids}
        
        # 動態獲取 System Prompt
        self._set_system_prompt()

        if self.is_gate:
            print(f"{self.log_prefix} 被指定為入口(gate)，將忽略其所有輸入連線。")
            self.input_ids = []
            self.activation_counts = {}

        print(f"{self.log_prefix} 已初始化。輸入源: {self.input_ids}, 輸出目標: {self.output_ids}")

    def _set_system_prompt(self):
        """動態設定此節點的 system_prompt"""
        db = self.manager.db
        system_prompt = None

        # 從資料庫查詢自訂 agent
        agent = crud_custom_agent.get_custom_agent_by_name_or_role(db, self.profession)
        if agent:
            system_prompt = agent.prompt
            print(f"{self.log_prefix} 成功從資料庫載入自訂 prompt。")

        # 如果找不到，使用預設值
        if not system_prompt:
            system_prompt = get_default_prompt()
            print(f"{self.log_prefix} 找不到對應的 prompt，使用 DEFAULT。")

        self.system_prompt = system_prompt

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

            # 將節點輸出寫入檔案
            try:
                basename = f"{self.id}_{self.profession}"
                saved_path = _save_text_file(basename, self.output_content)
                file_name = saved_path.name
            except Exception as fe:
                print(f"{self.log_prefix} 儲存檔案失敗: {fe}")
                file_name = None

            await self.manager.send_update({
                "nodeId": self.id,
                "status": "completed",
                "response": self.output_content,
                "file_name": file_name,
                "download_url": f"/api/workflow/download/{file_name}" if file_name else None
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
            default_system_prompt = get_default_prompt()
            
            try:
                final_summary = await self.execute_llm_call(default_system_prompt, summary_task)
                print(f"{self.log_prefix} DEFAULT Agent 總結完成。 ")
                self.master_history.append({"role": "最終總結 (DEFAULT)", "content": final_summary})
            except Exception as e:
                print(f"{self.log_prefix} DEFAULT Agent 總結失敗: {e}")
                final_summary = f"最終總結步驟失敗: {e}"

            # 儲存最終總結為檔案
            final_file_name = None
            try:
                final_path = _save_text_file("final_summary", final_summary)
                final_file_name = final_path.name
            except Exception as fe:
                print(f"{self.log_prefix} 儲存最終總結檔案失敗: {fe}")

            conv_id = await self._save_workflow_history()

            await self.send_update({
                "status": "finished",
                "response": "工作流執行完畢",
                "final_artical": final_summary,
                "conversation_id": conv_id,
                "final_file_name": final_file_name,
                "final_download_url": f"/api/workflow/download/{final_file_name}" if final_file_name else None
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
                response = await client.post(url, json=payload, timeout=WORKFLOW_TIMEOUT)
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

@router.websocket("/ws")
async def workflow_websocket_endpoint(websocket: WebSocket, db: Session = Depends(get_db)):
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

@router.get("/download/{file_name}")
async def download_generated_file(file_name: str):
    # 僅允許從 workflow_outputs 目錄下載
    target_path = (OUTPUT_DIR / file_name).resolve()
    try:
        # 防止目錄穿越
        if OUTPUT_DIR not in target_path.parents and target_path != OUTPUT_DIR:
            raise HTTPException(status_code=400, detail="非法路徑")
        if not target_path.exists():
            raise HTTPException(status_code=404, detail="檔案不存在")
        return FileResponse(path=str(target_path), filename=file_name, media_type="text/markdown; charset=utf-8")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"下載失敗: {e}")