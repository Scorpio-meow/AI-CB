#!/usr/bin/env python3
"""
啟動 Celery 工作者
"""

import subprocess
import sys
import os
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def start_celery_worker():
    """啟動 Celery 工作者"""
    logger.info("🚀 啟動 Celery 工作者...")
    
    try:
        # 設置環境變數
        env = os.environ.copy()
        env['PYTHONPATH'] = os.path.dirname(os.path.abspath(__file__)) + "/.."
        
        # 構建命令（使用 eventlet 在 Windows 上）
        python_exe = sys.executable
        cmd = [
            python_exe, "-m", "celery", 
            "-A", "app.celery_app", 
            "worker", 
            "--loglevel=info",
            "--pool=eventlet",
            "--concurrency=4"
        ]
        
        logger.info(f"執行命令: {' '.join(cmd)}")
        logger.info("⚠️ 按 Ctrl+C 停止工作者")
        
        # 運行 Celery 工作者
        subprocess.run(cmd, env=env, cwd=os.path.dirname(os.path.abspath(__file__)) + "/..")
        
    except KeyboardInterrupt:
        logger.info("🛑 收到停止信號，關閉工作者...")
    except Exception as e:
        logger.error(f"❌ 啟動 Celery 工作者失敗: {e}")

if __name__ == "__main__":
    start_celery_worker()
