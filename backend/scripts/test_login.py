"""
測試登入 API
"""
import sys
import os

# 添加父目錄到 Python 路徑
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
import json

def test_login(username, password):
    """測試登入"""
    url = "http://localhost:8001/api/auth/login"
    
    payload = {
        "username": username,
        "password": password
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    print(f"\n📝 測試登入 API")
    print(f"URL: {url}")
    print(f"Username: {username}")
    print(f"Password: {'*' * len(password)}")
    print("-" * 50)
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        
        print(f"\n✅ 狀態碼: {response.status_code}")
        print(f"響應頭: {dict(response.headers)}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n✅ 登入成功!")
            print(f"用戶: {data.get('user', {}).get('username')}")
            print(f"Access Token: {data.get('tokens', {}).get('access_token')[:50]}...")
            print(f"Refresh Token: {data.get('tokens', {}).get('refresh_token')[:50]}...")
            return True
        else:
            print(f"\n❌ 登入失敗!")
            try:
                error_data = response.json()
                print(f"錯誤詳情: {json.dumps(error_data, indent=2, ensure_ascii=False)}")
            except:
                print(f"響應文本: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print(f"\n❌ 無法連接到後端服務 (確保後端在 http://localhost:8001 運行)")
        return False
    except requests.exceptions.Timeout:
        print(f"\n❌ 請求超時")
        return False
    except Exception as e:
        print(f"\n❌ 錯誤: {e}")
        return False

if __name__ == "__main__":
    # 測試管理員帳號
    print("=" * 60)
    print("JWT 登入 API 測試")
    print("=" * 60)
    
    # 從命令行參數獲取憑證,或使用預設值
    if len(sys.argv) >= 3:
        username = sys.argv[1]
        password = sys.argv[2]
    else:
        username = input("請輸入用戶名 [yalkyao]: ").strip() or "yalkyao"
        password = input("請輸入密碼 [Mitac@2025]: ").strip() or "Mitac@2025"
    
    success = test_login(username, password)
    
    if success:
        print("\n✅ 測試通過!")
        sys.exit(0)
    else:
        print("\n❌ 測試失敗!")
        sys.exit(1)
