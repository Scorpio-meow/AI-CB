"""
JWT 認證核心模組
提供完整的 JWT Token 生成、驗證和密碼加密功能
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import os
from dotenv import load_dotenv

load_dotenv()

# JWT 配置
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-this-in-production")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

# 密碼加密配置
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# HTTP Bearer Token 認證
security = HTTPBearer()


class PasswordManager:
    """密碼管理器 - 處理密碼加密和驗證"""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """
        加密密碼
        
        Args:
            password: 明文密碼
            
        Returns:
            加密後的密碼哈希
        """
        # bcrypt 限制密碼長度為 72 字節
        if len(password.encode('utf-8')) > 72:
            password = password[:72]
        return pwd_context.hash(password)
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """
        驗證密碼
        
        Args:
            plain_password: 明文密碼
            hashed_password: 加密後的密碼哈希
            
        Returns:
            驗證結果
        """
        # bcrypt 限制密碼長度為 72 字節
        if len(plain_password.encode('utf-8')) > 72:
            plain_password = plain_password[:72]
        return pwd_context.verify(plain_password, hashed_password)


class TokenManager:
    """JWT Token 管理器"""
    
    @staticmethod
    def create_access_token(
        data: Dict[str, Any],
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        創建訪問令牌 (Access Token)
        
        Args:
            data: 要編碼到 token 中的數據 (通常包含 user_id, username, role 等)
            expires_delta: 自定義過期時間
            
        Returns:
            JWT access token
        """
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({
            "exp": expire,
            "type": "access",
            "iat": datetime.utcnow()
        })
        
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    
    @staticmethod
    def create_refresh_token(
        data: Dict[str, Any],
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        創建刷新令牌 (Refresh Token)
        
        Args:
            data: 要編碼到 token 中的數據
            expires_delta: 自定義過期時間
            
        Returns:
            JWT refresh token
        """
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        
        to_encode.update({
            "exp": expire,
            "type": "refresh",
            "iat": datetime.utcnow()
        })
        
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    
    @staticmethod
    def decode_token(token: str) -> Dict[str, Any]:
        """
        解碼並驗證 JWT token
        
        Args:
            token: JWT token 字符串
            
        Returns:
            解碼後的 payload
            
        Raises:
            HTTPException: 如果 token 無效或過期
        """
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            return payload
        except JWTError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"無效的認證令牌: {str(e)}",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    @staticmethod
    def verify_token_type(payload: Dict[str, Any], expected_type: str) -> bool:
        """
        驗證 token 類型
        
        Args:
            payload: token payload
            expected_type: 期望的 token 類型 ('access' 或 'refresh')
            
        Returns:
            是否匹配
        """
        return payload.get("type") == expected_type


# === 依賴注入函數 ===

async def get_current_user_from_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(lambda: None)  # 將在實際使用時注入正確的 db session
) -> Dict[str, Any]:
    """
    從 HTTP Authorization Bearer Token 中獲取當前用戶
    
    Args:
        credentials: HTTP Bearer 認證憑證
        db: 數據庫 session (可選,用於額外的用戶驗證)
        
    Returns:
        用戶信息字典
        
    Raises:
        HTTPException: 如果 token 無效
    """
    token = credentials.credentials
    payload = TokenManager.decode_token(token)
    
    # 驗證是否為 access token
    if not TokenManager.verify_token_type(payload, "access"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="無效的令牌類型",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 提取用戶信息
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="令牌中缺少用戶信息",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return {
        "user_id": int(user_id),
        "username": payload.get("username"),
        "email": payload.get("email"),
        "role": payload.get("role", "user"),
        "is_admin": payload.get("is_admin", False)
    }


async def get_current_active_user(
    current_user: Dict[str, Any] = Depends(get_current_user_from_token)
) -> Dict[str, Any]:
    """
    獲取當前活躍用戶 (可在此添加額外的活躍狀態檢查)
    
    Args:
        current_user: 當前用戶信息
        
    Returns:
        用戶信息字典
    """
    return current_user


async def get_current_admin_user(
    current_user: Dict[str, Any] = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    獲取當前管理員用戶 (僅管理員可通過)
    
    Args:
        current_user: 當前用戶信息
        
    Returns:
        管理員用戶信息
        
    Raises:
        HTTPException: 如果用戶不是管理員
    """
    if not current_user.get("is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理員權限"
        )
    
    return current_user


def create_token_pair(user_data: Dict[str, Any]) -> Dict[str, str]:
    """
    創建 access token 和 refresh token 對
    
    Args:
        user_data: 用戶數據 (必須包含 user_id)
        
    Returns:
        包含 access_token 和 refresh_token 的字典
    """
    # 準備 token payload
    token_data = {
        "sub": str(user_data["user_id"]),
        "username": user_data.get("username"),
        "email": user_data.get("email"),
        "role": user_data.get("role", "user"),
        "is_admin": user_data.get("is_admin", False)
    }
    
    access_token = TokenManager.create_access_token(token_data)
    refresh_token = TokenManager.create_refresh_token({"sub": str(user_data["user_id"])})
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


def verify_refresh_token(token: str) -> Dict[str, Any]:
    """
    驗證 refresh token 並返回 payload
    
    Args:
        token: refresh token
        
    Returns:
        token payload
        
    Raises:
        HTTPException: 如果 token 無效或類型不正確
    """
    payload = TokenManager.decode_token(token)
    
    if not TokenManager.verify_token_type(payload, "refresh"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="無效的刷新令牌類型"
        )
    
    return payload


# === 安全工具函數 ===

def validate_password_strength(password: str) -> tuple[bool, str]:
    """
    驗證密碼強度
    
    Args:
        password: 待驗證的密碼
        
    Returns:
        (是否有效, 錯誤消息)
    """
    if len(password) < 8:
        return False, "密碼長度至少需要 8 個字符"
    
    if not any(c.isupper() for c in password):
        return False, "密碼必須包含至少一個大寫字母"
    
    if not any(c.islower() for c in password):
        return False, "密碼必須包含至少一個小寫字母"
    
    if not any(c.isdigit() for c in password):
        return False, "密碼必須包含至少一個數字"
    
    return True, ""


def sanitize_username(username: str) -> str:
    """
    清理用戶名 (移除特殊字符)
    
    Args:
        username: 原始用戶名
        
    Returns:
        清理後的用戶名
    """
    import re
    # 只允許字母、數字、下劃線和連字符
    return re.sub(r'[^\w\-]', '', username)
