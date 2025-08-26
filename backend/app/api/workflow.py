
import json
import asyncio
import time
import os
import httpx
from typing import Dict, List, Any, Tuple

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends

from app.models.payloads import WorkflowPayload, Node, Edge
from app.api.chat import manager
from app.services.auth_service import AuthService

# =================================================================
# === 環境變數設定 (保持不變) =====================================
# =================================================================
OLLAMA_HOST = os.getenv("GITHUB_API_BASE", "https://fc5d1d0fc900.ngrok-free.app")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-oss:20b")

router = APIRouter()
auth_service = AuthService()

# =================================================================
# === ✅ NEW: 增強版 SYSTEM_PROMPTS ===============================
# =================================================================
# 新增了 Aggregator 角色，並微調了其他角色的描述
SYSTEM_PROMPTS = {
    "PM": "你是一位經驗豐富的專案經理。你的任務是根據初始指令，生成一份詳細的專案計畫。你的所有輸出都必須是一個 JSON 物件，格式為 {\"artical\": \"你的完整專案計畫\"}	extit{",
    "工程師": "你是一位務實的資深軟體工程師。你的任務是審核上游傳來的內容，並從技術可行性、系統穩定性與開發成本的角度，直接修改內容使其更完善。你的所有輸出都必須是一個 JSON 物件，格式為 {\"artical\": \"修改後的完整內文\"}	extit{",
    "業務分析師": "你是一位敏銳的業務分析師。你的任務是審核上游傳來的內容，並從市場趨勢、競爭對手與營收模式的角度，直接修改內容使其更完善。你的所有輸出都必須是一個 JSON 物件，格式為 {\"artical\": \"修改後的完整內文\"}	extit{",
    "Aggregator": "你是一個資訊聚合器。你的任務是將多個上游角色提供的內容整合成一份通順、連貫的文件。直接輸出整合後的完整內容。你的所有輸出都必須是一個 JSON 物件，格式為 {\"artical\": \"整合後的完整內文\"}	extit{",
    "default": "你是一個通用的 AI 助理。你的任務是審核上游傳來的內容，並直接修改使其更完善。你的所有輸出都必須是一個 JSON 物件，格式為 {\"artical\": \"修改後的完整內文\"}	extit{"
}


