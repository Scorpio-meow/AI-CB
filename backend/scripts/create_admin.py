"""
創建初始管理員帳號腳本

使用方法:
python scripts/create_admin.py --username admin --email admin@example.com --password YourSecurePassword123
"""

import sys
import os

# 添加專案根目錄到 Python 路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import argparse
from sqlalchemy.orm import Session
from app.models.database import SessionLocal
from app.crud.crud_user import get_user_by_username, get_user_by_email, create_user
from app.core.jwt_auth import validate_password_strength
import getpass


def create_admin_user(username: str, email: str, password: str):
    """
    創建管理員帳號
    
    Args:
        username: 管理員用戶名
        email: 管理員電子郵件
        password: 管理員密碼
    """
    db = SessionLocal()
    
    try:
        # 1. 檢查用戶名是否已存在
        existing_user = get_user_by_username(db, username)
        if existing_user:
            print(f"❌ 錯誤: 用戶名 '{username}' 已存在!")
            return False
        
        # 2. 檢查電子郵件是否已存在
        existing_email = get_user_by_email(db, email)
        if existing_email:
            print(f"❌ 錯誤: 電子郵件 '{email}' 已被使用!")
            return False
        
        # 3. 驗證密碼強度
        is_valid, error_msg = validate_password_strength(password)
        if not is_valid:
            print(f"❌ 密碼強度不足: {error_msg}")
            return False
        
        # 4. 創建管理員帳號
        admin_user = create_user(
            db=db,
            username=username,
            email=email,
            password=password,
            role="admin",
            is_admin=True
        )
        
        print("\n" + "="*60)
        print("✅ 管理員帳號創建成功!")
        print("="*60)
        print(f"用戶ID:    {admin_user.id}")
        print(f"用戶名:    {admin_user.username}")
        print(f"電子郵件:  {admin_user.email}")
        print(f"角色:      {admin_user.role}")
        print(f"管理員:    {'是' if admin_user.is_admin else '否'}")
        print(f"創建時間:  {admin_user.created_at}")
        print("="*60)
        print("\n您現在可以使用以下憑證登入系統:")
        print(f"  用戶名: {username}")
        print(f"  密碼:   (您剛才設置的密碼)")
        print("\n登入端點: POST /api/auth/login")
        print("="*60 + "\n")
        
        return True
        
    except Exception as e:
        print(f"❌ 創建管理員失敗: {str(e)}")
        return False
    finally:
        db.close()


def interactive_mode():
    """互動式模式創建管理員"""
    print("\n" + "="*60)
    print("         創建管理員帳號 (互動模式)")
    print("="*60 + "\n")
    
    # 獲取用戶名
    while True:
        username = input("請輸入管理員用戶名 (3-50 字符): ").strip()
        if len(username) >= 3 and len(username) <= 50:
            break
        print("❌ 用戶名長度必須在 3-50 字符之間")
    
    # 獲取電子郵件
    while True:
        email = input("請輸入管理員電子郵件: ").strip()
        if "@" in email and "." in email:
            break
        print("❌ 請輸入有效的電子郵件地址")
    
    # 獲取密碼
    while True:
        password = getpass.getpass("請輸入管理員密碼 (至少 8 字符,包含大小寫字母和數字): ")
        confirm_password = getpass.getpass("請再次輸入密碼以確認: ")
        
        if password != confirm_password:
            print("❌ 兩次輸入的密碼不一致,請重新輸入")
            continue
        
        is_valid, error_msg = validate_password_strength(password)
        if not is_valid:
            print(f"❌ {error_msg}")
            continue
        
        break
    
    # 確認創建
    print(f"\n您即將創建以下管理員帳號:")
    print(f"  用戶名:   {username}")
    print(f"  電子郵件: {email}")
    
    confirm = input("\n確認創建? (yes/no): ").strip().lower()
    
    if confirm in ['yes', 'y']:
        return create_admin_user(username, email, password)
    else:
        print("❌ 已取消創建")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="創建 ChatBot 系統的管理員帳號",
        epilog="示例: python scripts/create_admin.py --username admin --email admin@example.com"
    )
    
    parser.add_argument(
        "--username", "-u",
        type=str,
        help="管理員用戶名"
    )
    
    parser.add_argument(
        "--email", "-e",
        type=str,
        help="管理員電子郵件"
    )
    
    parser.add_argument(
        "--password", "-p",
        type=str,
        help="管理員密碼 (不建議在命令行中明文輸入,建議使用互動模式)"
    )
    
    parser.add_argument(
        "--interactive", "-i",
        action="store_true",
        help="使用互動模式"
    )
    
    args = parser.parse_args()
    
    # 如果指定互動模式或沒有提供參數,使用互動模式
    if args.interactive or not (args.username and args.email and args.password):
        success = interactive_mode()
    else:
        success = create_admin_user(args.username, args.email, args.password)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
