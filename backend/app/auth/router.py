"""
Auth v2 — FastAPI Router
Mounts at /auth — all 7 endpoints with proper HTTP status codes.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import service
from app.auth.schemas import (
    AuthResponse, ForgotPasswordRequest, GoogleAuthRequest, LoginRequest,
    MessageResponse, RegisterRequest, ResendOTPRequest,
    ResetPasswordRequest, UserResponse, VerifyEmailRequest,
)

from app.auth.security import decode_access_token, extract_bearer
from app.database import async_session_factory


router = APIRouter(prefix="/auth", tags=["Authentication v2"])


# ── Dependency: DB session ─────────────────────────────────────────────
async def get_db():
    async with async_session_factory() as db:
        try:
            yield db
        except Exception:
            await db.rollback()
            raise
        finally:
            await db.close()


# ── Dependency: Authenticated user ─────────────────────────────────────
async def get_current_user(request: Request) -> dict:
    """Extract and validate JWT from Authorization header."""
    token = extract_bearer(request.headers.get("authorization", ""))
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload


def _client_ip(request: Request) -> str:
    """Extract real client IP (handles reverse proxy X-Forwarded-For)."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


# ══════════════════════════════════════════════════════════════════════
# POST /auth/register
# ══════════════════════════════════════════════════════════════════════
@router.post(
    "/register",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register with email + password",
    responses={
        400: {"description": "Validation error / duplicate email"},
        429: {"description": "Rate limit exceeded"},
    },
)
async def register(
    request: Request,
    body: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await service.register(body, _client_ip(request), db)
        return MessageResponse(message=result["message"])
    except PermissionError as e:
        raise HTTPException(status_code=429, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ══════════════════════════════════════════════════════════════════════
# POST /auth/verify-email
# ══════════════════════════════════════════════════════════════════════
@router.post(
    "/verify-email",
    response_model=AuthResponse,
    summary="Verify email with 6-digit OTP",
    responses={
        400: {"description": "Invalid OTP"},
        404: {"description": "User not found"},
        429: {"description": "Too many attempts"},
    },
)
async def verify_email(
    body: VerifyEmailRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await service.verify_email(body, db)
    except PermissionError as e:
        raise HTTPException(status_code=429, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ══════════════════════════════════════════════════════════════════════
# POST /auth/resend-otp
# ══════════════════════════════════════════════════════════════════════
@router.post(
    "/resend-otp",
    response_model=MessageResponse,
    summary="Resend OTP verification code",
    responses={
        429: {"description": "Rate limit exceeded"},
    },
)
async def resend_otp(
    body: ResendOTPRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await service.resend_otp(body, db)
        return MessageResponse(message=result["message"])
    except PermissionError as e:
        raise HTTPException(status_code=429, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ══════════════════════════════════════════════════════════════════════
# POST /auth/login
# ══════════════════════════════════════════════════════════════════════
@router.post(
    "/login",
    response_model=AuthResponse,
    summary="Login with email + password",
    responses={
        401: {"description": "Invalid credentials"},
        403: {"description": "Email not verified"},
        429: {"description": "Too many attempts"},
    },
)
async def login(
    request: Request,
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await service.login(body, _client_ip(request), db)
    except PermissionError as e:
        code = 429 if "Too many" in str(e) else 403
        raise HTTPException(status_code=code, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


# ══════════════════════════════════════════════════════════════════════
# POST /auth/google
# ══════════════════════════════════════════════════════════════════════
@router.post(
    "/google",
    response_model=AuthResponse,
    summary="Authenticate with Google OAuth ID token",
    responses={
        400: {"description": "Invalid Google token"},
    },
)
async def google_auth(
    body: GoogleAuthRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await service.google_auth(body, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ══════════════════════════════════════════════════════════════════════
# POST /auth/logout
# ══════════════════════════════════════════════════════════════════════
@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Logout (stateless JWT — client must discard token)",
)
async def logout(current_user: dict = Depends(get_current_user)):
    # JWT is stateless — logout is client-side (discard token).
    # Future: add token to a blocklist/Redis set here.
    return MessageResponse(message="Logged out successfully.")


# ══════════════════════════════════════════════════════════════════════
# GET /auth/me
# ══════════════════════════════════════════════════════════════════════
@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get authenticated user profile",
    responses={
        401: {"description": "Not authenticated"},
        404: {"description": "User not found"},
    },
)
async def get_me(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await service.get_me(current_user["sub"], db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ══════════════════════════════════════════════════════════════
# POST /auth/forgot-password
# ══════════════════════════════════════════════════════════════
@router.post(
    "/forgot-password",
    response_model=MessageResponse,
    summary="Request a password reset OTP via email",
    responses={
        429: {"description": "Rate limit exceeded"},
    },
)
async def forgot_password(
    body: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await service.forgot_password(body, db)
        return MessageResponse(message=result["message"])
    except PermissionError as e:
        raise HTTPException(status_code=429, detail=str(e))


# ══════════════════════════════════════════════════════════════
# POST /auth/reset-password
# ══════════════════════════════════════════════════════════════
@router.post(
    "/reset-password",
    response_model=MessageResponse,
    summary="Reset password using OTP from email",
    responses={
        400: {"description": "Invalid OTP or expired"},
        429: {"description": "Too many attempts"},
    },
)
async def reset_password(
    body: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await service.reset_password(body, db)
        return MessageResponse(message=result["message"])
    except PermissionError as e:
        raise HTTPException(status_code=429, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
