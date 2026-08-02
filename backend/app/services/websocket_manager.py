import logging
from typing import List, Dict
from fastapi import WebSocket
logger = logging.getLogger(__name__)
class WorkflowWebSocketManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.user_connections: Dict[int, WebSocket] = {}
    async def connect(self, websocket: WebSocket, user_id: int):
        await websocket.accept()
        self.active_connections.append(websocket)
        self.user_connections[user_id] = websocket
        logger.info(f"User {user_id} connected to Workflow WebSocket")
    def disconnect(self, websocket: WebSocket, user_id: int):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        if user_id in self.user_connections:
            if self.user_connections[user_id] == websocket:
                del self.user_connections[user_id]
        logger.info(f"User {user_id} disconnected from Workflow WebSocket")
    async def send_json(self, data: dict, user_id: int):
        websocket = self.user_connections.get(user_id)
        if websocket:
            try:
                await websocket.send_json(data)
            except Exception as e:
                logger.error(f"Failed to send message to user {user_id}: {e}")
workflow_ws_manager = WorkflowWebSocketManager()
