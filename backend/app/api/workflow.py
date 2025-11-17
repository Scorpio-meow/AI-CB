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
from app.core.jwt_auth import get_current_active_user  # JWT 認證

# --- Constants and System Prompts ---
OLLAMA_HOST = os.getenv("LLM_API_BASE", "").strip()
if not OLLAMA_HOST:
    # Avoid import-time failure; warn and let callers handle missing host at runtime.
    print("⚠️ Environment variable LLM_API_BASE is not set. Workflow endpoints that call external LLM API will fail unless set.")

MODEL_NAME = os.getenv("MODEL_NAME", "gpt-oss:20b").strip()
if not MODEL_NAME:
    print("⚠️ Environment variable MODEL_NAME is not set; defaulting to 'gpt-oss:20b'.")


WORKFLOW_TIMEOUT = float(os.getenv("WORKFLOW_TIMEOUT", "180"))
CYCLE_LIMIT = int(os.getenv("WORKFLOW_CYCLE_LIMIT", "2"))  # 可配置的循環限制
MAX_HISTORY_SIZE = int(os.getenv("WORKFLOW_MAX_HISTORY", "20"))  # 防止記憶體洩漏
MAX_CONTEXT_MESSAGES = int(os.getenv("WORKFLOW_MAX_CONTEXT", "5"))  # LLM 上下文限制

# 全局 HTTP 客戶端 (連接池) - 提升效能
_http_client: Optional[httpx.AsyncClient] = None
_client_lock = asyncio.Lock()

def get_default_prompt():
    """獲取預設的 prompt。"""
    return "你是一位資深編輯與溝通專家。請將內容優化得更清晰、結構化且具說服力：1) 核心訊息、2) 結構邏輯、3) 受眾語氣。盡量使用小節與條列；適合時用簡短表格輔助呈現。"

async def get_http_client() -> httpx.AsyncClient:
    """獲取或創建全局 HTTP 客戶端 (連接池模式)"""
    global _http_client
    async with _client_lock:
        if _http_client is None or _http_client.is_closed:
            _http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(WORKFLOW_TIMEOUT),
                limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
            )
        return _http_client

async def close_http_client():
    """關閉全局 HTTP 客戶端"""
    global _http_client
    async with _client_lock:
        if _http_client is not None:
            await _http_client.aclose()
            _http_client = None

router = APIRouter()
chat_service = ChatService()

@router.get("/professions", response_model=List[str], summary="獲取所有可用的專業角色")
def get_professions(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_active_user)
):
    """
    返回所有可用的專業角色列表，僅包含當前用戶可見的角色。
    包含所有公開 Agent 和用戶自己的私人 Agent。
    會對列表進行去重和排序。
    """
    unique_professions: set[str] = set()

    try:
        user_id = current_user.get("user_id")
        # 獲取用戶可見的 Agent (公開 + 自己的私人)
        custom_agents = crud_custom_agent.get_custom_agents(db, user_id=user_id)
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
    """清理檔名,防止安全漏洞"""
    safe = "".join(c for c in name if c.isalnum() or c in ("-", "_", "+", ".", " "))
    return (safe.strip().replace(" ", "_") or "output")[:120]

