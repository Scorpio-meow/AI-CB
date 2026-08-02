import json
import logging
from typing import List
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.models.database import get_db
from app.core.jwt_auth import get_current_active_user
from app.crud import crud_custom_agent
from app.services.websocket_manager import workflow_ws_manager
from app.services.workflow_service import (
    WorkflowProcess,
    DynamicWorkflowManager,
    OUTPUT_DIR,
    sanitize_filename
)
logger = logging.getLogger(__name__)
router = APIRouter()
@router.get("/professions", response_model=List[str], summary="獲取所有可用的專業角色")
def get_professions(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_active_user)
):
    unique_professions: set[str] = set()
    try:
        user_id = current_user.get("user_id")
        custom_agents = crud_custom_agent.get_custom_agents(db, user_id=user_id)
        for agent in custom_agents:
            unique_professions.add(agent.name)
            unique_professions.add(agent.role)
    except Exception as e:
        logger.error(f"從資料庫載入自訂 Agent 列表失敗: {e}")
    return sorted(list(unique_professions))
@router.websocket("/ws")
async def workflow_websocket_endpoint(websocket: WebSocket, db: Session = Depends(get_db)):
    user_id = 1
    await workflow_ws_manager.connect(websocket, user_id)
    
    try:
        while True:
            import asyncio
            data = await asyncio.wait_for(
                websocket.receive_text(),
                timeout=3600.0
            )
            
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
                
                if not payload_data:
                    await websocket.send_json({
                        "status": "error", 
                        "response": "Payload 不得為空"
                    })
                    continue
                
                try:
                    workflow_process = WorkflowProcess(**payload_data)
                except Exception as e:
                    await websocket.send_json({
                        "status": "error",
                        "response": f"Payload 格式錯誤: {str(e)}"
                    })
                    continue
                
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
                
    except WebSocketDisconnect:
        logger.info(f"使用者 {user_id} 的 WebSocket 正常斷線。")
        
    except Exception as e:
        logger.error(f"WebSocket 發生未預期錯誤 ({type(e).__name__}): {e}")
        if websocket.client_state.value != 3:
            try:
                await websocket.send_json({
                    "status": "error", 
                    "response": "伺服器內部錯誤: 請稍後重試"
                })
            except Exception as send_e:
                logger.warning("傳送錯誤訊息時失敗: %s", str(send_e))
                
    finally:
        workflow_ws_manager.disconnect(websocket, user_id)
@router.get("/download/{file_name}")
async def download_generated_file(file_name: str):
    safe_filename = sanitize_filename(file_name)
    target_path = (OUTPUT_DIR / safe_filename).resolve()
    
    try:
        if not target_path.is_relative_to(OUTPUT_DIR):
            raise HTTPException(status_code=400, detail="非法路徑")
            
        if not target_path.exists():
            raise HTTPException(status_code=404, detail="檔案不存在")
            
        if not target_path.is_file():
            raise HTTPException(status_code=400, detail="目標不是檔案")
        
        file_size = target_path.stat().st_size
        max_size = 50 * 1024 * 1024
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
        logger.exception("下載檔案時發生錯誤")
        raise HTTPException(status_code=500, detail="下載失敗: 內部錯誤，請聯繫系統管理員")