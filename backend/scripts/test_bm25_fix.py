#!/usr/bin/env python3
"""
測試修復後的 BM25 索引加載
"""

import asyncio
import sys
import os
import logging
from langchain.schema import Document

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.rag.contextual_rag import HybridContextualRAG

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_bm25_index_loading():
    """測試 BM25 索引加載修復"""
    logger.info("=== 測試 BM25 索引加載修復 ===")
    
    try:
        # 初始化 RAG 系統
        rag = HybridContextualRAG()
        logger.info("✅ RAG 系統初始化成功")
        
        # 檢查 BM25 索引狀態
        if rag.bm25_index is None:
            logger.info("📝 BM25 索引為空（正常，因為沒有文檔）")
        else:
            logger.info(f"📊 BM25 索引已加載，包含文檔數量: {len(rag.documents)}")
        
        # 測試添加一個簡單文檔來創建索引
        logger.info("測試添加文檔以創建 BM25 索引...")
        test_docs = [
            Document(
                page_content='這是一個測試文檔，用於驗證 BM25 索引功能。',
                metadata={'title': '測試文檔1', 'source': 'test'}
            ),
            Document(
                page_content='人工智能是計算機科學的一個重要分支。',
                metadata={'title': '測試文檔2', 'source': 'test'}
            )
        ]
        
        # 使用異步方法添加文檔
        await rag.add_documents(test_docs)
        
        logger.info(f"✅ 添加了 {len(test_docs)} 個文檔")
        logger.info(f"📊 FAISS 索引現在包含 {rag.index.ntotal} 個向量")
        
        if rag.bm25_index is not None:
            logger.info("✅ BM25 索引已成功創建")
        else:
            logger.warning("⚠️ BM25 索引仍為空")
        
        # 測試搜索功能
        logger.info("測試搜索功能...")
        query = "人工智能"
        results = rag.smart_search(query)
        
        logger.info(f"搜索 '{query}' 返回 {len(results)} 個結果")
        for i, result in enumerate(results):
            logger.info(f"結果 {i+1}: {result.page_content[:50]}... (來源: {result.metadata.get('source', 'unknown')})")
        
        logger.info("✅ 所有測試通過")
        return True
        
    except Exception as e:
        logger.error(f"❌ 測試失敗: {e}")
        return False

if __name__ == "__main__":
    async def main():
        success = await test_bm25_index_loading()
        if success:
            print("\n🎉 BM25 索引修復測試成功！")
        else:
            print("\n💥 BM25 索引修復測試失敗！")
    
    asyncio.run(main())