async def _save_text_file_async(basename: str, content: str) -> Path:
    """異步儲存檔案,避免阻塞事件循環"""
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    filename = f"{ts}_{_sanitize_filename(basename)}.md"
    path = OUTPUT_DIR / filename
    
    # 使用 asyncio 寫入檔案
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        None, 
        lambda: path.write_text(content or "", encoding="utf-8")
    )
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
        
        # 並發控制鎖 - 防止競態條件
        self._lock = asyncio.Lock()
        
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
        user_id = self.manager.user_id
        system_prompt = None

        # 從資料庫查詢用戶可見的自訂 agent
        agent = crud_custom_agent.get_custom_agent_by_name_or_role(db, self.profession, user_id=user_id)
        if agent:
            system_prompt = agent.prompt
            visibility = "公開" if agent.is_public else "私人"
            print(f"{self.log_prefix} 成功從資料庫載入自訂 prompt ({visibility})。")

        # 如果找不到，使用預設值
        if not system_prompt:
            system_prompt = get_default_prompt()
            print(f"{self.log_prefix} 找不到對應的 prompt，使用 DEFAULT。")

        self.system_prompt = system_prompt

    async def check_and_run(self, sender_id: str):
        """檢查並運行節點 (帶並發控制)"""
        async with self._lock:  # 防止競態條件
            print(f"{self.log_prefix} 由 {sender_id} 觸發檢查... (收到 {len(self.received_inputs)} / 需要 {len(self.input_ids)})")
            
            if self.status == "COMPLETED":
                count = self.activation_counts.get(sender_id, 0)
                print(f"{self.log_prefix} 已完成，但收到來自 {sender_id} 的循環激活。當前計數: {count}/{CYCLE_LIMIT}")
                
                if count < CYCLE_LIMIT:
                    self.activation_counts[sender_id] = count + 1
                    self.status = "PENDING"
                    print(f"{self.log_prefix} 循環次數未達上限，重置狀態為 PENDING。")
                else:
                    print(f"{self.log_prefix} 已達到循環次數上限 ({CYCLE_LIMIT})，忽略來自 {sender_id} 的激活。")
                    # 不在鎖內調用 check_completion,避免死鎖
                    asyncio.create_task(self.manager.check_completion())
                    return

            if self.status != "PENDING":
                print(f"{self.log_prefix} 狀態為 {self.status}，跳過執行。")
                return

            if all(input_id in self.received_inputs for input_id in self.input_ids):
                print(f"{self.log_prefix} ✅ 所有依賴項均已滿足，準備執行。")
                # 在鎖外執行,避免長時間持鎖
                self.status = "RUNNING"
        
        # 鎖外執行實際工作
        await self.run()

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

            # 將節點輸出寫入檔案 (異步)
            try:
                basename = f"{self.id}_{self.profession}"
                saved_path = await _save_text_file_async(basename, self.output_content)
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

        # 添加到歷史記錄,並限制大小防止記憶體洩漏
        self.master_history.append({
            "role": self.nodes[completed_node_id].profession,
            "content": result
        })
        
        # 保持歷史記錄在合理範圍內
        if len(self.master_history) > MAX_HISTORY_SIZE:
            # 保留第一條 (User 初始問題) 和最近的記錄
            self.master_history = [self.master_history[0]] + self.master_history[-(MAX_HISTORY_SIZE-1):]
            print(f"{self.log_prefix} 歷史記錄已裁剪至 {MAX_HISTORY_SIZE} 條")

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

            # 儲存最終總結為檔案 (異步)
            final_file_name = None
            try:
                final_path = await _save_text_file_async("final_summary", final_summary)
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
        """獨立的 LLM 調用函數，使用連接池和精確錯誤處理。"""
        print(f"{self.log_prefix} 開始執行 `execute_llm_call`。 ")
        
        # 輸入驗證
        if not system_prompt or not task_description:
            raise ValueError("system_prompt 和 task_description 不能為空")
        
        try:
            client = await get_http_client()  # 使用連接池
            url = f"{OLLAMA_HOST}/api/chat"
            
            # 構建 messages 列表
            messages = [
                {
                    "role": "system",
                    "content": system_prompt[:4000]  # 限制長度,防止過長
                }
            ]
            
            # 添加工作流歷史上下文 (限制數量,防止記憶體洩漏)
            if self.master_history:
                context_messages = self.master_history[-MAX_CONTEXT_MESSAGES:]
                for entry in context_messages:
                    role = entry.get("role", "")
                    content = entry.get("content", "")
                    
                    # 跳過 User 角色,避免與 task_description 重複
                    if role == "User":
                        continue
                        
                    # 其他專業角色視為 assistant,並保留角色標註
                    messages.append({
                        "role": "assistant",
                        "content": f"[{role}]\n{content[:2000]}"  # 限制單條長度
                    })
            
            # 添加當前任務描述
            messages.append({
                "role": "user",
                "content": task_description[:4000]  # 限制長度
            })
            
            payload = {
                "model": MODEL_NAME,
                "messages": messages,
                "stream": False
            }
            
            print(f"{self.log_prefix} 調用 LLM API，messages 數量: {len(messages)}")
            
            # 使用連接池的客戶端
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            
            # /api/chat 返回格式: {"message": {"role": "assistant", "content": "..."}}
            response_text = data.get("message", {}).get("content", "").strip()
            
            if not response_text:
                raise ValueError("LLM 返回空響應")
            
            print(f"{self.log_prefix} LLM API 調用成功，響應長度: {len(response_text)} 字符。 ")
            return response_text
            
        except httpx.TimeoutException as e:
            error_msg = f"LLM API 請求超時 ({WORKFLOW_TIMEOUT}s): {str(e)}"
            print(f"{self.log_prefix} {error_msg}")
            raise TimeoutError(error_msg) from e
            
        except httpx.HTTPStatusError as e:
            error_msg = f"LLM API HTTP 錯誤 {e.response.status_code}: {e.response.text[:200]}"
            print(f"{self.log_prefix} {error_msg}")
            raise RuntimeError(error_msg) from e
            
        except httpx.RequestError as e:
            error_msg = f"LLM API 網路請求失敗: {str(e)}"
            print(f"{self.log_prefix} {error_msg}")
            raise ConnectionError(error_msg) from e
            
        except (KeyError, ValueError) as e:
            error_msg = f"LLM API 響應格式錯誤: {str(e)}"
            print(f"{self.log_prefix} {error_msg}")
            raise ValueError(error_msg) from e
            
        except Exception as e:
            error_msg = f"LLM API 未預期錯誤 ({type(e).__name__}): {str(e)}"
            print(f"{self.log_prefix} {error_msg}")
            raise RuntimeError(error_msg) from e

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
    """工作流 WebSocket 端點 - 改進錯誤處理和資源管理"""
    user_id = 1  # TODO: 實施適當的身份驗證
    await manager.connect(websocket, user_id)
    print(f"使用者 {user_id} 的 Workflow WebSocket 連線成功 (驗證已繞過)。 ")
    
    try:
        while True:
            try:
                # 設置接收超時,避免無限等待
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=3600.0  # 1小時超時
                )
                
                # 驗證 JSON 格式
                try:
                    message = json.loads(data)
                except json.JSONDecodeError as e:
                    await websocket.send_json({
                        "status": "error", 
                        "response": f"無效的 JSON 格式: {str(e)}"
                    })
                    continue
                
                msg_type = message.get("type")

                if msg_type == "start_workflow":
                    payload_data = message.get("payload")
                    
                    # 輸入驗證
                    if not payload_data:
                        await websocket.send_json({
                            "status": "error", 
                            "response": "Payload 不得為空"
                        })
                        continue
                    
                    # 驗證 payload 結構
                    try:
                        workflow_process = WorkflowProcess(**payload_data)
                    except Exception as e:
                        await websocket.send_json({
                            "status": "error",
                            "response": f"Payload 格式錯誤: {str(e)}"
                        })
                        continue
                    
                    # 啟動工作流
                    try:
                        manager_instance = DynamicWorkflowManager(
                            workflow_process, websocket, user_id, db
                        )
                        asyncio.create_task(manager_instance.start())
                    except Exception as e:
                        await websocket.send_json({
                            "status": "error",
                            "response": f"工作流啟動失敗: {str(e)}"
                        })
                else:
                    await websocket.send_json({
                        "status": "error",
                        "response": f"未知的訊息類型: {msg_type}"
                    })
                    
            except asyncio.TimeoutError:
                print(f"使用者 {user_id} 的 WebSocket 連線超時，發送心跳...")
                try:
                    await websocket.send_json({"status": "ping"})
                except Exception:
                    break  # 連接已斷開
                    
    except WebSocketDisconnect:
        print(f"使用者 {user_id} 的 WebSocket 正常斷線。 ")
        
    except Exception as e:
        print(f"WebSocket 發生未預期錯誤 ({type(e).__name__}): {e}")
        # 嘗試發送錯誤訊息
        if websocket.client_state.value != 3:  # 3 = CLOSED
            try:
                await websocket.send_json({
                    "status": "error", 
                    "response": f"伺服器內部錯誤: {type(e).__name__}"
                })
            except Exception as send_e:
                print(f"傳送錯誤訊息時失敗: {send_e}")
                
    finally:
        # 確保清理資源
        manager.disconnect(websocket, user_id)
        print(f"使用者 {user_id} 的 WebSocket 資源已清理。 ")

