"""
Auth v2 — Security Primitives
Covers: bcrypt password hashing, JWT issuance/validation, OTP generation
"""
from __future__ import annotations

import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

from jose import JWTError, jwt
from passlib.context import CryptContext

# ── Config ─────────────────────────────────────────────────────────────
JWT_SECRET   = os.getenv("JWT_SECRET_KEY", "change-me-in-production")
JWT_ALGO     = "HS256"
ACCESS_TTL   = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))   # minutes

# passlib context — bcrypt with sensible rounds (12 is good balance of speed/security)
_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)


# ══════════════════════════════════════════════════════════════════════
# PASSWORD
# ══════════════════════════════════════════════════════════════════════

def hash_password(plain: str) -> str:
    """bcrypt-hash a plaintext password."""
    return _pwd_ctx.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Constant-time password comparison."""
    return _pwd_ctx.verify(plain, hashed)


# ══════════════════════════════════════════════════════════════════════
# JWT
# ══════════════════════════════════════════════════════════════════════

def create_access_token(
    user_id: str,
    email: str,
    provider: str,
    is_verified: bool,
) -> Tuple[str, int]:
    """
    Issue a signed JWT.
    Returns (token, expires_in_seconds).
    """
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=ACCESS_TTL)
    payload = {
        "sub":         user_id,
        "email":       email,
        "provider":    provider,
        "is_verified": is_verified,
        "iat":         int(now.timestamp()),
        "exp":         int(expire.timestamp()),
        "jti":         secrets.token_hex(16),   # unique token ID (for future revocation)
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)
    return token, ACCESS_TTL * 60


def decode_access_token(token: str) -> Optional[dict]:
    """
    Decode and verify JWT.
    Returns payload dict on success, None on failure.
    """
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])
    except JWTError:
        return None


# ══════════════════════════════════════════════════════════════════════
# OTP
# ══════════════════════════════════════════════════════════════════════

def generate_otp() -> Tuple[str, str]:
    """
    Generate a cryptographically secure 6-digit OTP.
    Returns (otp_plaintext, sha256_hex_digest).

    SHA-256 is used (not bcrypt) because:
    - OTPs are short-lived (10 min)
    - OTPs are already high-entropy random numbers
    - bcrypt would add unnecessary latency
    """
    otp_plain = f"{secrets.randbelow(900_000) + 100_000:06d}"
    otp_hash  = hashlib.sha256(otp_plain.encode()).hexdigest()
    return otp_plain, otp_hash


def verify_otp(otp_plain: str, stored_hash: str) -> bool:
    """Constant-time comparison of OTP against stored hash."""
    candidate_hash = hashlib.sha256(otp_plain.encode()).hexdigest()
    return secrets.compare_digest(candidate_hash, stored_hash)


# ══════════════════════════════════════════════════════════════════════
# BEARER EXTRACTION
# ══════════════════════════════════════════════════════════════════════

def extract_bearer(authorization: str) -> Optional[str]:
    """Parse 'Bearer <token>' header safely."""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    return authorization[7:].strip() or None
