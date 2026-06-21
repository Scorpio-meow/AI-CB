import json
import logging
from typing import List, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.core.jwt_auth import get_current_active_user, TokenManager
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
        logger.error(f"從資料庫載入自訂 Agent 列表失敗: {e}")

    return sorted(list(unique_professions))

@router.websocket("/ws")
async def workflow_websocket_endpoint(
    websocket: WebSocket,
    token: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """工作流 WebSocket 端點 - 接受連線並將訊息分派給工作流管理器"""
    await websocket.accept()
    
    if not token:
        logger.warning("WebSocket 認證失敗: 缺少 token")
        await websocket.send_json({
            "status": "error",
            "response": "認證失敗: 缺少 token"
        })
        await websocket.close(code=3000)
        return
        
    try:
        payload = TokenManager.decode_token(token)
        if not TokenManager.verify_token_type(payload, "access"):
            logger.warning("WebSocket 認證失敗: 無效的 token 類型")
            await websocket.send_json({
                "status": "error",
                "response": "認證失敗: 無效的 token 類型"
            })
            await websocket.close(code=3000)
            return
            
        user_id_str = payload.get("sub")
        if not user_id_str:
            logger.warning("WebSocket 認證失敗: token 中無 sub 資訊")
            await websocket.send_json({
                "status": "error",
                "response": "認證失敗: token 中缺少用戶資訊"
            })
            await websocket.close(code=3000)
            return
            
        user_id = int(user_id_str)
    except Exception as e:
        logger.error(f"WebSocket 認證驗證失敗: {e}")
        await websocket.send_json({
            "status": "error",
            "response": f"認證失敗: {str(e)}"
        })
        await websocket.close(code=3000)
        return

    # 將經認證的連線註冊至管理器中
    workflow_ws_manager.active_connections.append(websocket)
    workflow_ws_manager.user_connections[user_id] = websocket
    logger.info(f"User {user_id} connected to Workflow WebSocket (authenticated)")
    
    try:
        while True:
            # 設置接收超時,避免無限等待
            import asyncio
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
                
    except WebSocketDisconnect:
        logger.info(f"使用者 {user_id} 的 WebSocket 正常斷線。")
        
    except Exception as e:
        logger.error(f"WebSocket 發生未預期錯誤 ({type(e).__name__}): {e}")
        # 嘗試發送錯誤訊息
        if websocket.client_state.value != 3:  # 3 = CLOSED
            try:
                await websocket.send_json({
                    "status": "error", 
                    "response": "伺服器內部錯誤: 請稍後重試"
                })
            except Exception as send_e:
                logger.warning("傳送錯誤訊息時失敗: %s", str(send_e))
                
    finally:
        # 確保清理資源
        workflow_ws_manager.disconnect(websocket, user_id)

@router.get("/download/{file_name}")
async def download_generated_file(file_name: str):
    """下載工作流生成的檔案 - 包含路徑防護"""
    safe_filename = sanitize_filename(file_name)
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
        logger.exception("下載檔案時發生錯誤")
        raise HTTPException(status_code=500, detail="下載失敗: 內部錯誤，請聯繫系統管理員")