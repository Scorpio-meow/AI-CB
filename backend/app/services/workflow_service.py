import asyncio
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
import httpx
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import settings
from app.crud import crud_custom_agent
from app.crud.workflow_crud import save_workflow_history

logger = logging.getLogger(__name__)

# 檔案輸出目錄設定
OUTPUT_DIR = (Path(__file__).resolve().parents[2] / "data" / "workflow_outputs").resolve()
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 全局 HTTP 客戶端 (連接池模式)
_http_client: Optional[httpx.AsyncClient] = None
_client_lock = asyncio.Lock()

def get_default_prompt() -> str:
    """獲取預設的 prompt。"""
    return "你是一位資深編輯與溝通專家。請將內容優化得更清晰、結構化且具說服力：1) 核心訊息、2) 結構邏輯、3) 受眾語氣。盡量使用小節與條列；適合時用簡短表格輔助呈現。"

def sanitize_filename(name: str) -> str:
    """清理檔名,防止安全漏洞"""
    safe = "".join(c for c in name if c.isalnum() or c in ("-", "_", "+", ".", " "))
    return (safe.strip().replace(" ", "_") or "output")[:120]

async def save_text_file_async(basename: str, content: str) -> Path:
    """異步儲存檔案,避免阻塞事件循環"""
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    filename = f"{ts}_{sanitize_filename(basename)}.md"
    path = OUTPUT_DIR / filename
    
    # 使用 anyio 寫入檔案
    import anyio
    await anyio.to_thread.run_sync(
        lambda: path.write_text(content or "", encoding="utf-8")
    )
    return path

async def get_http_client() -> httpx.AsyncClient:
    """獲取或創建全局 HTTP 客戶端 (連接池模式)"""
    global _http_client
    async with _client_lock:
        if _http_client is None or _http_client.is_closed:
            _http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(settings.LLM_TIMEOUT),
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
            logger.info("Workflow HTTP client closed successfully.")


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
        self.input_ids = [i.rsplit('_', 1)[0] for i in agent_info.input]
        self.output_ids = [o.rsplit('_', 1)[0] for o in agent_info.output]
        self.manager = manager
        self.status = "PENDING"
        self.received_inputs: Dict[str, str] = {}
        self.output_content: Optional[str] = None
        self.log_prefix = f"[節點: {self.id} ({self.profession})]"
        self.activation_counts: Dict[str, int] = {input_id: 0 for input_id in self.input_ids}
        
        # 並發控制鎖 - 防止競態條件
        self._lock = asyncio.Lock()
        
        # 延遲初始化 system_prompt，防止在 __init__ 中同步阻塞 DB 呼叫
        self.system_prompt: Optional[str] = None

        if self.is_gate:
            logger.info(f"{self.log_prefix} 被指定為入口(gate)，將忽略其所有輸入連線。")
            self.input_ids = []
            self.activation_counts = {}

        logger.info(f"{self.log_prefix} 已初始化。輸入源: {self.input_ids}, 輸出目標: {self.output_ids}")

    def _load_system_prompt_sync(self) -> str:
        """從資料庫查詢此節點的 system_prompt (同步，配合 anyio.to_thread.run_sync 使用)"""
        db = self.manager.db
        user_id = self.manager.user_id
        system_prompt = None

        # 從資料庫查詢用戶可見的自訂 agent
        agent = crud_custom_agent.get_custom_agent_by_name_or_role(db, self.profession, user_id=user_id)
        if agent:
            system_prompt = agent.prompt
            visibility = "公開" if agent.is_public else "私人"
            logger.info(f"{self.log_prefix} 成功從資料庫載入自訂 prompt ({visibility})。")

        # 如果找不到，使用預設值
        if not system_prompt:
            system_prompt = get_default_prompt()
            logger.info(f"{self.log_prefix} 找不到對應的 prompt，使用 DEFAULT。")

        return system_prompt

    async def check_and_run(self, sender_id: str):
        """檢查並運行節點 (帶並發控制)"""
        async with self._lock:  # 防止競態條件
            logger.info(f"{self.log_prefix} 由 {sender_id} 觸發檢查... (收到 {len(self.received_inputs)} / 需要 {len(self.input_ids)})")
            
            if self.status == "COMPLETED":
                count = self.activation_counts.get(sender_id, 0)
                logger.info(f"{self.log_prefix} 已完成，但收到來自 {sender_id} 的循環激活。當前計數: {count}/{settings.WORKFLOW_CYCLE_LIMIT}")
                
                if count < settings.WORKFLOW_CYCLE_LIMIT:
                    self.activation_counts[sender_id] = count + 1
                    self.status = "PENDING"
                    logger.info(f"{self.log_prefix} 循環次數未達上限，重置狀態為 PENDING。")
                else:
                    logger.info(f"{self.log_prefix} 已達到循環次數上限 ({settings.WORKFLOW_CYCLE_LIMIT})，忽略來自 {sender_id} 的激活。")
                    # 不在鎖內調用 check_completion,避免死鎖
                    asyncio.create_task(self.manager.check_completion())
                    return

            if self.status != "PENDING":
                logger.info(f"{self.log_prefix} 狀態為 {self.status}，跳過執行。")
                return

            if all(input_id in self.received_inputs for input_id in self.input_ids):
                logger.info(f"{self.log_prefix} 所有依賴項均已滿足，準備執行。")
                self.status = "RUNNING"
        
        # 鎖外執行實際工作
        await self.run()

    async def run(self):
        logger.info(f"{self.log_prefix} 開始執行 `run` 函數。")
        self.status = "RUNNING"
        await self.manager.send_update({
            "nodeId": self.id,
            "status": "thinking",
            "message": f"{self.profession} 正在思考..."
        })

        # 懶加載 system prompt，防止同步阻塞 DB
        if self.system_prompt is None:
            import anyio
            self.system_prompt = await anyio.to_thread.run_sync(self._load_system_prompt_sync)

        input_parts = []
        for sender_id, content in self.received_inputs.items():
            sender_node = self.manager.nodes.get(sender_id)
            sender_role = sender_node.profession if sender_node else "User (初始指令)"
            input_parts.append(f"--- 來自「{sender_role}」的輸入 ---\n{content}")
        
        combined_input = "\n\n".join(input_parts)
        task_description = f"請基於以下全部內容，從你「{self.profession}」的角度出發，完成你的任務。\n\n{combined_input}"

        try:
            # 啟用 Tool Calling 支援
            raw_response = await self.manager.execute_llm_call(self.system_prompt, task_description, tools=True)
            self.output_content = raw_response if raw_response else "(內容生成失敗)"
            self.status = "COMPLETED"
            logger.info(f"{self.log_prefix} 執行成功。")

            # 將節點輸出寫入檔案 (異步)
            try:
                basename = f"{self.id}_{self.profession}"
                saved_path = await save_text_file_async(basename, self.output_content)
                file_name = saved_path.name
            except Exception as fe:
                logger.error(f"{self.log_prefix} 儲存檔案失敗: {fe}")
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
            logger.error(f"{self.log_prefix} {error_msg}")
            await self.manager.handle_failure(error_msg)


