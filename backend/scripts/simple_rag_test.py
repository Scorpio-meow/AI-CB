#!/usr/bin/env python3
"""
簡化的 RAG 測試腳本
"""

import sys
import os
import asyncio
import logging

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.rag.contextual_rag import HybridContextualRAG
from langchain.schema import Document

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_basic_functionality():
    """測試基本功能"""
    logger.info("初始化 HybridContextualRAG...")
    
    try:
        rag = HybridContextualRAG()
        logger.info("初始化成功")
        
        # 檢查屬性
        logger.info(f"embedding_dimension: {rag.embedding_dimension}")
        logger.info(f"has text_splitter: {hasattr(rag, 'text_splitter')}")
        logger.info(f"has_reranker: {rag.has_reranker}")
        
        # 創建測試文檔
        test_doc = Document(
            page_content="這是一個測試文檔，用於驗證 RAG 系統的基本功能。包含人工智能、機器學習等相關內容。",
            metadata={"source": "test_doc.txt", "document_id": 1}
        )
        
        logger.info("添加測試文檔...")
        await rag.add_documents([test_doc])
        
        # 測試搜尋
        logger.info("測試向量搜尋...")
        vector_results = rag.vector_search("人工智能", 3)
        logger.info(f"向量搜尋結果數: {len(vector_results)}")
        
        logger.info("測試 BM25 搜尋...")
        bm25_results = rag.bm25_search("人工智能", 3)
        logger.info(f"BM25 搜尋結果數: {len(bm25_results)}")
        
        logger.info("測試混合搜尋...")
        hybrid_results = rag.hybrid_search("人工智能")
        logger.info(f"混合搜尋結果數: {len(hybrid_results)}")
        
        logger.info("測試智能搜尋...")
        smart_results = rag.smart_search("人工智能")
        logger.info(f"智能搜尋結果數: {len(smart_results)}")
        
        # 獲取統計信息
        stats = rag.get_statistics()
        logger.info(f"系統統計: {stats}")
        
        logger.info("所有測試完成！")
        
    except Exception as e:
        logger.error(f"測試失敗: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_basic_functionality())
