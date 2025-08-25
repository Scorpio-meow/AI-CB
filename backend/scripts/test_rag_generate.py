#!/usr/bin/env python3
"""
直接測試 HybridContextualRAG 的 generate_response 方法
"""
import asyncio
import sys
import os

# 添加項目路徑
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.rag.contextual_rag import HybridContextualRAG

async def test_rag_generate_response():
    """測試 RAG 系統的完整 generate_response 流程"""
    try:
        print("🔄 初始化 HybridContextualRAG...")
        rag = HybridContextualRAG()
        print("✅ 初始化成功")
        
        # 測試查詢
        query = "你好，請介紹一下你的功能"
        print(f"\n📝 測試查詢: {query}")
        
        # 調用 generate_response
        print("🔄 調用 generate_response...")
        response = await rag.generate_response(query, conversation_id=1)
        
        print("✅ 回應生成成功")
        print(f"📊 回應統計:")
        print(f"  - 使用文檔數: {response.get('context_used', 0)}")
        print(f"  - 檢索時間: {response.get('retrieval_time', 0):.3f}s")
        print(f"  - 生成時間: {response.get('generation_time', 0):.3f}s")
        print(f"  - 總時間: {response.get('total_time', 0):.3f}s")
        print(f"  - 來源: {response.get('sources', [])}")
        
        print(f"\n🤖 AI 回應:")
        print(response.get('answer', '無回應'))
        
        return True
        
    except Exception as e:
        print(f"❌ 測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_rag_generate_response())
    if success:
        print("\n🎉 RAG 系統測試成功!")
    else:
        print("\n💥 RAG 系統測試失敗!")
