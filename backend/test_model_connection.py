#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""測試指定模型的 API 連接"""
import requests
import json
import os

def test_model(model_name):
    """測試特定模型是否正常運作"""
    url = "https://blowfish-absolute-absolutely.ngrok-free.app/api/generate"
    
    payload = {
        "model": model_name,
        "prompt": "你好，請用繁體中文回答：你是誰？",
        "stream": False
    }
    
    headers = {"Content-Type": "application/json"}
    
    print(f"🔍 測試模型: {model_name}")
    print(f"📦 URL: {url}")
    print(f"\n正在發送請求...\n")
    
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=120)
        print(f"狀態碼: {resp.status_code}")
        
        if resp.status_code == 200:
            data = resp.json()
            response_text = data.get('response', '').strip()
            print(f"\n✅ 成功! 模型回應:\n{response_text}\n")
            return True
        else:
            print(f"\n❌ 錯誤: HTTP {resp.status_code}")
            print(f"回應: {resp.text}\n")
            return False
            
    except requests.exceptions.Timeout:
        print("❌ 請求超時（超過120秒）\n")
        return False
    except requests.exceptions.ConnectionError as e:
        print(f"❌ 連接錯誤: {e}\n")
        return False
    except Exception as e:
        print(f"❌ 未知錯誤: {e}\n")
        return False

if __name__ == "__main__":
    # Test the model from .env
    model = "gpt-oss:20b"
    
    print("="*60)
    print(f"  測試 Ollama 模型連接")
    print("="*60 + "\n")
    
    if test_model(model):
        print("✅ 模型測試通過！可以正常使用。")
    else:
        print("❌ 模型測試失敗！請檢查：")
        print("   1. Ollama 服務是否正在運行")
        print("   2. ngrok 隧道是否正常")
        print("   3. 模型名稱是否正確")
