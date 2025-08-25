#!/usr/bin/env python3
"""
測試 Ollama API 連接
"""
import requests
import os
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()

OLLAMA_HOST = os.getenv("GITHUB_API_BASE", "https://fc5d1d0fc900.ngrok-free.app")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-oss:20b")

def check_model(model_name=None):
    """檢查指定模型是否存在"""
    model_name = model_name or MODEL_NAME
    try:
        url = f"{OLLAMA_HOST}/api/tags"
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        data = response.json()
        models = [m["name"] for m in data.get("models", [])]

        return model_name in models, models

    except requests.exceptions.RequestException as e:
        print("⚠️ 無法連線到 Ollama API:", e)
        return False, []


def ask_model(prompt, model_name=None):
    """向指定模型發送 POST 請求"""
    model_name = model_name or MODEL_NAME
    url = f"{OLLAMA_HOST}/api/generate"
    payload = {
        "model": model_name,
        "prompt": prompt,
        "stream": False   # 設定 True 會分段回傳，這裡先用 False 一次拿到完整結果
    }

    try:
        response = requests.post(url, json=payload, timeout=60)
        response.raise_for_status()

        data = response.json()
        return data.get("response", "").strip()

    except requests.exceptions.RequestException as e:
        return f"⚠️ 請求失敗: {e}"


if __name__ == "__main__":
    print(f"🔗 測試 Ollama API: {OLLAMA_HOST}")
    print(f"🤖 使用模型: {MODEL_NAME}")
    
    # 1. 檢查模型
    print("\n1. 檢查模型存在...")
    exists, models = check_model()
    if exists:
        print(f"✅ 模型存在: {MODEL_NAME}")
    else:
        print(f"❌ 找不到模型: {MODEL_NAME}")
        print("目前已安裝的模型清單:", models)
        print("將嘗試發送請求...")

    # 2. 發送測試問題
    question = "你好，請簡短回答：什麼是人工智能？"
    print(f"\n2. 📝 提問: {question}")
    answer = ask_model(question)
    print(f"\n🤖 回覆: {answer}")
    
    # 3. 測試RAG相關問題
    rag_question = "請用繁體中文回答問題，並說明你可以如何幫助用戶。"
    print(f"\n3. 📝 RAG測試: {rag_question}")
    rag_answer = ask_model(rag_question)
    print(f"\n🤖 RAG回覆: {rag_answer}")
