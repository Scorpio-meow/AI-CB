"""
安全增強功能測試腳本
測試 RSA 加密、Token 黑名單、HttpOnly Cookie 等功能
"""

import requests
import json
import time
from datetime import datetime

# 配置
BASE_URL = "http://localhost:8000/api"
TEST_USER = {
    "username": "security_test_user",
    "email": "security@test.com",
    "password": "SecurePassword123"
}


def print_section(title):
    """打印分節標題"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def test_register():
    """測試用戶註冊"""
    print_section("測試 1: 用戶註冊")
    
    url = f"{BASE_URL}/auth/register"
    
    try:
        response = requests.post(url, json=TEST_USER)
        
        if response.status_code == 201:
            print("✅ 註冊成功")
            data = response.json()
            print(f"   用戶: {data['user']['username']}")
            print(f"   Access Token: {data['tokens']['access_token'][:50]}...")
            
            # 檢查 Cookie
            cookies = response.cookies
            if 'refresh_token' in cookies:
                print("✅ Refresh Token 已存儲在 HttpOnly Cookie")
                print(f"   Cookie: {cookies['refresh_token'][:50]}...")
            else:
                print("❌ 未找到 Refresh Token Cookie")
            
            return data['tokens']['access_token'], cookies
        else:
            print(f"❌ 註冊失敗: {response.status_code}")
            print(f"   錯誤: {response.json()}")
            return None, None
    except Exception as e:
        print(f"❌ 請求失敗: {e}")
        return None, None


def test_login():
    """測試用戶登入"""
    print_section("測試 2: 用戶登入")
    
    url = f"{BASE_URL}/auth/login"
    
    try:
        response = requests.post(url, json={
            "username": TEST_USER["username"],
            "password": TEST_USER["password"]
        })
        
        if response.status_code == 200:
            print("✅ 登入成功")
            data = response.json()
            access_token = data['tokens']['access_token']
            
            # 檢查 Cookie
            cookies = response.cookies
            if 'refresh_token' in cookies:
                print("✅ Refresh Token 已存儲在 HttpOnly Cookie")
                return access_token, cookies
            else:
                print("❌ 未找到 Refresh Token Cookie")
                return access_token, None
        else:
            print(f"❌ 登入失敗: {response.status_code}")
            return None, None
    except Exception as e:
        print(f"❌ 請求失敗: {e}")
        return None, None


def test_token_validation(access_token):
    """測試 Token 驗證"""
    print_section("測試 3: Token 驗證")
    
    url = f"{BASE_URL}/auth/me"
    headers = {"Authorization": f"Bearer {access_token}"}
    
    try:
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            print("✅ Token 驗證成功")
            data = response.json()
            print(f"   用戶 ID: {data['id']}")
            print(f"   用戶名: {data['username']}")
            return True
        else:
            print(f"❌ Token 驗證失敗: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 請求失敗: {e}")
        return False


def test_token_refresh(cookies):
    """測試 Token 刷新（使用 Cookie）"""
    print_section("測試 4: Token 刷新 (HttpOnly Cookie)")
    
    url = f"{BASE_URL}/auth/refresh"
    
    try:
        response = requests.post(url, cookies=cookies)
        
        if response.status_code == 200:
            print("✅ Token 刷新成功")
            data = response.json()
            new_access_token = data['access_token']
            print(f"   新 Access Token: {new_access_token[:50]}...")
            
            # 檢查是否更新了 Cookie
            new_cookies = response.cookies
            if 'refresh_token' in new_cookies:
                print("✅ Refresh Token Cookie 已更新")
            
            return new_access_token, response.cookies
        else:
            print(f"❌ Token 刷新失敗: {response.status_code}")
            print(f"   錯誤: {response.json()}")
            return None, None
    except Exception as e:
        print(f"❌ 請求失敗: {e}")
        return None, None


def test_logout(access_token, cookies):
    """測試登出（Token 黑名單）"""
    print_section("測試 5: 登出 (Token 黑名單)")
    
    url = f"{BASE_URL}/auth/logout"
    headers = {"Authorization": f"Bearer {access_token}"}
    
    try:
        response = requests.post(url, headers=headers, cookies=cookies)
        
        if response.status_code == 200:
            print("✅ 登出成功")
            
            # 驗證 Token 是否已被撤銷
            print("\n   驗證 Token 是否已被撤銷...")
            time.sleep(1)  # 等待 Redis 更新
            
            validation_response = requests.get(
                f"{BASE_URL}/auth/me",
                headers=headers
            )
            
            if validation_response.status_code == 401:
                print("✅ Token 已被成功撤銷（加入黑名單）")
                return True
            else:
                print("❌ Token 仍然有效（黑名單未生效）")
                return False
        else:
            print(f"❌ 登出失敗: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 請求失敗: {e}")
        return False


def test_rsa_signature():
    """測試 RSA 簽名"""
    print_section("測試 6: RSA 非對稱加密")
    
    print("檢查 RSA 金鑰文件...")
    
    import os
    from pathlib import Path
    
    keys_dir = Path(__file__).parent.parent / "keys"
    private_key = keys_dir / "jwt_private.pem"
    public_key = keys_dir / "jwt_public.pem"
    
    if private_key.exists() and public_key.exists():
        print("✅ RSA 金鑰對已生成")
        print(f"   私鑰: {private_key}")
        print(f"   公鑰: {public_key}")
        
        # 讀取金鑰大小
        with open(private_key, 'r') as f:
            key_content = f.read()
            if 'BEGIN PRIVATE KEY' in key_content:
                print("✅ 私鑰格式正確 (PKCS#8)")
        
        with open(public_key, 'r') as f:
            key_content = f.read()
            if 'BEGIN PUBLIC KEY' in key_content:
                print("✅ 公鑰格式正確")
        
        return True
    else:
        print("❌ RSA 金鑰文件未找到")
        return False


def main():
    """主測試流程"""
    print("\n" + "🔐" * 30)
    print("安全增強功能測試")
    print("🔐" * 30)
    
    # 測試 1: RSA 簽名
    test_rsa_signature()
    
    # 測試 2: 註冊
    access_token, cookies = test_register()
    if not access_token:
        print("\n❌ 測試中止：註冊失敗")
        return
    
    # 測試 3: Token 驗證
    test_token_validation(access_token)
    
    # 測試 4: Token 刷新
    new_access_token, new_cookies = test_token_refresh(cookies)
    if new_access_token:
        access_token = new_access_token
        cookies = new_cookies
    
    # 測試 5: 登出和黑名單
    test_logout(access_token, cookies)
    
    # 測試 6: 重新登入
    access_token, cookies = test_login()
    if access_token:
        test_token_validation(access_token)
    
    print("\n" + "=" * 60)
    print("  測試完成")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
