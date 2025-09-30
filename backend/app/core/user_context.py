"""
User Context - Simple user context management for API requests.
This provides a foundation for future authentication system integration.
"""
from typing import Optional
from fastapi import Header, HTTPException


async def get_current_user_id(
    x_user_id: Optional[str] = Header(None, description="User ID from client (temporary)")
) -> int:
    """
    Get current user ID from request headers.
    
    For now, this accepts an optional X-User-ID header or defaults to user_id=1.
    In production, this should be replaced with proper JWT/OAuth authentication.
    
    Args:
        x_user_id: Optional user ID from X-User-ID header
        
    Returns:
        int: User ID (defaults to 1 if not provided)
        
    TODO: Replace with proper authentication system:
        - JWT token validation
        - OAuth2 integration
        - Session management
    """
    if x_user_id:
        try:
            user_id = int(x_user_id)
            if user_id <= 0:
                raise ValueError("User ID must be positive")
            return user_id
        except (ValueError, TypeError):
            raise HTTPException(
                status_code=400,
                detail="Invalid X-User-ID header. Must be a positive integer."
            )
    
    # Default to user_id=1 for backward compatibility
    # TODO: Remove this default once authentication is implemented
    return 1


def get_default_user_id() -> int:
    """
    Get the default user ID for operations that don't have user context.
    
    Returns:
        int: Default user ID (1)
        
    TODO: Remove this once all operations have proper user context
    """
    return 1
