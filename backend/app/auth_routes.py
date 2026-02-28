"""
Authentication Routes (Supabase Auth version)
Only /auth/me endpoint remains — register, login, refresh are all handled
by Supabase directly from the frontend.
"""

from fastapi import APIRouter, Depends
from app.schemas import UserResponse
from app.auth_legacy import get_current_user


router = APIRouter(tags=["authentication"])


# ---------------- CURRENT USER ----------------
@router.get("/auth/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    """
    Returns the current authenticated user's info.
    Token is verified via Supabase GoTrue API.
    """
    return UserResponse(
        id=str(current_user["id"]),
        email=current_user["email"],
        name=current_user["name"],
        created_at=current_user["created_at"],
    )
