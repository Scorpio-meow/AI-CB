from celery import Celery
import os

# broker and backend from environment or defaults
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/1')

celery_app = Celery('ai_cb', broker=CELERY_BROKER_URL, backend=CELERY_RESULT_BACKEND)
celery_app.conf.update(task_track_started=True, task_time_limit=3600)

# 手動導入任務模組以確保任務被註冊
try:
    from app.tasks import rag_tasks  # 明確導入任務模組
    print("✅ RAG 任務模組已成功導入")
except ImportError as e:
    print(f"❌ 導入任務模組失敗: {e}")

# autodiscover tasks in app.tasks
celery_app.autodiscover_tasks(['app.tasks'])
