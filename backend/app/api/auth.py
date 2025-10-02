"""
認證 API 端點
提供用戶註冊、登入、令牌刷新、資料管理等功能
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from typing import List

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
    PasswordManager
)
from app.core.security_logging import log_security_event

router = APIRouter(prefix="/api/auth", tags=["Authentication"])
security = HTTPBearer()


@router.post("/register", response_model=LoginResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserRegister,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    用戶註冊
    
    - **username**: 用戶名(3-50 字符,只允許字母、數字、下劃線、連字符)
    - **email**: 電子郵件地址
    - **password**: 密碼 (至少 8 字符,包含大小寫字母和數字)
    
    返回用戶資料和 JWT tokens
    """
    # 1. 清理用戶名
    username = sanitize_username(user_data.username)
    
    # 2. 檢查用戶名是否已存在
    if get_user_by_username(db, username):
        log_security_event("REGISTER_FAILED", request=request, details={"username": username, "reason": "用戶名已存在"})
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用戶名已被使用"
        )
    
    # 3. 檢查電子郵件是否已存在
    if get_user_by_email(db, user_data.email):
        log_security_event("REGISTER_FAILED", request=request, details={"email": user_data.email, "reason": "電子郵件已存在"})
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="電子郵件已被使用"
        )
    
    # 4. 驗證密碼強度
    is_valid, error_msg = validate_password_strength(user_data.password)
    if not is_valid:
        log_security_event("REGISTER_FAILED", request=request, details={"username": username, "reason": error_msg})
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )
    
    # 5. 創建用戶
    try:
        new_user = create_user(
            db=db,
            username=username,
            email=user_data.email,
            password=user_data.password,
            role="user",
            is_admin=False
        )
        
        # 6. 生成 JWT tokens
        tokens = create_token_pair({
            "user_id": new_user.id,
            "username": new_user.username,
            "email": new_user.email,
            "role": new_user.role,
            "is_admin": new_user.is_admin
        })
        
        # 7. 記錄成功註冊
        log_security_event("USER_REGISTERED", request=request, user_id=new_user.id, details={
            "username": new_user.username
        })
        
        return LoginResponse(
            user=UserProfile.model_validate(new_user),
            tokens=Token(**tokens),
            message="註冊成功"
        )
        
    except Exception as e:
        log_security_event("REGISTER_ERROR", request=request, details={"error": str(e)})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"註冊失敗: {str(e)}"
        )


@router.post("/login", response_model=LoginResponse)
async def login(
    credentials: UserLogin,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    用戶登入
    
    - **username**: 用戶名或電子郵件
    - **password**: 密碼
    
    返回用戶資料和 JWT tokens
    """
    # 1. 驗證用戶憑證
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
    
    # 2. 更新最後登入時間
    update_user_last_login(db, user.id)
    
    # 3. 生成 JWT tokens
    tokens = create_token_pair({
        "user_id": user.id,
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "is_admin": user.is_admin
    })
    
    # 4. 記錄成功登入
    log_security_event("USER_LOGIN", request=request, user_id=user.id, details={
        "username": user.username
    })
    
    return LoginResponse(
        user=UserProfile.model_validate(user),
        tokens=Token(**tokens),
        message="登入成功"
    )


@router.post("/refresh", response_model=Token)
async def refresh_token(
    token_data: TokenRefresh,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    刷新 Access Token
    
    使用 Refresh Token 獲取新的 Access Token
    """
    try:
        # 驗證 refresh token 並獲取用戶信息
        user = verify_refresh_token(db, token_data.refresh_token)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="無效的刷新令牌"
            )
        
        # 生成新的 token pair
        tokens = create_token_pair({
            "user_id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "is_admin": user.is_admin
        })
        
        log_security_event("TOKEN_REFRESHED", request=request, user_id=user.id)
        
        return Token(**tokens)
        
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
    """
    獲取當前用戶資料
    
    需要有效的 Access Token
    """
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
    """
    更新當前用戶資料
    
    可更新：
    - 電子郵件
    - 密碼（需要提供當前密碼）
    """
    user_obj = get_user_by_id(db, user["user_id"])
    
    if not user_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用戶不存在"
        )
    
    # 更新電子郵件
    if user_update.email:
        # 檢查新郵件是否已被使用
        existing_user = get_user_by_email(db, user_update.email)
        if existing_user and existing_user.id != user_obj.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="該電子郵件已被使用"
            )
        update_user_email(db, user_obj.id, user_update.email)
        log_security_event("USER_EMAIL_UPDATED", request=request, user_id=user_obj.id)
    
    # 更新密碼
    if user_update.new_password:
        # 驗證當前密碼
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
        
        # 驗證新密碼強度
        is_valid, error_msg = validate_password_strength(user_update.new_password)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )
        
        update_user_password(db, user_obj.id, user_update.new_password)
        log_security_event("PASSWORD_CHANGED", request=request, user_id=user_obj.id)
    
    # 刷新用戶數據
    user_obj = get_user_by_id(db, user_obj.id)
    return UserProfile.model_validate(user_obj)


@router.post("/change-password", response_model=MessageResponse)
async def change_password(
    password_data: PasswordChange,
    request: Request,
    user: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    修改密碼
    
    需要提供當前密碼和新密碼
    """
    user_obj = get_user_by_id(db, user["user_id"])
    
    if not user_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用戶不存在"
        )
    
    # 驗證當前密碼
    pwd_mgr = PasswordManager()
    if not pwd_mgr.verify_password(password_data.current_password, user_obj.hashed_password):
        log_security_event("PASSWORD_CHANGE_FAILED", request=request, user_id=user_obj.id, details={
            "reason": "當前密碼錯誤"
        })
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="當前密碼錯誤"
        )
    
    # 驗證新密碼強度
    is_valid, error_msg = validate_password_strength(password_data.new_password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )
    
    # 更新密碼
    update_user_password(db, user_obj.id, password_data.new_password)
    log_security_event("PASSWORD_CHANGED", request=request, user_id=user_obj.id)
    
    return MessageResponse(message="密碼修改成功")


@router.post("/logout", response_model=MessageResponse)
async def logout(
    request: Request,
    user: dict = Depends(get_current_active_user)
):
    """
    用戶登出
    
    記錄登出事件（實際令牌失效由前端處理）
    """
    log_security_event("USER_LOGOUT", request=request, user_id=user["user_id"], details={
        "username": user["username"]
    })
    
    return MessageResponse(message="登出成功")


@router.post("/validate-token", response_model=MessageResponse)
async def validate_token(
    user: dict = Depends(get_current_active_user)
):
    """
    驗證令牌是否有效
    
    用於前端檢查令牌有效性
    """
    return MessageResponse(message="令牌有效")
