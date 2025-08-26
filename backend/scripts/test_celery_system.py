#!/usr/bin/env python3
"""
測試 Celery 背景工作者系統
"""

import asyncio
import sys
import os
import time
import logging
from langchain.schema import Document

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.celery_app import celery_app
from app.tasks.rag_tasks import add_documents_task, force_reindex_task
from app.rag.contextual_rag import HybridContextualRAG

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_celery_connection():
    """測試 Celery 連接"""
    logger.info("=== 測試 Celery 連接 ===")
    
    try:
        # 檢查 Celery 狀態
        inspect = celery_app.control.inspect()
        active_workers = inspect.active()
        
        if active_workers:
            logger.info(f"✅ 發現 {len(active_workers)} 個活躍的 Celery 工作者")
            for worker_name, tasks in active_workers.items():
                logger.info(f"  工作者: {worker_name}, 活躍任務: {len(tasks)}")
        else:
            logger.warning("⚠️ 沒有發現活躍的 Celery 工作者")
            
        return active_workers is not None
        
    except Exception as e:
        logger.error(f"❌ Celery 連接失敗: {e}")
        return False

def test_task_submission():
    """測試任務提交"""
    logger.info("=== 測試任務提交 ===")
    
    try:
        # 創建測試文檔（轉換為可序列化的格式）
        test_docs = [
            {
                'page_content': '這是一個 Celery 測試文檔，用於驗證背景工作者功能。',
                'metadata': {'title': 'Celery 測試文檔', 'source': 'celery_test'}
            }
        ]
        
        # 提交添加文檔任務
        logger.info("提交 add_documents_task...")
        result = add_documents_task.delay(test_docs)
        logger.info(f"任務 ID: {result.id}")
        logger.info(f"任務狀態: {result.status}")
        
        # 等待任務完成（最多30秒）
        logger.info("等待任務完成...")
        start_time = time.time()
        timeout = 30
        
        while not result.ready() and (time.time() - start_time) < timeout:
            time.sleep(1)
            logger.info(f"任務狀態: {result.status}")
        
        if result.ready():
            if result.successful():
                logger.info("✅ 任務成功完成")
                logger.info(f"結果: {result.result}")
                return True
            else:
                logger.error(f"❌ 任務失敗: {result.result}")
                return False
        else:
            logger.warning("⚠️ 任務超時")
            return False
            
    except Exception as e:
        logger.error(f"❌ 任務提交失敗: {e}")
        return False

def test_direct_execution():
    """測試直接執行（作為對比）"""
    logger.info("=== 測試直接執行 ===")
    
    try:
        # 直接執行 RAG 操作
        rag = HybridContextualRAG()
        
        test_docs = [
            Document(
                page_content='這是一個直接執行測試文檔。',
                metadata={'title': '直接執行測試', 'source': 'direct_test'}
            )
        ]
        
        start_time = time.time()
        
        # 使用 asyncio 運行異步方法
        async def run_add_documents():
            await rag.add_documents(test_docs)
        
        asyncio.run(run_add_documents())
        
        execution_time = time.time() - start_time
        logger.info(f"✅ 直接執行完成，耗時: {execution_time:.2f}秒")
        logger.info(f"索引中向量數量: {rag.index.ntotal}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 直接執行失敗: {e}")
        return False

def test_fallback_mechanism():
    """測試回退機制"""
    logger.info("=== 測試回退機制 ===")
    
    try:
        from app.api.documents import _enqueue_task_safe
        from app.tasks.rag_tasks import add_documents_task
        
        test_docs = [
            {
                'page_content': '這是一個回退機制測試文檔。',
                'metadata': {'title': '回退測試', 'source': 'fallback_test'}
            }
        ]
        
        # 測試安全入隊函數
        result = _enqueue_task_safe(add_documents_task, test_docs)
        
        if result is not None:
            logger.info("✅ 回退機制測試成功（Celery 可用）")
        else:
            logger.info("✅ 回退機制測試成功（使用直接執行）")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 回退機制測試失敗: {e}")
        return False

def main():
    """主測試函數"""
    logger.info("🚀 開始 Celery 背景工作者測試")
    
    results = {}
    
    # 1. 測試 Celery 連接
    results['connection'] = test_celery_connection()
    
    # 2. 測試任務提交
    results['task_submission'] = test_task_submission()
    
    # 3. 測試直接執行
    results['direct_execution'] = test_direct_execution()
    
    # 4. 測試回退機制
    results['fallback'] = test_fallback_mechanism()
    
    # 總結報告
    logger.info("=" * 60)
    logger.info("📊 測試總結報告")
    logger.info("=" * 60)
    
    if results['connection']:
        logger.info("✅ Celery 連接正常")
    else:
        logger.info("❌ Celery 連接有問題")
    
    if results['task_submission']:
        logger.info("✅ 任務提交和執行正常")
    else:
        logger.info("❌ 任務提交和執行有問題")
    
    if results['direct_execution']:
        logger.info("✅ 直接執行正常")
    else:
        logger.info("❌ 直接執行有問題")
    
    if results['fallback']:
        logger.info("✅ 回退機制正常")
    else:
        logger.info("❌ 回退機制有問題")
    
    # 給出建議
    if not results['connection'] or not results['task_submission']:
        logger.info("\n💡 建議:")
        logger.info("1. 啟動 Celery 工作者:")
        logger.info("   celery -A app.celery_app worker --loglevel=info")
        logger.info("2. 檢查 Redis 連接:")
        logger.info("   redis-cli ping")
        logger.info("3. 系統會自動回退到直接執行模式")
    else:
        logger.info("\n🎉 所有系統正常運行！")

if __name__ == "__main__":
    main()
