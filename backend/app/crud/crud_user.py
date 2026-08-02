
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional, List
from datetime import datetime
from app.models import User
from app.core.jwt_auth import PasswordManager
def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()
def get_user_by_username(db: Session, username: str) -> Optional[User]:
    return db.query(User).filter(User.username == username).first()
def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(User.email == email).first()
def get_user_by_username_or_email(db: Session, identifier: str) -> Optional[User]:
    return db.query(User).filter(
        or_(User.username == identifier, User.email == identifier)
    ).first()
def get_users(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    is_active: Optional[bool] = None
) -> List[User]:
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
    query = db.query(User)
    
    if is_active is not None:
        query = query.filter(User.is_active == is_active)
    
    return query.count()
