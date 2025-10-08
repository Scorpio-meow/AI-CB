#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""列出可用的 LLM 模型"""
import requests
import json

def list_models():
    """列出 Ollama 服務中可用的模型"""
    # Ollama API endpoint for listing models
    url = "https://blowfish-absolute-absolutely.ngrok-free.app/api/tags"
    
    print(f"🔍 查詢 URL: {url}")
    print("\n正在獲取模型列表...\n")
    
    try:
        resp = requests.get(url, timeout=30)
        print(f"✅ 狀態碼: {resp.status_code}")
        
        if resp.status_code == 200:
            data = resp.json()
            models = data.get('models', [])
            
            if models:
                print(f"\n📋 找到 {len(models)} 個可用模型:\n")
                for i, model in enumerate(models, 1):
                    name = model.get('name', 'N/A')
                    size = model.get('size', 0) / (1024**3)  # Convert to GB
                    modified = model.get('modified_at', 'N/A')
                    print(f"{i}. {name}")
                    print(f"   大小: {size:.2f} GB")
                    print(f"   修改時間: {modified}\n")
            else:
                print("❌ 沒有找到任何模型")
        else:
            print(f"❌ 錯誤: HTTP {resp.status_code}")
            print(resp.text)
            
    except requests.exceptions.Timeout:
        print("❌ 請求超時")
    except requests.exceptions.ConnectionError as e:
        print(f"❌ 連接錯誤: {e}")
    except Exception as e:
        print(f"❌ 未知錯誤: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    list_models()
