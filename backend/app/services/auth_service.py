from sqlalchemy.orm import Session
from app.models import User, UserCreate
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
import os

class AuthService:
    def __init__(self):
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        self.secret_key = os.getenv("SECRET_KEY", "your-secret-key")
        self.algorithm = os.getenv("ALGORITHM", "HS256")
        self.access_token_expire_minutes = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """驗證密碼"""
        return self.pwd_context.verify(plain_password, hashed_password)
    
    def get_password_hash(self, password: str) -> str:
        """生成密碼哈希"""
        return self.pwd_context.hash(password)
    
    def create_access_token(self, data: dict):
        """創建訪問令牌"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
    
    async def create_user(self, db: Session, user_data: UserCreate):
        """創建新用戶"""
        # 檢查用戶名是否已存在
        existing_user = db.query(User).filter(User.username == user_data.username).first()
        if existing_user:
            raise ValueError("用戶名已存在")
        
        # 檢查郵箱是否已存在
        existing_email = db.query(User).filter(User.email == user_data.email).first()
        if existing_email:
            raise ValueError("郵箱已被註冊")
        
        # 創建新用戶
        hashed_password = self.get_password_hash(user_data.password)
        db_user = User(
            username=user_data.username,
            email=user_data.email,
            hashed_password=hashed_password
        )
        
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        
        return db_user
    
    async def authenticate_user(self, db: Session, username: str, password: str):
        """驗證用戶"""
        user = db.query(User).filter(User.username == username).first()
        if not user:
            return False
        if not self.verify_password(password, user.hashed_password):
            return False
        return user
    
    async def get_current_user(self, db: Session, token: str):
        """根據令牌獲取當前用戶"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            username: str = payload.get("sub")
            if username is None:
                return None
        except JWTError:
            return None
        
        user = db.query(User).filter(User.username == username).first()
        return user
    
    async def get_user_by_id(self, db: Session, user_id: int):
        """根據 ID 獲取用戶"""
        return db.query(User).filter(User.id == user_id).first()
