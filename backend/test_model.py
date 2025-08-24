#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from sentence_transformers import SentenceTransformer

def test_model():
    try:
        print("正在載入 paraphrase-multilingual-MiniLM-L12-v2 模型...")
        model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
        
        print(f"模型維度: {model.get_sentence_embedding_dimension()}")
        
        # 測試繁體中文編碼
        test_texts = [
            "這是一個測試文件",
            "ChatBot 系統功能",
            "知識庫管理"
        ]
        
        embeddings = model.encode(test_texts)
        print(f"測試文本數量: {len(test_texts)}")
        print(f"向量形狀: {embeddings.shape}")
        print("繁體中文測試成功！")
        
    except Exception as e:
        print(f"錯誤: {e}")

if __name__ == "__main__":
    test_model()
