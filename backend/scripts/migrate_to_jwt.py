"""
數據庫遷移腳本 - 遷移到 JWT 認證系統

此腳本會:
1. 為 User 表添加新的欄位 (role, last_login)
2. 為現有用戶設置預設密碼 (可選)
3. 驗證數據庫遷移完成

使用方法:
python scripts/migrate_to_jwt.py
"""

import sys
import os

# 添加專案根目錄到 Python 路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import Column, String, DateTime, text, inspect
from app.models.database import engine, SessionLocal
from app.models import User
from app.core.jwt_auth import PasswordManager
from datetime import datetime


def column_exists(table_name: str, column_name: str) -> bool:
    """檢查表中是否存在某個欄位"""
    inspector = inspect(engine)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns


def add_column_if_not_exists(table_name: str, column_name: str, column_type: str):
    """如果欄位不存在,則添加"""
    if not column_exists(table_name, column_name):
        print(f"  添加欄位: {table_name}.{column_name} ({column_type})")
        with engine.connect() as conn:
            conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"))
            conn.commit()
        return True
    else:
        print(f"  欄位已存在: {table_name}.{column_name}")
        return False


def migrate_database():
    """執行數據庫遷移"""
    print("\n" + "="*60)
    print("         數據庫遷移: JWT 認證系統")
    print("="*60 + "\n")
    
    print("步驟 1: 檢查並添加新欄位...")
    
    # 添加 role 欄位
    added_role = add_column_if_not_exists("users", "role", "VARCHAR DEFAULT 'user'")
    
    # 添加 last_login 欄位
    added_last_login = add_column_if_not_exists("users", "last_login", "DATETIME")
    
    if added_role or added_last_login:
        print("✅ 欄位添加完成\n")
    else:
        print("✅ 所有欄位已存在,無需添加\n")
    
    # 步驟 2: 更新現有用戶數據
    print("步驟 2: 更新現有用戶數據...")
    db = SessionLocal()
    
    try:
        users = db.query(User).all()
        updated_count = 0
        
        for user in users:
            updated = False
            
            # 設置 role (如果為 None)
            if not hasattr(user, 'role') or user.role is None:
                user.role = "admin" if user.is_admin else "user"
                updated = True
            
            # 檢查密碼 (如果沒有密碼,設置預設密碼)
            if not user.hashed_password or user.hashed_password == '':
                print(f"  警告: 用戶 '{user.username}' 沒有密碼")
                set_password = input(f"    是否為此用戶設置預設密碼 'ChangeMe123'? (yes/no): ").strip().lower()
                
                if set_password in ['yes', 'y']:
                    user.hashed_password = PasswordManager.hash_password('ChangeMe123')
                    updated = True
                    print(f"    ✅ 已設置預設密碼,請儘快修改!")
            
            if updated:
                updated_count += 1
        
        if updated_count > 0:
            db.commit()
            print(f"✅ 已更新 {updated_count} 個用戶\n")
        else:
            print("✅ 無需更新用戶數據\n")
        
    except Exception as e:
        db.rollback()
        print(f"❌ 更新用戶數據失敗: {str(e)}\n")
    finally:
        db.close()
    
    # 步驟 3: 驗證遷移
    print("步驟 3: 驗證遷移...")
    
    required_columns = {
        'id': True,
        'username': True,
        'email': True,
        'hashed_password': True,
        'is_active': True,
        'is_admin': True,
        'role': True,
        'created_at': True,
        'last_login': True
    }
    
    missing_columns = []
    for col_name in required_columns.keys():
        if not column_exists('users', col_name):
            missing_columns.append(col_name)
    
    if missing_columns:
        print(f"❌ 遷移不完整,缺少欄位: {', '.join(missing_columns)}")
        return False
    else:
        print("✅ 所有必需欄位都已存在")
    
    # 統計信息
    db = SessionLocal()
    try:
        total_users = db.query(User).count()
        active_users = db.query(User).filter(User.is_active == True).count()
        admin_users = db.query(User).filter(User.is_admin == True).count()
        
        print(f"\n統計信息:")
        print(f"  總用戶數:   {total_users}")
        print(f"  活躍用戶:   {active_users}")
        print(f"  管理員:     {admin_users}")
    finally:
        db.close()
    
    print("\n" + "="*60)
    print("✅ 數據庫遷移完成!")
    print("="*60 + "\n")
    
    print("後續步驟:")
    print("1. 如果沒有管理員帳號,請運行: python scripts/create_admin.py")
    print("2. 通知用戶使用新的 JWT 認證系統登入")
    print("3. 更新前端應用以使用新的認證端點\n")
    
    return True


def main():
    try:
        success = migrate_database()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ 遷移失敗: {str(e)}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
