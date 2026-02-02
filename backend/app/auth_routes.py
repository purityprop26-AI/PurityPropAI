"""
Authentication Routes
Handles user registration, login, token refresh, and user info endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from odmantic import AIOEngine, ObjectId
from app.database import get_engine
from app.models import User
from app.schemas import (
    UserCreate,
    UserLogin,
    Token,
    UserResponse,
    RefreshTokenRequest
)
from app.auth import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    get_current_user,
    verify_token,
)

router = APIRouter(tags=["authentication"])
# ❗ NO /api prefix here — handled in main.py


# ---------------- REGISTER ----------------
@router.post("/auth/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_data: UserCreate,
    engine: AIOEngine = Depends(get_engine),
):
    existing_user = await engine.find_one(User, User.email == user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    new_user = User(
        email=user_data.email,
        name=user_data.name,
        hashed_password=hash_password(user_data.password),
    )

    await engine.save(new_user)

    access_token = create_access_token(data={"sub": str(new_user.id)})
    refresh_token = create_refresh_token(data={"sub": str(new_user.id)})

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse.model_validate(new_user),
    )


# ---------------- LOGIN ----------------
@router.post("/auth/login", response_model=Token)
async def login_user(
    credentials: UserLogin,
    engine: AIOEngine = Depends(get_engine),
):
    user = await engine.find_one(User, User.email == credentials.email)
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse.model_validate(user),
    )


# ---------------- REFRESH TOKEN ----------------
@router.post("/auth/refresh", response_model=Token)
async def refresh_access_token(
    request: RefreshTokenRequest,
    engine: AIOEngine = Depends(get_engine),
):
    payload = verify_token(request.refresh_token)

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid token type")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    try:
        user = await engine.find_one(User, User.id == ObjectId(user_id))
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid user")

    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    new_access_token = create_access_token(data={"sub": user_id})

    return Token(
        access_token=new_access_token,
        refresh_token=request.refresh_token,
        user=UserResponse.model_validate(user),
    )


# ---------------- CURRENT USER ----------------
@router.get("/auth/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return UserResponse.model_validate(current_user)
