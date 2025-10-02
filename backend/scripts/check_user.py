"""
檢查資料庫中的用戶和測試密碼驗證
"""
import sys
import os

# 添加父目錄到 Python 路徑
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.database import get_db
from app.crud.crud_user import get_user_by_username, authenticate_user
from app.core.jwt_auth import PasswordManager

pwd_mgr = PasswordManager()
verify_password = pwd_mgr.verify_password

def main():
    print("=" * 60)
    print("用戶資料庫檢查")
    print("=" * 60)
    
    db = next(get_db())
    
    # 檢查用戶
    username = "yalkyao"
    user = get_user_by_username(db, username)
    
    if not user:
        print(f"\n❌ 用戶 '{username}' 不存在")
        return
    
    print(f"\n✅ 用戶存在:")
    print(f"   ID: {user.id}")
    print(f"   Username: {user.username}")
    print(f"   Email: {user.email}")
    print(f"   Role: {user.role}")
    print(f"   Is Admin: {user.is_admin}")
    print(f"   Is Active: {user.is_active}")
    print(f"   Hashed Password: {user.hashed_password[:50]}...")
    
    # 測試密碼驗證
    print(f"\n🔐 測試密碼驗證:")
    test_passwords = ["Mitac@2025", "Test123!", "admin123"]
    
    for pwd in test_passwords:
        result = verify_password(pwd, user.hashed_password)
        status = "✅ 正確" if result else "❌ 錯誤"
        print(f"   {status} - 密碼: {'*' * len(pwd)}")
    
    # 測試完整認證流程
    print(f"\n🔍 測試完整認證:")
    auth_user = authenticate_user(db, username, "Mitac@2025")
    if auth_user:
        print(f"   ✅ 認證成功 - 用戶: {auth_user.username}")
    else:
        print(f"   ❌ 認證失敗")

if __name__ == "__main__":
    main()
