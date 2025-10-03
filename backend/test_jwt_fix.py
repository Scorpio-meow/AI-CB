"""
測試 JWT 修復是否正常工作
"""
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(__file__))

from app.core.jwt_auth import TokenManager, create_token_pair

def test_jwt_operations():
    """測試 JWT token 的創建和解碼"""
    print("🧪 測試 JWT 操作...")
    
    # 測試用戶數據
    user_data = {
        "user_id": 1,
        "username": "test_user",
        "email": "test@example.com",
        "role": "admin",
        "is_admin": True
    }
    
    try:
        # 1. 創建 token 對
        print("\n1️⃣ 創建 Token 對...")
        tokens = create_token_pair(user_data)
        print(f"✅ Access Token: {tokens['access_token'][:50]}...")
        print(f"✅ Refresh Token: {tokens['refresh_token'][:50]}...")
        
        # 2. 解碼 access token
        print("\n2️⃣ 解碼 Access Token...")
        access_payload = TokenManager.decode_token(tokens['access_token'])
        print(f"✅ Payload: {access_payload}")
        
        # 3. 驗證 token 類型
        print("\n3️⃣ 驗證 Token 類型...")
        is_access = TokenManager.verify_token_type(access_payload, "access")
        print(f"✅ 是 Access Token: {is_access}")
        
        # 4. 解碼 refresh token
        print("\n4️⃣ 解碼 Refresh Token...")
        refresh_payload = TokenManager.decode_token(tokens['refresh_token'])
        print(f"✅ Payload: {refresh_payload}")
        
        # 5. 驗證 refresh token 類型
        print("\n5️⃣ 驗證 Refresh Token 類型...")
        is_refresh = TokenManager.verify_token_type(refresh_payload, "refresh")
        print(f"✅ 是 Refresh Token: {is_refresh}")
        
        print("\n" + "="*60)
        print("✅ 所有測試通過! JWT 系統運行正常")
        print("="*60)
        
        return True
        
    except Exception as e:
        print(f"\n❌ 測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_jwt_operations()
    sys.exit(0 if success else 1)
