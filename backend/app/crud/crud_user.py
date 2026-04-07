"""
用戶 CRUD 操作
處理用戶相關的數據庫操作
"""

from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional, List
from datetime import datetime

from app.models import User
from app.core.jwt_auth import PasswordManager


def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    """
    根據 ID 獲取用戶
    
    Args:
        db: 數據庫 session
        user_id: 用戶 ID
        
    Returns:
        用戶對象或 None
    """
    return db.query(User).filter(User.id == user_id).first()


def get_user_by_username(db: Session, username: str) -> Optional[User]:
    """
    根據用戶名獲取用戶
    
    Args:
        db: 數據庫 session
        username: 用戶名
        
    Returns:
        用戶對象或 None
    """
    return db.query(User).filter(User.username == username).first()


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """
    根據電子郵件獲取用戶
    
    Args:
        db: 數據庫 session
        email: 電子郵件地址
        
    Returns:
        用戶對象或 None
    """
    return db.query(User).filter(User.email == email).first()


def get_user_by_username_or_email(db: Session, identifier: str) -> Optional[User]:
    """
    根據用戶名或電子郵件獲取用戶
    
    Args:
        db: 數據庫 session
        identifier: 用戶名或電子郵件
        
    Returns:
        用戶對象或 None
    """
    return db.query(User).filter(
        or_(User.username == identifier, User.email == identifier)
    ).first()


def get_users(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    is_active: Optional[bool] = None
) -> List[User]:
    """
    獲取用戶列表
    
    Args:
        db: 數據庫 session
        skip: 跳過的記錄數
        limit: 返回的最大記錄數
        is_active: 過濾活躍狀態 (None = 全部)
        
    Returns:
        用戶列表
    """
    query = db.query(User)
    
    if is_active is not None:
        query = query.filter(User.is_active == is_active)
    
    return query.offset(skip).limit(limit).all()


def create_user(
    db: Session,
    username: str,
    email: str,
    password: str,
    role: str = "user",
    is_admin: bool = False
) -> User:
    """
    創建新用戶
    
    Args:
        db: 數據庫 session
        username: 用戶名
        email: 電子郵件
        password: 明文密碼 (將自動加密)
        role: 用戶角色
        is_admin: 是否為管理員
        
    Returns:
        新創建的用戶對象
    """
    hashed_password = PasswordManager.hash_password(password)
    
    db_user = User(
        username=username,
        email=email,
        hashed_password=hashed_password,
        role=role,
        is_admin=is_admin,
        is_active=True,
        created_at=datetime.utcnow()
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    return db_user


def authenticate_user(
    db: Session,
    username_or_email: str,
    password: str
) -> Optional[User]:
    """
    驗證用戶憑證
    
    Args:
        db: 數據庫 session
        username_or_email: 用戶名或電子郵件
        password: 明文密碼
        
    Returns:
        驗證成功返回用戶對象,否則返回 None
    """
    user = get_user_by_username_or_email(db, username_or_email)
    
    if not user:
        return None
    
    if not user.is_active:
        return None
    
    if not PasswordManager.verify_password(password, user.hashed_password):
        return None

    if PasswordManager.needs_rehash(user.hashed_password):
        user.hashed_password = PasswordManager.hash_password(password)
        db.commit()
        db.refresh(user)
    
    return user


def update_user_password(
    db: Session,
    user_id: int,
    new_password: str
) -> Optional[User]:
    """
    更新用戶密碼
    
    Args:
        db: 數據庫 session
        user_id: 用戶 ID
        new_password: 新的明文密碼
        
    Returns:
        更新後的用戶對象或 None
    """
    user = get_user_by_id(db, user_id)
    
    if not user:
        return None
    
    user.hashed_password = PasswordManager.hash_password(new_password)
    db.commit()
    db.refresh(user)
    
    return user


def update_user_email(
    db: Session,
    user_id: int,
    new_email: str
) -> Optional[User]:
    """
    更新用戶電子郵件
    
    Args:
        db: 數據庫 session
        user_id: 用戶 ID
        new_email: 新的電子郵件地址
        
    Returns:
        更新後的用戶對象或 None
    """
    user = get_user_by_id(db, user_id)
    
    if not user:
        return None
    
    user.email = new_email
    db.commit()
    db.refresh(user)
    
    return user


def update_user_last_login(
    db: Session,
    user_id: int
) -> Optional[User]:
    """
    更新用戶最後登入時間
    
    Args:
        db: 數據庫 session
        user_id: 用戶 ID
        
    Returns:
        更新後的用戶對象或 None
    """
    user = get_user_by_id(db, user_id)
    
    if not user:
        return None
    
    user.last_login = datetime.utcnow()
    db.commit()
    db.refresh(user)
    
    return user


def deactivate_user(
    db: Session,
    user_id: int
) -> Optional[User]:
    """
    停用用戶帳號
    
    Args:
        db: 數據庫 session
        user_id: 用戶 ID
        
    Returns:
        更新後的用戶對象或 None
    """
    user = get_user_by_id(db, user_id)
    
    if not user:
        return None
    
    user.is_active = False
    db.commit()
    db.refresh(user)
    
    return user


def activate_user(
    db: Session,
    user_id: int
) -> Optional[User]:
    """
    啟用用戶帳號
    
    Args:
        db: 數據庫 session
        user_id: 用戶 ID
        
    Returns:
        更新後的用戶對象或 None
    """
    user = get_user_by_id(db, user_id)
    
    if not user:
        return None
    
    user.is_active = True
    db.commit()
    db.refresh(user)
    
    return user


def delete_user(
    db: Session,
    user_id: int
) -> bool:
    """
    刪除用戶 (永久刪除)
    
    Args:
        db: 數據庫 session
        user_id: 用戶 ID
        
    Returns:
        是否刪除成功
    """
    user = get_user_by_id(db, user_id)
    
    if not user:
        return False
    
    db.delete(user)
    db.commit()
    
    return True


def update_user_role(
    db: Session,
    user_id: int,
    role: str,
    is_admin: Optional[bool] = None
) -> Optional[User]:
    """
    更新用戶角色
    
    Args:
        db: 數據庫 session
        user_id: 用戶 ID
        role: 新角色
        is_admin: 是否為管理員 (可選)
        
    Returns:
        更新後的用戶對象或 None
    """
    user = get_user_by_id(db, user_id)
    
    if not user:
        return None
    
    user.role = role
    
    if is_admin is not None:
        user.is_admin = is_admin
    
    db.commit()
    db.refresh(user)
    
    return user


def count_users(db: Session, is_active: Optional[bool] = None) -> int:
    """
    統計用戶數量
    
    Args:
        db: 數據庫 session
        is_active: 過濾活躍狀態
        
    Returns:
        用戶數量
    """
    query = db.query(User)
    
    if is_active is not None:
        query = query.filter(User.is_active == is_active)
    
    return query.count()
