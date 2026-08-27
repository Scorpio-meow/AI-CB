from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from typing import List
import logging
import os
logger = logging.getLogger(__name__)
from app.models.database import get_db
from app.schemas.auth import (
    UserRegister, UserLogin, Token, TokenRefresh,
    UserProfile, UserUpdate, PasswordChange,
    LoginResponse, MessageResponse
)
from app.crud.crud_user import (
    get_user_by_username, get_user_by_email,
    create_user, authenticate_user,
    update_user_password, update_user_email,
    update_user_last_login, get_user_by_id
)
from app.core.jwt_auth import (
    create_token_pair, verify_refresh_token,
    get_current_active_user, get_current_admin_user,
    validate_password_strength, sanitize_username,
    PasswordManager, revoke_token
)
from app.core.config import settings
from app.core.security_logging import log_security_event
REFRESH_COOKIE_NAME = "refresh_token"
REFRESH_COOKIE_PATH = "/api/auth"
router = APIRouter(prefix="/api/auth", tags=["Authentication"])
security = HTTPBearer()
def _get_cookie_secure() -> bool:
    if settings.COOKIE_SECURE is not None:
        return settings.COOKIE_SECURE
    return settings.ENVIRONMENT == "production"
def _get_cookie_samesite() -> str:
    return settings.COOKIE_SAMESITE or "lax"
def _set_refresh_cookie(response: Response, refresh_token: str) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=refresh_token,
        httponly=True,
        secure=_get_cookie_secure(),
        samesite=_get_cookie_samesite(),
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        path=REFRESH_COOKIE_PATH,
    )
@router.post("/register", response_model=LoginResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserRegister,
    request: Request,
    response: Response,
    db: Session = Depends(get_db)
):
    username = sanitize_username(user_data.username)
    
    if get_user_by_username(db, username):
        log_security_event("REGISTER_FAILED", request=request, details={"username": username, "reason": "用戶名已存在"})
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用戶名已被使用"
        )
    
    if get_user_by_email(db, user_data.email):
        log_security_event("REGISTER_FAILED", request=request, details={"email": user_data.email, "reason": "電子郵件已存在"})
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="電子郵件已被使用"
        )
    
    is_valid, error_msg = validate_password_strength(user_data.password)
    if not is_valid:
        log_security_event("REGISTER_FAILED", request=request, details={"username": username, "reason": error_msg})
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )
    
    try:
        new_user = create_user(
            db=db,
            username=username,
            email=user_data.email,
            password=user_data.password,
            role="user",
            is_admin=False
        )
        
        tokens = create_token_pair({
            "user_id": new_user.id,
            "username": new_user.username,
            "email": new_user.email,
            "role": new_user.role,
            "is_admin": new_user.is_admin
        })
        
        _set_refresh_cookie(response, tokens["refresh_token"])
        
        log_security_event("USER_REGISTERED", request=request, user_id=new_user.id, details={
            "username": new_user.username
        })
        
        return LoginResponse(
            user=UserProfile.model_validate(new_user),
            tokens=Token(
                access_token=tokens["access_token"],
                token_type=tokens["token_type"],
                refresh_token=""
            ),
            message="註冊成功"
        )
        
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.exception("用戶註冊失敗")
        log_security_event("REGISTER_ERROR", request=request, details={"error": "internal_error"})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="註冊失敗: 內部錯誤，請聯繫系統管理員"
        )
@router.post("/login", response_model=LoginResponse)
async def login(
    credentials: UserLogin,
    request: Request,
    response: Response,
    db: Session = Depends(get_db)
):
    user = authenticate_user(db, credentials.username, credentials.password)
    
    if not user:
        log_security_event("LOGIN_FAILED", request=request, details={
            "username": credentials.username,
            "reason": "無效的憑證"
        })
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用戶名或密碼錯誤",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    update_user_last_login(db, user.id)
    
    tokens = create_token_pair({
        "user_id": user.id,
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "is_admin": user.is_admin
    })
    
    _set_refresh_cookie(response, tokens["refresh_token"])
    
    log_security_event("USER_LOGIN", request=request, user_id=user.id, details={
        "username": user.username
    })
    
    return LoginResponse(
        user=UserProfile.model_validate(user),
        tokens=Token(
            access_token=tokens["access_token"],
            token_type=tokens["token_type"],
            refresh_token=""
        ),
        message="登入成功"
    )
