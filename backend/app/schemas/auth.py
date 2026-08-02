
from pydantic import BaseModel, EmailStr, Field, field_validator, ConfigDict, validator
from typing import Optional
from datetime import datetime
class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, description="用戶名")
    email: EmailStr = Field(..., description="電子郵件地址")
    password: str = Field(..., min_length=8, description="密碼")
    
    @validator('username')
    def username_alphanumeric(cls, v):
        import re
        if not re.match(r'^[\w\-]+$', v):
            raise ValueError('用戶名只能包含字母、數字、下劃線和連字符')
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "username": "john_doe",
                "email": "john@example.com",
                "password": "SecurePass123"
            }
        }
class UserLogin(BaseModel):
    username: str = Field(..., description="用戶名或電子郵件")
    password: str = Field(..., description="密碼")
    
    class Config:
        json_schema_extra = {
            "example": {
                "username": "john_doe",
                "password": "SecurePass123"
            }
        }
class Token(BaseModel):
    access_token: str = Field(..., description="訪問令牌")
    refresh_token: str = Field(..., description="刷新令牌")
    token_type: str = Field(default="bearer", description="令牌類型")
    expires_in: Optional[int] = Field(default=1800, description="過期時間(秒)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 1800
            }
        }
class TokenRefresh(BaseModel):
    refresh_token: str = Field(..., description="刷新令牌")
    
    class Config:
        json_schema_extra = {
            "example": {
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            }
        }
class UserProfile(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    username: str
    email: str
    role: str
    is_active: bool
    is_admin: bool
    created_at: datetime
    last_login: Optional[datetime] = None
class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    current_password: Optional[str] = None
    new_password: Optional[str] = Field(None, min_length=8)
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "newemail@example.com",
                "current_password": "OldPass123",
                "new_password": "NewSecurePass456"
            }
        }
class PasswordChange(BaseModel):
    current_password: str = Field(..., description="當前密碼")
    new_password: str = Field(..., min_length=8, description="新密碼")
    confirm_password: str = Field(..., description="確認新密碼")
    
    @validator('confirm_password')
    def passwords_match(cls, v, values):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('兩次輸入的密碼不一致')
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "current_password": "OldPass123",
                "new_password": "NewSecurePass456",
                "confirm_password": "NewSecurePass456"
            }
        }
class PasswordReset(BaseModel):
    user_id: int = Field(..., description="用戶 ID")
    new_password: str = Field(..., min_length=8, description="新密碼")
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": 5,
                "new_password": "ResetPass789"
            }
        }
class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)
    role: str = Field(default="user", pattern="^(user|admin|moderator)$")
    is_active: bool = Field(default=True)
    is_admin: bool = Field(default=False)
    
    class Config:
        json_schema_extra = {
            "example": {
                "username": "new_user",
                "email": "newuser@example.com",
                "password": "InitialPass123",
                "role": "user",
                "is_active": True,
                "is_admin": False
            }
        }
class LoginResponse(BaseModel):
    user: UserProfile
    tokens: Token
    message: str = Field(default="登入成功")
    
    class Config:
        json_schema_extra = {
            "example": {
                "user": {
                    "id": 1,
                    "username": "john_doe",
                    "email": "john@example.com",
                    "role": "user",
                    "is_active": True,
                    "is_admin": False,
                    "created_at": "2024-01-01T00:00:00",
                    "last_login": "2024-01-15T10:30:00"
                },
                "tokens": {
                    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                    "token_type": "bearer",
                    "expires_in": 1800
                },
                "message": "登入成功"
            }
        }
class MessageResponse(BaseModel):
    message: str
    success: bool = True
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "操作成功",
                "success": True
            }
        }
