#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""測試 LLM API 連接"""
import requests
import json

def test_llm_api():
    """測試 LLM API 是否正常運作"""
    url = "https://blowfish-absolute-absolutely.ngrok-free.app/api/generate"
    
    payload = {
        "model": "gpt-4o-mini",
        "prompt": "Hello, please respond with 'Hi'",
        "stream": False
    }
    
    headers = {"Content-Type": "application/json"}
    
    print(f"🔍 測試 URL: {url}")
    print(f"📦 Payload: {json.dumps(payload, indent=2)}")
    print("\n正在發送請求...\n")
    
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=30)
        print(f"✅ 狀態碼: {resp.status_code}")
        print(f"📄 回應標頭: {dict(resp.headers)}")
        print(f"\n回應內容:")
        print(resp.text)
        
        if resp.status_code == 200:
            data = resp.json()
            print(f"\n✅ 成功! 模型回應: {data.get('response', 'N/A')}")
        else:
            print(f"\n❌ 錯誤: HTTP {resp.status_code}")
            
    except requests.exceptions.Timeout:
        print("❌ 請求超時")
    except requests.exceptions.ConnectionError as e:
        print(f"❌ 連接錯誤: {e}")
    except Exception as e:
        print(f"❌ 未知錯誤: {e}")

if __name__ == "__main__":
    test_llm_api()