@router.post("/refresh", response_model=Token)
async def refresh_token(
    request: Request,
    response: Response,
    db: Session = Depends(get_db)
):
    try:
        refresh_token_value = request.cookies.get(REFRESH_COOKIE_NAME)
        
        if not refresh_token_value:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="未找到刷新令牌"
            )
        
        payload = verify_refresh_token(refresh_token_value)
        
        user_id = payload.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="無效的刷新令牌"
            )
        
        user = get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="無效的刷新令牌"
            )
        
        tokens = create_token_pair({
            "user_id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "is_admin": user.is_admin
        })
        
        _set_refresh_cookie(response, tokens["refresh_token"])
        
        log_security_event("TOKEN_REFRESHED", request=request, user_id=user.id)
        
        return Token(
            access_token=tokens["access_token"],
            token_type=tokens["token_type"],
            refresh_token=""
        )
        
    except HTTPException:
        raise
    except Exception as e:
        log_security_event("TOKEN_REFRESH_ERROR", request=request, details={"error": str(e)})
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="刷新令牌失敗"
        )
@router.get("/me", response_model=UserProfile)
async def get_current_user_profile(
    user: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    user = get_user_by_id(db, user["user_id"])
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用戶不存在"
        )
    
    return UserProfile.model_validate(user)
@router.put("/me", response_model=UserProfile)
async def update_current_user_profile(
    user_update: UserUpdate,
    request: Request,
    user: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    user_obj = get_user_by_id(db, user["user_id"])
    
    if not user_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用戶不存在"
        )
    
    if user_update.email:
        existing_user = get_user_by_email(db, user_update.email)
        if existing_user and existing_user.id != user_obj.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="該電子郵件已被使用"
            )
        update_user_email(db, user_obj.id, user_update.email)
        log_security_event("USER_EMAIL_UPDATED", request=request, user_id=user_obj.id)
    
    if user_update.new_password:
        if not user_update.current_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="需要提供當前密碼"
            )
        
        pwd_mgr = PasswordManager()
        if not pwd_mgr.verify_password(user_update.current_password, user_obj.hashed_password):
            log_security_event("PASSWORD_CHANGE_FAILED", request=request, user_id=user_obj.id, details={
                "reason": "當前密碼錯誤"
            })
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="當前密碼錯誤"
            )
        
        is_valid, error_msg = validate_password_strength(user_update.new_password)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )
        
        update_user_password(db, user_obj.id, user_update.new_password)
        log_security_event("PASSWORD_CHANGED", request=request, user_id=user_obj.id)
    
    user_obj = get_user_by_id(db, user_obj.id)
    return UserProfile.model_validate(user_obj)
@router.post("/change-password", response_model=MessageResponse)
async def change_password(
    password_data: PasswordChange,
    request: Request,
    user: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    user_obj = get_user_by_id(db, user["user_id"])
    
    if not user_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用戶不存在"
        )
    
    pwd_mgr = PasswordManager()
    if not pwd_mgr.verify_password(password_data.current_password, user_obj.hashed_password):
        log_security_event("PASSWORD_CHANGE_FAILED", request=request, user_id=user_obj.id, details={
            "reason": "當前密碼錯誤"
        })
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="當前密碼錯誤"
        )
    
    is_valid, error_msg = validate_password_strength(password_data.new_password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )
    
    update_user_password(db, user_obj.id, password_data.new_password)
    log_security_event("PASSWORD_CHANGED", request=request, user_id=user_obj.id)
    
    return MessageResponse(message="密碼修改成功")
@router.post("/logout", response_model=MessageResponse)
async def logout(
    request: Request,
    response: Response,
    user: dict = Depends(get_current_active_user)
):
    try:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            access_token = auth_header.split(" ")[1]
            revoke_token(access_token)
        
        refresh_token_value = request.cookies.get(REFRESH_COOKIE_NAME)
        if refresh_token_value:
            revoke_token(refresh_token_value)
        
        response.delete_cookie(
            key=REFRESH_COOKIE_NAME,
            path=REFRESH_COOKIE_PATH
        )
        
        log_security_event("USER_LOGOUT", request=request, user_id=user["user_id"], details={
            "username": user["username"]
        })
        
        return MessageResponse(message="登出成功")
    
    except Exception as e:
        log_security_event("LOGOUT_ERROR", request=request, user_id=user.get("user_id"), details={
            "error": str(e)
        })
        response.delete_cookie(key=REFRESH_COOKIE_NAME, path=REFRESH_COOKIE_PATH)
        return MessageResponse(message="登出成功")
@router.post("/validate-token", response_model=MessageResponse)
async def validate_token(
    user: dict = Depends(get_current_active_user)
):
    return MessageResponse(message="令牌有效")