@router.get("/download/{file_name}")
async def download_generated_file(file_name: str):
    """下載工作流生成的檔案 - 改進安全性"""
    # 清理檔名,防止路徑穿越攻擊
    safe_filename = _sanitize_filename(file_name)
    target_path = (OUTPUT_DIR / safe_filename).resolve()
    
    try:
        # 嚴格的路徑驗證
        if not target_path.is_relative_to(OUTPUT_DIR):
            raise HTTPException(status_code=400, detail="非法路徑")
            
        if not target_path.exists():
            raise HTTPException(status_code=404, detail="檔案不存在")
            
        if not target_path.is_file():
            raise HTTPException(status_code=400, detail="目標不是檔案")
        
        # 檢查檔案大小 (防止大檔案攻擊)
        file_size = target_path.stat().st_size
        max_size = 50 * 1024 * 1024  # 50MB
        if file_size > max_size:
            raise HTTPException(status_code=413, detail="檔案過大")
            
        return FileResponse(
            path=str(target_path), 
            filename=safe_filename, 
            media_type="text/markdown; charset=utf-8"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"下載檔案時發生錯誤: {e}")
        raise HTTPException(status_code=500, detail=f"下載失敗: {type(e).__name__}")

# =================================================================
# 應用生命週期管理
# =================================================================

@router.on_event("shutdown")
async def shutdown_event():
    """應用關閉時清理資源"""
    print("正在關閉 Workflow 模組...")
    await close_http_client()
    print("HTTP 客戶端已關閉")