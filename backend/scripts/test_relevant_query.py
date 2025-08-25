#!/usr/bin/env python3
"""
測試更相關的查詢
"""
import asyncio
import sys
import os

# 添加項目路徑
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.rag.contextual_rag import HybridContextualRAG

async def test_relevant_query():
    """測試與現有文檔相關的查詢"""
    try:
        print("🔄 初始化 HybridContextualRAG...")
        rag = HybridContextualRAG()
        print("✅ 初始化成功")
        
        # 測試更相關的查詢
        query = "國家機密保護法的相關規定"
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
    success = asyncio.run(test_relevant_query())
    if success:
        print("\n🎉 相關查詢測試成功!")
    else:
        print("\n💥 相關查詢測試失敗!")
