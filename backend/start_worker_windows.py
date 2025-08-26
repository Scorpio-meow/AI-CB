#!/usr/bin/env python
"""
Windows 相容的 Celery Worker 啟動腳本
避免 eventlet 在 Windows 上的相容性問題
"""
import os
import sys
import logging

# 確保專案根目錄在 Python 路徑中
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 設定日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def start_worker():
    """啟動 Celery Worker"""
    try:
        # 導入 Celery 應用程式
        from app.celery_app import celery_app
        
        logger.info("🔥 啟動 Celery Worker (Windows 模式)")
        logger.info(f"📁 專案路徑: {project_root}")
        
        # 使用 solo pool，最適合 Windows 環境
        celery_app.worker_main([
            'worker',
            '--loglevel=info',
            '--pool=solo',  # 使用 solo pool，避免多執行緒問題
            '--without-gossip',  # 減少網路開銷
            '--without-mingle',  # 減少啟動時間
            '--without-heartbeat',  # 簡化配置
        ])
        
    except KeyboardInterrupt:
        logger.info("🛑 Worker 被用戶中止")
    except Exception as e:
        logger.error(f"❌ Worker 啟動失敗: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    start_worker()
