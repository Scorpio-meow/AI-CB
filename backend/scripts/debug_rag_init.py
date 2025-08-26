#!/usr/bin/env python3
"""
調試 RAG 初始化
"""

import sys
import os
import logging

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_imports():
    """測試導入"""
    try:
        logger.info("測試基本導入...")
        from sentence_transformers import SentenceTransformer, CrossEncoder
        logger.info("✓ sentence_transformers")
        
        from whoosh import index, fields, qparser, scoring
        logger.info("✓ whoosh")
        
        import faiss
        logger.info("✓ faiss")
        
        from langchain.text_splitter import RecursiveCharacterTextSplitter
        logger.info("✓ langchain")
        
        logger.info("所有導入成功")
        return True
    except Exception as e:
        logger.error(f"導入失敗: {e}")
        return False

def test_step_by_step_init():
    """分步測試初始化"""
    try:
        logger.info("開始分步初始化...")
        
        # Step 1: Basic imports
        import requests
        from sentence_transformers import SentenceTransformer, CrossEncoder
        import faiss
        from langchain.text_splitter import RecursiveCharacterTextSplitter
        logger.info("✓ 導入完成")
        
        # Step 2: Load embedding model
        logger.info("載入嵌入模型...")
        local_embeddings = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
        embedding_dimension = local_embeddings.get_sentence_embedding_dimension()
        logger.info(f"✓ 嵌入模型載入完成，維度: {embedding_dimension}")
        
        # Step 3: Try cross-encoder
        logger.info("嘗試載入 cross-encoder...")
        try:
            cross_encoder = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
            has_reranker = True
            logger.info("✓ Cross-encoder 載入成功")
        except Exception as e:
            logger.warning(f"Cross-encoder 載入失敗: {e}")
            cross_encoder = None
            has_reranker = False
        
        # Step 4: Text splitter
        logger.info("初始化文字分割器...")
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=600,
            chunk_overlap=150,
            length_function=len,
        )
        logger.info("✓ 文字分割器初始化完成")
        
        # Step 5: FAISS index
        logger.info("初始化 FAISS 索引...")
        index = faiss.IndexFlatIP(embedding_dimension)
        logger.info(f"✓ FAISS 索引初始化完成，維度: {embedding_dimension}")
        
        logger.info("分步初始化全部成功！")
        return True
        
    except Exception as e:
        logger.error(f"分步初始化失敗: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_manual_class_creation():
    """手動創建類實例"""
    try:
        logger.info("手動創建類...")
        
        class TestRAG:
            def __init__(self):
                logger.info("創建 TestRAG 實例...")
                self.has_reranker = False
                self.text_splitter = None
                logger.info("TestRAG 初始化完成")
        
        test_rag = TestRAG()
        logger.info(f"has_reranker: {test_rag.has_reranker}")
        logger.info("手動創建成功！")
        return True
        
    except Exception as e:
        logger.error(f"手動創建失敗: {e}")
        return False

if __name__ == "__main__":
    logger.info("=== RAG 初始化調試 ===")
    
    # Test 1: Imports
    if not test_imports():
        logger.error("導入測試失敗，停止")
        sys.exit(1)
    
    # Test 2: Step by step
    if not test_step_by_step_init():
        logger.error("分步初始化失敗，停止")
        sys.exit(1)
    
    # Test 3: Manual class
    if not test_manual_class_creation():
        logger.error("手動創建失敗，停止")
        sys.exit(1)
    
    logger.info("所有調試測試通過！")
