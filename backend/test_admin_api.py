"""
測試管理員 API 端點
"""
import requests
import sys
import os
from dotenv import load_dotenv

load_dotenv()

# 配置
API_BASE = os.getenv("LLM_API_BASE", "http://localhost:8001")
if "devtunnels" in API_BASE:
    # 使用 DevTunnels URL
    BACKEND_URL = "https://1848b1fg-8001.asse.devtunnels.ms"
else:
    BACKEND_URL = "http://localhost:8001"

def test_admin_endpoints():
    """測試管理員端點的認證和 CORS"""
    print(f"🧪 測試後端 API: {BACKEND_URL}")
    print("="*60)
    
    # 1. 測試健康檢查
    print("\n1️⃣ 測試健康檢查端點...")
    try:
        response = requests.get(f"{BACKEND_URL}/api/health")
        print(f"✅ 健康檢查: {response.status_code}")
        if response.status_code == 200:
            print(f"   響應: {response.json()}")
    except Exception as e:
        print(f"❌ 健康檢查失敗: {e}")
    
    # 2. 測試登入 (創建 token)
    print("\n2️⃣ 測試登入端點...")
    login_data = {
        "username": "admin",
        "password": "Admin123!"  # 根據您的實際管理員密碼調整
    }
    
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/auth/login",
            json=login_data,
            headers={
                "Content-Type": "application/json",
                "Origin": "https://1848b1fg-3000.asse.devtunnels.ms"
            }
        )
        print(f"   狀態碼: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            access_token = data.get("access_token")
            print(f"✅ 登入成功!")
            print(f"   Token: {access_token[:50]}...")
            
            # 3. 測試管理員端點
            print("\n3️⃣ 測試管理員統計端點...")
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Origin": "https://1848b1fg-3000.asse.devtunnels.ms"
            }
            
            response = requests.get(
                f"{BACKEND_URL}/api/admin/statistics",
                headers=headers
            )
            print(f"   狀態碼: {response.status_code}")
            
            if response.status_code == 200:
                print(f"✅ 管理員統計: {response.json()}")
            else:
                print(f"❌ 管理員統計失敗: {response.text}")
            
            # 4. 測試用戶列表端點
            print("\n4️⃣ 測試用戶列表端點...")
            response = requests.get(
                f"{BACKEND_URL}/api/admin/users",
                headers=headers
            )
            print(f"   狀態碼: {response.status_code}")
            
            if response.status_code == 200:
                users = response.json()
                print(f"✅ 用戶列表 ({len(users)} 個用戶)")
                for user in users[:3]:  # 只顯示前3個
                    print(f"   - {user.get('username')} ({user.get('email')})")
            else:
                print(f"❌ 用戶列表失敗: {response.text}")
                
        else:
            print(f"❌ 登入失敗: {response.text}")
            
    except Exception as e:
        print(f"❌ 請求失敗: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_admin_endpoints()
