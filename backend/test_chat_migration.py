"""
測試 /api/chat 遷移後的功能

運行方式:
1. 確保後端服務已啟動 (port 8001)
2. 運行: python test_chat_migration.py
"""

import asyncio
import httpx
import json

# 配置
BACKEND_URL = "http://localhost:8001"
TEST_USER_ID = 1

async def test_rag_single_turn():
    """測試 RAG 單輪對話"""
    print("\n" + "="*60)
    print("測試 1: RAG 單輪對話")
    print("="*60)
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BACKEND_URL}/api/chat",
            json={
                "message": "什麼是特休?",
                "user_id": TEST_USER_ID
            },
            timeout=30.0
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 成功! 回答長度: {len(data.get('response', ''))}")
            print(f"   檢索策略: {data.get('retrieval_strategy', 'N/A')}")
            print(f"   使用來源: {len(data.get('sources', []))}")
        else:
            print(f"❌ 失敗! 狀態碼: {response.status_code}")
            print(f"   錯誤: {response.text}")

async def test_rag_multi_turn():
    """測試 RAG 多輪對話"""
    print("\n" + "="*60)
    print("測試 2: RAG 多輪對話")
    print("="*60)
    
    async with httpx.AsyncClient() as client:
        # 第一輪
        response1 = await client.post(
            f"{BACKEND_URL}/api/chat",
            json={
                "message": "什麼是補休?",
                "user_id": TEST_USER_ID
            },
            timeout=30.0
        )
        
        if response1.status_code == 200:
            data1 = response1.json()
            conversation_id = data1.get('conversation_id')
            print(f"✅ 第一輪成功! 對話ID: {conversation_id}")
            
            # 第二輪 (使用相同 conversation_id)
            await asyncio.sleep(1)
            response2 = await client.post(
                f"{BACKEND_URL}/api/chat",
                json={
                    "message": "那到期了怎麼辦?",
                    "user_id": TEST_USER_ID,
                    "conversation_id": conversation_id
                },
                timeout=30.0
            )
            
            if response2.status_code == 200:
                data2 = response2.json()
                print(f"✅ 第二輪成功! 回答長度: {len(data2.get('response', ''))}")
                print(f"   是否理解上下文: {'是' if '補休' in data2.get('response', '') else '未知'}")
            else:
                print(f"❌ 第二輪失敗! 狀態碼: {response2.status_code}")
        else:
            print(f"❌ 第一輪失敗! 狀態碼: {response1.status_code}")

async def test_workflow_execution():
    """測試工作流執行 (需要 WebSocket)"""
    print("\n" + "="*60)
    print("測試 3: 工作流系統")
    print("="*60)
    print("ℹ️  工作流測試需要 WebSocket 連接,請手動在前端測試")
    print("   前端地址: http://localhost:3000")

async def test_llm_api_direct():
    """直接測試 LLM API 端點"""
    print("\n" + "="*60)
    print("測試 4: LLM API 直接調用")
    print("="*60)
    
    # 從環境變數讀取 (或使用預設值)
    import os
    llm_api_base = os.getenv("LLM_API_BASE", "https://blowfish-absolute-absolutely.ngrok-free.app")
    model_name = os.getenv("MODEL_NAME", "gpt-oss:20b")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{llm_api_base}/api/chat",
                json={
                    "model": model_name,
                    "messages": [
                        {"role": "system", "content": "你是一個測試助理。"},
                        {"role": "user", "content": "請簡短回答:今天天氣如何?"}
                    ],
                    "stream": False
                },
                headers={"ngrok-skip-browser-warning": "true"},
                timeout=30.0
            )
            
            if response.status_code == 200:
                data = response.json()
                content = data.get("message", {}).get("content", "")
                print(f"✅ LLM API 正常! 回答: {content[:100]}...")
            else:
                print(f"❌ LLM API 異常! 狀態碼: {response.status_code}")
        except Exception as e:
            print(f"❌ 連接失敗: {e}")

async def main():
    """運行所有測試"""
    print("\n" + "🚀 開始測試 /api/chat 遷移後的功能...")
    
    try:
        await test_llm_api_direct()
        await asyncio.sleep(2)
        
        await test_rag_single_turn()
        await asyncio.sleep(2)
        
        await test_rag_multi_turn()
        await asyncio.sleep(2)
        
        await test_workflow_execution()
        
    except Exception as e:
        print(f"\n❌ 測試過程出錯: {e}")
    
    print("\n" + "="*60)
    print("測試完成!")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(main())
