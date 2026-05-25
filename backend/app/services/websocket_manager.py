import logging
from typing import List, Dict
from fastapi import WebSocket

logger = logging.getLogger(__name__)

class WorkflowWebSocketManager:
    """獨立管理工作流 WebSocket 連線的管理器"""
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.user_connections: Dict[int, WebSocket] = {}

    async def connect(self, websocket: WebSocket, user_id: int):
        """接受連線並將其加入管理清單"""
        await websocket.accept()
        self.active_connections.append(websocket)
        self.user_connections[user_id] = websocket
        logger.info(f"User {user_id} connected to Workflow WebSocket")

    def disconnect(self, websocket: WebSocket, user_id: int):
        """當斷開連線時清除連線資訊"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        if user_id in self.user_connections:
            # 只有當該 user_id 當前對應的 WebSocket 是這個連線時才刪除
            # 避免多重登入衝突
            if self.user_connections[user_id] == websocket:
                del self.user_connections[user_id]
        logger.info(f"User {user_id} disconnected from Workflow WebSocket")

    async def send_json(self, data: dict, user_id: int):
        """發送 JSON 訊息給特定使用者的連線"""
        websocket = self.user_connections.get(user_id)
        if websocket:
            try:
                await websocket.send_json(data)
            except Exception as e:
                logger.error(f"Failed to send message to user {user_id}: {e}")

# 全局單例 WebSocket 管理器
workflow_ws_manager = WorkflowWebSocketManager()
