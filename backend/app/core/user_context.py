from typing import Optional
from fastapi import Header, HTTPException, Depends
from app.core.jwt_auth import get_current_active_user
async def get_current_user_id(
    user: dict = Depends(get_current_active_user)
) -> int:
    return user["user_id"]
def get_default_user_id() -> int:
    return 1
