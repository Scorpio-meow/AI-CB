"""
User Context - User context management with JWT authentication integration.
"""
from typing import Optional
from fastapi import Header, HTTPException, Depends
from app.core.jwt_auth import get_current_active_user


async def get_current_user_id(
    user: dict = Depends(get_current_active_user)
) -> int:
    """
    Get current user ID from JWT token.
    
    This extracts the user_id from the validated JWT token.
    Requires valid authentication.
    
    Args:
        user: User data from JWT token (injected by dependency)
        
    Returns:
        int: User ID from the authenticated user
    """
    return user["user_id"]


from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.security import ADMIN_API_KEY
import hmac

security_bearer = HTTPBearer(auto_error=False)

async def get_mcp_or_user_id(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer)
) -> int:
    """
    獲取使用者 ID，支援 X-API-Key (MCP 用) 或 JWT Token。
    """
    # 1. 優先驗證 X-API-Key
    if x_api_key and ADMIN_API_KEY and hmac.compare_digest(x_api_key, ADMIN_API_KEY):
        return get_default_user_id()
        
    # 2. 次要驗證 JWT Token
    if credentials:
        token = credentials.credentials
        try:
            from app.core.jwt_auth import TokenManager
            payload = TokenManager.decode_token(token)
            if TokenManager.verify_token_type(payload, "access"):
                return payload["user_id"]
        except Exception:
            pass

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="認證失敗：無效的 X-API-Key 或 JWT Token",
        headers={"WWW-Authenticate": "Bearer/ApiKey"}
    )


def get_default_user_id() -> int:
    """
    Get the default user ID for operations that don't have user context.
    
    Returns:
        int: Default user ID (1)
        
    Note: This should only be used for system operations, not user-specific data.
    """
    return 1
