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


def get_default_user_id() -> int:
    """
    Get the default user ID for operations that don't have user context.
    
    Returns:
        int: Default user ID (1)
        
    Note: This should only be used for system operations, not user-specific data.
    """
    return 1
