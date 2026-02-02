"""
Authentication utilities for JWT token handling and password hashing.
"""

from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from odmantic import AIOEngine, ObjectId
from app.config import settings
from app.database import get_engine
from app.models import User

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Bearer auth
security = HTTPBearer()


# ---------------- PASSWORDS ---------------- #

def hash_password(password: str) -> str:
    import hashlib, base64
    hashed = hashlib.sha256(password.encode()).digest()
    return pwd_context.hash(base64.b64encode(hashed).decode())


def verify_password(password: str, hashed_password: str) -> bool:
    import hashlib, base64
    hashed = hashlib.sha256(password.encode()).digest()
    return pwd_context.verify(base64.b64encode(hashed).decode(), hashed_password)


# ---------------- TOKENS ---------------- #

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=settings.refresh_token_expire_minutes)
    )
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def verify_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ---------------- CURRENT USER ---------------- #

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    engine: AIOEngine = Depends(get_engine),
) -> User:
    token = credentials.credentials
    payload = verify_token(token)

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    try:
        user = await engine.find_one(User, User.id == ObjectId(user_id))
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid user")

    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(
        HTTPBearer(auto_error=False)
    ),
    engine: AIOEngine = Depends(get_engine),
) -> Optional[User]:
    if not credentials:
        return None
    try:
        return await get_current_user(credentials, engine)
    except HTTPException:
        return None
