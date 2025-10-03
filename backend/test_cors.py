#!/usr/bin/env python3
"""
測試 CORS 配置
"""
import requests
import json

# 測試配置
BACKEND_URL = "https://1848b1fg-8001.asse.devtunnels.ms"
FRONTEND_ORIGIN = "https://1848b1fg-3000.asse.devtunnels.ms"

def test_preflight():
    """測試 OPTIONS preflight 請求"""
    print("🧪 測試 CORS Preflight 請求...")
    print(f"Backend URL: {BACKEND_URL}")
    print(f"Origin: {FRONTEND_ORIGIN}")
    print()
    
    headers = {
        'Origin': FRONTEND_ORIGIN,
        'Access-Control-Request-Method': 'POST',
        'Access-Control-Request-Headers': 'content-type,authorization',
    }
    
    try:
        response = requests.options(
            f"{BACKEND_URL}/api/chat/conversations",
            headers=headers,
            timeout=10
        )
        
        print(f"✅ Status Code: {response.status_code}")
        print(f"\n📋 Response Headers:")
        for key, value in response.headers.items():
            if 'access-control' in key.lower() or 'origin' in key.lower():
                print(f"  {key}: {value}")
        
        # 檢查關鍵 CORS headers
        allow_origin = response.headers.get('Access-Control-Allow-Origin')
        allow_methods = response.headers.get('Access-Control-Allow-Methods')
        allow_headers = response.headers.get('Access-Control-Allow-Headers')
        
        print(f"\n🔍 CORS 檢查:")
        print(f"  ✓ Allow-Origin: {allow_origin}")
        print(f"  ✓ Allow-Methods: {allow_methods}")
        print(f"  ✓ Allow-Headers: {allow_headers}")
        
        if allow_origin == FRONTEND_ORIGIN or allow_origin == '*':
            print(f"\n✅ CORS 配置正確！")
        else:
            print(f"\n❌ CORS 配置錯誤！Expected: {FRONTEND_ORIGIN}, Got: {allow_origin}")
            
    except requests.exceptions.Timeout:
        print("❌ 請求超時 (可能是 DevTunnels 問題)")
    except requests.exceptions.ConnectionError as e:
        print(f"❌ 連接錯誤: {e}")
    except Exception as e:
        print(f"❌ 錯誤: {e}")

def test_actual_request():
    """測試實際的 POST 請求"""
    print("\n\n🧪 測試實際 POST 請求...")
    
    headers = {
        'Origin': FRONTEND_ORIGIN,
        'Content-Type': 'application/json',
    }
    
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/chat/conversations",
            headers=headers,
            json={"title": "Test"},
            timeout=10
        )
        
        print(f"✅ Status Code: {response.status_code}")
        print(f"Response: {response.text[:200]}")
        
    except requests.exceptions.Timeout:
        print("❌ 請求超時")
    except Exception as e:
        print(f"❌ 錯誤: {e}")

if __name__ == "__main__":
    test_preflight()
    test_actual_request()
