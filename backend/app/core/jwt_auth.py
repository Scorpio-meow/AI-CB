
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import logging
import bcrypt as bcrypt_lib
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import os
from dotenv import load_dotenv
load_dotenv()
logger = logging.getLogger(__name__)
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-this-in-production")
ALGORITHM = os.getenv("JWT_ALGORITHM", "RS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
try:
    from app.core.rsa_keys import rsa_manager
    USE_RSA = True
    RSA_PRIVATE_KEY = rsa_manager.get_private_key_pem()
    RSA_PUBLIC_KEY = rsa_manager.get_public_key_pem()
    print("使用 RSA 非對稱加密進行 JWT 簽名")
except Exception as e:
    import os
    if os.getenv("ENVIRONMENT") == "production":
        print(f"生產環境 RSA 金鑰載入失敗: {e}")
        raise RuntimeError("生產環境必須使用 RSA 金鑰進行 JWT 簽名") from e
    else:
        USE_RSA = False
        RSA_PRIVATE_KEY = None
        RSA_PUBLIC_KEY = None
        ALGORITHM = "HS256"
        print(f"開發環境 RSA 金鑰載入失敗，暫時使用 HS256: {e}")
        print(f"警告：請盡快修復 RSA 金鑰配置！")
try:
    from app.core.redis_client import TokenBlacklist
    USE_BLACKLIST = True
except Exception as e:
    USE_BLACKLIST = False
    print(f"Token 黑名單功能不可用: {e}")
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
security = HTTPBearer()
def _normalize_legacy_bcrypt_password(password: str, max_bytes: int = 72) -> str:
    encoded_password = password.encode("utf-8")
    if len(encoded_password) <= max_bytes:
        return password
    return encoded_password[:max_bytes].decode("utf-8", errors="ignore")
class PasswordManager:
    
    @staticmethod
    def hash_password(password: str) -> str:
        return pwd_context.hash(password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        if hashed_password.startswith("$2"):
            plain_password = _normalize_legacy_bcrypt_password(plain_password)
            try:
                return bcrypt_lib.checkpw(
                    plain_password.encode("utf-8"),
                    hashed_password.encode("utf-8"),
                )
            except ValueError:
                return False
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def needs_rehash(hashed_password: str) -> bool:
        return hashed_password.startswith("$2") or pwd_context.needs_update(hashed_password)
class TokenManager:
    
    @staticmethod
    def create_access_token(
        data: Dict[str, Any],
        expires_delta: Optional[timedelta] = None
    ) -> str:
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
        
        if USE_RSA:
            encoded_jwt = jwt.encode(to_encode, RSA_PRIVATE_KEY, algorithm="RS256")
        else:
            encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm="HS256")
        return encoded_jwt
    
    @staticmethod
    def create_refresh_token(
        data: Dict[str, Any],
        expires_delta: Optional[timedelta] = None
    ) -> str:
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
        
        if USE_RSA:
            encoded_jwt = jwt.encode(to_encode, RSA_PRIVATE_KEY, algorithm="RS256")
        else:
            encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm="HS256")
        return encoded_jwt
    
    @staticmethod
    def decode_token(token: str) -> Dict[str, Any]:
        if USE_BLACKLIST and TokenBlacklist.is_blacklisted(token):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="令牌已被撤銷",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        try:
            if USE_RSA:
                payload = jwt.decode(
                    token, 
                    RSA_PUBLIC_KEY, 
                    algorithms=["RS256"],
                    options={"verify_signature": True, "verify_exp": True}
                )
            else:
                payload = jwt.decode(
                    token, 
                    SECRET_KEY, 
                    algorithms=["HS256"],
                    options={"verify_signature": True, "verify_exp": True}
                )
            return payload
        except JWTError:
            logger.exception("無效的認證令牌: 驗證失敗")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="無效的認證令牌: 驗證失敗",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    @staticmethod
    def verify_token_type(payload: Dict[str, Any], expected_type: str) -> bool:
        return payload.get("type") == expected_type
async def get_current_user_from_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(lambda: None)
) -> Dict[str, Any]:
    token = credentials.credentials
    payload = TokenManager.decode_token(token)
    
    if not TokenManager.verify_token_type(payload, "access"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="無效的令牌類型",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
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
    return current_user
async def get_current_admin_user(
    current_user: Dict[str, Any] = Depends(get_current_active_user)
) -> Dict[str, Any]:
    if not current_user.get("is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理員權限"
        )
    
    return current_user
def create_token_pair(user_data: Dict[str, Any]) -> Dict[str, str]:
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
    payload = TokenManager.decode_token(token)
    
    if not TokenManager.verify_token_type(payload, "refresh"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="無效的刷新令牌類型"
        )
    
    return payload
def validate_password_strength(password: str) -> tuple[bool, str]:
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
    import re
    return re.sub(r'[^\w\-]', '', username)
def revoke_token(token: str, expires_in: int = None):
    if not USE_BLACKLIST:
        print("Token 黑名單功能未啟用")
        return False
    
    try:
        if expires_in is None:
            payload = TokenManager.decode_token(token)
            exp = payload.get("exp")
            if exp:
                expires_in = max(int(exp - datetime.utcnow().timestamp()), 0)
            else:
                expires_in = 86400
        
        return TokenBlacklist.add_token(token, expires_in)
    except Exception as e:
        print(f"撤銷 Token 失敗: {e}")
        return False