class WorkflowOrchestrator:
    def __init__(self, payload: WorkflowPayload, websocket: WebSocket, user_id: int):
        self.payload = payload
        self.websocket = websocket
        self.user_id = user_id
        self.nodes = {node.id: node for node in payload.nodes}
        
        # ✅ NEW: 支援多個下游節點的邊線地圖
        self.edge_map: Dict[str, List[str]] = {node.id: [] for node in payload.nodes}
        for edge in payload.edges:
            self.edge_map[edge.source].append(edge.target)

        self.master_history: List[Dict[str, str]] = []
        self.node_outputs: Dict[str, Any] = {}
        
        # ✅ NEW: 追蹤回滾次數
        self.rollback_counts: Dict[str, int] = {node.id: 0 for node in payload.nodes}
        self.max_rollbacks = 3

        self.conversation_id = None

    async def _send_update(self, data: dict):
        """向前端發送更新訊息"""
        await self.websocket.send_json(data)

    def _build_contextual_prompt(self, task_description: str, role_history: List[Dict[str, str]]) -> str:
        """建立包含上下文的 Prompt"""
        history_str = "\n".join([f"【{msg['role']}】:\n{msg['content']}" for msg in role_history])
        prompt = f"""
        ---"對話背景"---
        {history_str}\n
        --- END ---\n
        --- 當前任務 ---
        {task_description}\n
        --- END ---
        """
        return prompt

    async def _execute_agent_turn(self, node_id: str, task_description: str, role_history: List[Dict[str, str]]) -> Dict[str, any]:
        """執行單個 Agent 的回合，包含 API 呼叫"""
        node = self.nodes[node_id]
        role = node.data.originalLabel
        system_prompt = SYSTEM_PROMPTS.get(role, SYSTEM_PROMPTS["default"])
        
        await self._send_update({"nodeId": node_id, "status": "thinking", "message": f"{role} 正在思考..."})
        
        contextual_prompt = self._build_contextual_prompt(task_description, role_history)
        final_prompt = f"System Prompt: {system_prompt}\n\n{contextual_prompt}"
        
        response_content = ""
        
        try:
            async with httpx.AsyncClient() as client:
                url = f"{OLLAMA_HOST}/api/generate"
                payload = {"model": MODEL_NAME, "prompt": final_prompt, "stream": False}
                response = await client.post(url, json=payload, timeout=180.0)
                response.raise_for_status()
                data = response.json()
                response_content = data.get("response", "{}").strip()

            response_data = json.loads(response_content)
            artical = response_data.get("artical", f"解析失敗或內容為空: {response_content}")
            
            self.node_outputs[node_id] = artical # 儲存節點輸出
            self.master_history.append({"role": role, "content": artical})

            await self._send_update({
                "nodeId": node_id, "status": "completed", "response": artical, "can_rollback": True
            })
            return response_data
            
        except httpx.RequestError as e:
            error_msg = f"呼叫 OLLAMA API 失敗: {e}"
            await self._send_update({"nodeId": node_id, "status": "error", "response": error_msg})
            raise
        except json.JSONDecodeError:
            error_msg = f"模型未回傳有效的 JSON 格式。收到內容: {response_content[:300]}..."
            await self._send_update({"nodeId": node_id, "status": "error", "response": error_msg})
            raise
        except Exception as e:
            error_msg = f"模型呼叫或處理失敗: {e}"
            await self._send_update({"nodeId": node_id, "status": "error", "response": error_msg})
            raise

    # =================================================================
    # === ✅✅✅ NEW: 核心邏輯 - 工作流執行 ============================
    # =================================================================
    async def start(self):
        """開始執行工作流"""
        try:
            self.conversation_id = int(time.time())
            self.master_history.append({"role": "User", "content": self.payload.initialPrompt})
            await self._send_update({"status": "started", "conversationId": self.conversation_id})
            
            entry_point_id = self.payload.entryPointId
            if not entry_point_id:
                raise ValueError("未定義進入點 (entryPointId)")

            # 從進入點開始，逐層執行
            await self._process_node(entry_point_id, self.payload.initialPrompt, [self.master_history[0]])

            final_artical = self.node_outputs.get(list(self.nodes.keys())[-1], "工作流未產生最終結果。")
            await self._send_update({"status": "finished", "response": "工作流執行完畢", "final_artical": final_artical})

        except Exception as e:
            print(f"工作流發生嚴重錯誤: {e}")
            await self._send_update({"status": "error", "response": str(e)})

    async def _process_node(self, node_id: str, input_content: str, history: List[Dict[str, str]]):
        """遞歸處理單個節點及其下游節點"""
        node = self.nodes[node_id]
        role = node.data.originalLabel

        # 1. 執行當前節點
        if role == "Aggregator":
            # Aggregator 的輸入是多個上游內容的列表
            task = f"請將以下多份內容整合成一份連貫的文件：\n\n---\n{input_content}\n---"
        else:
            task = f"請基於以下內容，從你的「{role}」角度出發，完成你的任務。\n\n---\n{input_content}\n---"
        
        await self._execute_agent_turn(node_id, task, history)
        
        # 2. 處理下游節點
        downstream_nodes = self.edge_map.get(node_id, [])
        if not downstream_nodes:
            # 如果是最後一個節點，流程結束
            return

        # 獲取當前節點的輸出，作為下游節點的輸入
        current_output = self.node_outputs[node_id]
        
        if len(downstream_nodes) == 1:
            # 如果只有一個下游節點，直接遞歸處理
            next_node_id = downstream_nodes[0]
            await self._process_node(next_node_id, current_output, self.master_history)
        
        elif len(downstream_nodes) > 1:
            # ✅ NEW: 並發處理多個下游節點
            await self._send_update({"nodeId": node_id, "status": "info", "message": f"正在將任務分發給 {len(downstream_nodes)} 個下游角色..."})
            
            # 建立並發執行的任務列表
            parallel_tasks = []
            for next_node_id in downstream_nodes:
                # 每個並發任務都是一個獨立的 agent turn
                next_node = self.nodes[next_node_id]
                next_role = next_node.data.originalLabel
                parallel_task_desc = f"請基於以下內容，從你的「{next_role}」角度出發，完成你的任務。\n\n---\n{current_output}\n---"
                parallel_tasks.append(self._execute_agent_turn(next_node_id, parallel_task_desc, self.master_history))
            
            # 使用 asyncio.gather 執行並發任務
            parallel_results = await asyncio.gather(*parallel_tasks, return_exceptions=True)

            # 檢查並發任務是否有異常
            for result in parallel_results:
                if isinstance(result, Exception):
                    # 如果有異常，整個工作流失敗
                    raise result

            # ✅ NEW: 尋找聚合器 (Aggregator) 來合併結果
            # 假設第一個並發節點的下游是聚合器
            aggregator_node_id = None
            if downstream_nodes:
                first_parallel_node_id = downstream_nodes[0]
                potential_aggregators = self.edge_map.get(first_parallel_node_id, [])
                if potential_aggregators and self.nodes[potential_aggregators[0]].data.originalLabel == "Aggregator":
                    aggregator_node_id = potential_aggregators[0]

            if aggregator_node_id:
                # 將所有並發結果合併成單一輸入，交給聚合器
                combined_input = "\n\n---\n\n".join([self.node_outputs[nid] for nid in downstream_nodes])
                await self._process_node(aggregator_node_id, combined_input, self.master_history)
            else:
                # 如果沒有聚合器，並發分支結束後，整個流程就結束
                await self._send_update({"status": "info", "message": "並行任務已完成，但未找到下游聚合器，流程結束。"})


    # =================================================================
    # === ✅✅✅ NEW: 核心邏輯 - 處理回滾 ============================
    # =================================================================
    async def handle_rollback(self, node_id: str, user_feedback: str):
        """處理用戶請求的回滾"""
        if self.rollback_counts.get(node_id, 0) >= self.max_rollbacks:
            await self._send_update({"nodeId": node_id, "status": "error", "response": "已達到最大回滾次數限制。"})
            return

        self.rollback_counts[node_id] = self.rollback_counts.get(node_id, 0) + 1
        
        node = self.nodes[node_id]
        role = node.data.originalLabel
        original_output = self.node_outputs.get(node_id, "沒有找到原始輸出。")
        
        await self._send_update({
            "nodeId": node_id, 
            "status": "revising", 
            "message": f"收到回滾請求，正在第 {self.rollback_counts[node_id]}/{self.max_rollbacks} 次修正...",
            "can_rollback": False # 修訂期間暫時禁止再次回滾
        })

        # 找到觸發此節點的上一個節點的輸出作為輸入
        input_content = "無法確定此節點的原始輸入。"
        for source, targets in self.edge_map.items():
            if node_id in targets:
                # 找到上游節點
                input_content = self.node_outputs.get(source, input_content)
                break
        else: # 如果是入口節點
            input_content = self.payload.initialPrompt


        # 建立用於修正的 Prompt
        task_description = (
            f"你先前對以下內容的處理結果未獲批准。\n"
            f"--- 原始輸入 ---"
            f"{input_content}\n--- END ---\n"
            f"--- 你先前失敗的輸出 ---{original_output}\n--- END ---\n"
            f"--- 用戶提供的修改回饋 ---{user_feedback}\n--- END ---\n"
            f"請根據用戶的回饋，從你「{role}」的角度，徹底地重寫並改進你的輸出。不要只是評論，請直接產出修正後的完整內容。"
        )

        # 重新執行 Agent Turn
        history_for_revision = [msg for msg in self.master_history if msg.get("content") != original_output]
        await self._execute_agent_turn(node_id, task_description, history_for_revision)

        # 回滾後，需要重新觸發下游流程
        await self._send_update({"status": "info", "message": f"{role} 已修正，正在重新觸發下游流程..."})
        await self._process_node(node_id, "", history_for_revision) # 重新啟動從此節點開始的流程