# =================================================================
# 3. 工作流管理器 (Workflow Manager)
# =================================================================

class DynamicWorkflowManager:
    def __init__(self, workflow_process: WorkflowProcess, websocket: Any, user_id: int, db: Session):
        self.process = workflow_process
        self.websocket = websocket
        self.user_id = user_id
        self.db = db
        self.master_history: List[Dict[str, str]] = []
        self.is_failed = False
        self.log_prefix = "[管理器]"
        
        logger.info(f"{self.log_prefix} 正在從 payload 初始化節點...")
        self.nodes: Dict[str, WorkflowNode] = {
            agent.ID: WorkflowNode(agent, self) for agent in self.process.agents
        }
        logger.info(f"{self.log_prefix} 所有節點初始化完畢。")

    async def start(self):
        logger.info(f"{self.log_prefix} 開始執行 `start` 函數。")
        try:
            await self.send_update({"status": "started", "message": "工作流啟動..."})
            self.master_history.append({"role": "User", "content": self.process.initialPrompt})

            gate_nodes = [node for node in self.nodes.values() if node.is_gate]
            
            if len(gate_nodes) != 1:
                raise ValueError(f"錯誤：工作流必須有且僅有一個入口節點(gate)，但找到了 {len(gate_nodes)} 個。")
            
            gate_node = gate_nodes[0]
            logger.info(f"{self.log_prefix} 找到唯一起始節點: {gate_node.id}。")

            gate_node.received_inputs["user_prompt"] = self.process.initialPrompt
            await gate_node.check_and_run(sender_id="_start_workflow")

        except Exception as e:
            await self.handle_failure(f"工作流初始化失敗: {e}")

    async def propagate_result(self, completed_node_id: str, result: str):
        logger.info(f"\n{self.log_prefix} ===== 開始傳播結果 (來源: {completed_node_id}) =====")
        if self.is_failed: 
            return

        # 添加到歷史記錄
        self.master_history.append({
            "role": self.nodes[completed_node_id].profession,
            "content": result
        })
        
        # 限制歷史記錄大小以防記憶體洩漏
        if len(self.master_history) > settings.WORKFLOW_MAX_HISTORY:
            # 保留第一條 (User 初始問題) 和最近的記錄
            self.master_history = [self.master_history[0]] + self.master_history[-(settings.WORKFLOW_MAX_HISTORY-1):]
            logger.info(f"{self.log_prefix} 歷史記錄已裁剪至 {settings.WORKFLOW_MAX_HISTORY} 條")

        output_target_ids = self.nodes[completed_node_id].output_ids
        if not output_target_ids:
            logger.info(f"{self.log_prefix} 節點 {completed_node_id} 沒有下游，檢查工作流是否結束。")
            await self.check_completion()
            return

        downstream_tasks = []
        for target_id in output_target_ids:
            downstream_node = self.nodes.get(target_id)
            if downstream_node:
                logger.info(f"{self.log_prefix} 找到下游: 將結果從 {completed_node_id} 傳遞到 {downstream_node.id}。")
                downstream_node.received_inputs[completed_node_id] = result
                downstream_tasks.append(downstream_node.check_and_run(sender_id=completed_node_id))
        
        if downstream_tasks:
            logger.info(f"{self.log_prefix} 觸發了 {len(downstream_tasks)} 個下游節點的檢查。")
            await asyncio.gather(*downstream_tasks)
        else:
            logger.warning(f"{self.log_prefix} 警告：節點 {completed_node_id} 有輸出目標但未找到對應節點實例。")
            await self.check_completion()
        
        logger.info(f"{self.log_prefix} ===== 結果傳播完畢 =====\n")

    async def check_completion(self):
        logger.info(f"{self.log_prefix} 開始執行 `check_completion` 函數。")
        all_settled = all(node.status in ["COMPLETED", "FAILED"] for node in self.nodes.values())
        
        if all_settled and not self.is_failed:
            logger.info(f"{self.log_prefix} 所有節點均已穩定，準備進行最終總結。")
            final_node = self._find_final_node()
            content_to_summarize = final_node.output_content if final_node else "(未能確定用於總結的內容)"

            await self.send_update({"status": "info", "message": "所有流程已完成，正在進行最終總結..."})
            
            summary_task = f"請將以下全部內容，做一個全面、完整、有條理的最終總結報告。\n\n---\n{content_to_summarize}\n---"
            default_system_prompt = get_default_prompt()
            
            try:
                final_summary = await self.execute_llm_call(default_system_prompt, summary_task)
                logger.info(f"{self.log_prefix} DEFAULT Agent 總結完成。")
                self.master_history.append({"role": "最終總結 (DEFAULT)", "content": final_summary})
            except Exception as e:
                logger.error(f"{self.log_prefix} DEFAULT Agent 總結失敗: {e}")
                final_summary = f"最終總結步驟失敗: {e}"

            # 儲存最終總結為檔案 (異步)
            final_file_name = None
            try:
                final_path = await save_text_file_async("final_summary", final_summary)
                final_file_name = final_path.name
            except Exception as fe:
                logger.error(f"{self.log_prefix} 儲存最終總結檔案失敗: {fe}")

            # 儲存工作流對話歷史
            conv_id = await save_workflow_history(
                self.db, 
                self.user_id, 
                self.process.initialPrompt, 
                self.master_history
            )

            await self.send_update({
                "status": "finished",
                "response": "工作流執行完畢",
                "final_artical": final_summary,
                "conversation_id": conv_id,
                "final_file_name": final_file_name,
                "final_download_url": f"/api/workflow/download/{final_file_name}" if final_file_name else None
            })
        else:
            logger.info(f"{self.log_prefix} 尚有 PENDING 或 RUNNING 的節點，工作流繼續。")

    def _find_final_node(self) -> Optional[WorkflowNode]:
        for node in self.nodes.values():
            if not node.output_ids:
                return node
        return list(self.nodes.values())[-1]

    async def handle_failure(self, error_message: str):
        if not self.is_failed:
            self.is_failed = True
            logger.error(f"{self.log_prefix} 工作流失敗: {error_message}")
            await self.send_update({"status": "error", "response": error_message})

    async def send_update(self, data: dict):
        try:
            await self.websocket.send_json(data)
        except Exception as e:
            logger.error(f"Failed to send JSON via websocket: {e}")

    async def execute_llm_call(
        self,
        system_prompt: str,
        task_description: str,
        tools: Optional[bool] = None
    ) -> str:
        """獨立的 LLM 調用函數，支援 Tool Calling 與策略 Provider 切換。"""
        logger.info(f"{self.log_prefix} 開始執行 `execute_llm_call`。")
        
        # 輸入驗證
        if not system_prompt or not task_description:
            raise ValueError("system_prompt 和 task_description 不能為空")
            
        from app.core.llm_provider import get_llm_provider
        provider = get_llm_provider()
        
        # 建立對話 messages (包含自訂歷史上下文，但過濾非標準 role，以相容 OpenAI / Ollama 規範)
        messages = [
            {"role": "system", "content": system_prompt}
        ]
        
        if self.master_history:
            context_messages = self.master_history[-settings.WORKFLOW_MAX_CONTEXT:]
            for entry in context_messages:
                role = entry.get("role", "")
                content = entry.get("content", "")
                
                # 跳過 User 角色,避免與 task_description 重複
                if role == "User":
                    continue
                    
                # 其它專業角色轉換為 assistant 角色，供對話生成上下文
                messages.append({
                    "role": "assistant",
                    "content": f"[{role}]\n{content}"
                })
                
        messages.append({
            "role": "user",
            "content": task_description
        })
        
        # 呼叫 provider 執行
        # 我們將使用 TOOL_SCHEMAS 提供所有的工具定義給 LLM
        from app.tools.registry import TOOL_SCHEMAS
        
        # 只有在傳入了 tools 或開啟了 Tool Calling 支援時才傳入 TOOL_SCHEMAS
        active_tools = TOOL_SCHEMAS if tools is not None else None
        
        return await provider.chat_with_tools(
            messages=messages,
            tools=active_tools,
            max_iterations=5
        )
