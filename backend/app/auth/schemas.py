"""
Auth v2 — Pydantic Schemas (Request / Response models)
"""
import re
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, field_validator


# ── Request models ─────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def validate_password_policy(cls, v: str) -> str:
        errors = []
        if len(v) < 8:
            errors.append("at least 8 characters")
        if not re.search(r"[A-Z]", v):
            errors.append("at least 1 uppercase letter")
        if not re.search(r"\d", v):
            errors.append("at least 1 number")
        if errors:
            raise ValueError("Password must contain: " + ", ".join(errors))
        return v

    @field_validator("name")
    @classmethod
    def clean_name(cls, v: str) -> str:
        return v.strip()


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1, max_length=128)


class GoogleAuthRequest(BaseModel):
    """Frontend sends the Google ID token received after OAuth consent."""
    id_token: str = Field(..., description="Google ID token from Google OAuth")


class VerifyEmailRequest(BaseModel):
    email: EmailStr
    otp: str = Field(..., min_length=6, max_length=6, pattern=r"^\d{6}$")


class ResendOTPRequest(BaseModel):
    email: EmailStr


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    email: EmailStr
    otp: str = Field(..., min_length=6, max_length=6, pattern=r"^\d{6}$")
    new_password: str = Field(..., min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        errors = []
        if not re.search(r"[A-Z]", v):
            errors.append("at least 1 uppercase letter")
        if not re.search(r"\d", v):
            errors.append("at least 1 number")
        if errors:
            raise ValueError("Password must contain: " + ", ".join(errors))
        return v


class LogoutRequest(BaseModel):
    """Optional — used to invalidate server-side refresh token if implemented."""
    pass



# ── Response models ────────────────────────────────────────────────────

class UserResponse(BaseModel):
    user_id: str
    email: str
    name: Optional[str]
    picture: Optional[str]
    provider: str
    is_verified: bool

    model_config = {"from_attributes": True}


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int     # seconds
    user: UserResponse


class MessageResponse(BaseModel):
    message: str
    success: bool = True