# =================================================================
# === WebSocket 端點與主處理邏輯 (更新) ===========================
# =================================================================
# @router.websocket("/ws")
# async def workflow_websocket_endpoint(websocket: WebSocket, user_id: int = Depends(AuthService.get_current_user_from_token)):
@router.websocket("/ws")
async def workflow_websocket_endpoint(websocket: WebSocket):
    user_id = 1 # 繞過驗證，使用預設用戶
    await manager.connect(websocket, user_id)
    print(f"使用者 {user_id} 的 Workflow WebSocket 連線成功 (驗證已繞過)。")
    orchestrator: WorkflowOrchestrator = None

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            msg_type = message.get("type")
            payload_data = message.get("payload")

            if msg_type == "start_workflow":
                if not payload_data:
                    await websocket.send_json({"status": "error", "response": "Payload 不得為空"})
                    continue
                
                payload = WorkflowPayload(**payload_data)
                orchestrator = WorkflowOrchestrator(payload, websocket, user_id)
                asyncio.create_task(orchestrator.start())
            
            # ✅ NEW: 處理回滾請求
            elif msg_type == "request_rollback":
                if not orchestrator:
                    await websocket.send_json({"status": "error", "response": "工作流尚未啟動，無法回滾。"})
                    continue
                
                node_id = payload_data.get("nodeId")
                feedback = payload_data.get("feedback", "無具體回饋，請改進。")
                if not node_id:
                    await websocket.send_json({"status": "error", "response": "回滾請求中缺少 nodeId。"})
                    continue

                asyncio.create_task(orchestrator.handle_rollback(node_id, feedback))

    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)
        print(f"使用者 {user_id} 的 WebSocket 連線已斷開。")
    except Exception as e:
        print(f"WebSocket 發生錯誤: {e}")
        if websocket and websocket.client_state.value != 3:
             try:
                 await websocket.send_json({"status": "error", "response": f"伺服器內部錯誤: {e}"})
             except Exception as send_e:
                 print(f"傳送錯誤訊息時失敗: {send_e}")
        manager.disconnect(websocket, user_id)
