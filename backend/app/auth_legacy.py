"""
Authentication Utilities — Supabase JWT Token Verification

FIX [MED-B4]: Replaced per-request httpx.AsyncClient creation with a module-level
              persistent client. Eliminates ~100-200ms TLS handshake overhead per request.
              Client is kept alive with connection pooling and TTL from Supabase.

Security model:
  - JWT tokens issued by Supabase GoTrue
  - Verified against Supabase /auth/v1/user endpoint
  - Token must be Bearer token in Authorization header
"""

import httpx
from fastapi import HTTPException, Header
from app.config import settings

# Supabase auth verification endpoint
SUPABASE_AUTH_URL = f"{settings.supabase_url}/auth/v1/user"

# FIX [MED-B4]: Persistent AsyncClient — reuses TCP connections across requests.
# Replaces the previous pattern of: async with httpx.AsyncClient() as client: ...
# which created a new TLS connection on every single auth check.
_auth_client = httpx.AsyncClient(
    timeout=httpx.Timeout(10.0, connect=3.0),
    limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
    headers={
        "apikey": settings.supabase_anon_key,
    },
)


async def verify_supabase_token(authorization: str = Header(...)) -> dict:
    """
    Verify Supabase JWT token by calling GoTrue /auth/v1/user.

    Args:
        authorization: Bearer token from Authorization header

    Returns:
        User dict with id, email, name, created_at

    Raises:
        HTTPException 401 if token is invalid or missing
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header format")

    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(status_code=401, detail="Missing authentication token")

    try:
        # FIX [MED-B4]: Reuses existing TCP connection — no new TLS handshake
        response = await _auth_client.get(
            SUPABASE_AUTH_URL,
            headers={"Authorization": f"Bearer {token}"},
        )

        if response.status_code == 401:
            raise HTTPException(status_code=401, detail="Token expired or invalid")
        if response.status_code != 200:
            raise HTTPException(
                status_code=401,
                detail=f"Auth verification failed: {response.status_code}"
            )

        user_data = response.json()
        return {
            "id": user_data.get("id"),
            "email": user_data.get("email"),
            "name": (
                user_data.get("user_metadata", {}).get("name")
                or user_data.get("email", "").split("@")[0]
            ),
            "created_at": str(user_data.get("created_at", "")),
        }

    except HTTPException:
        raise
    except httpx.TimeoutException:
        raise HTTPException(status_code=503, detail="Authentication service timeout")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Token verification error: {str(e)}")


async def get_current_user(authorization: str = Header(...)) -> dict:
    """
    FastAPI dependency that returns the current authenticated user.
    Alias of verify_supabase_token for cleaner route signatures.
    """
    return await verify_supabase_token(authorization)


async def close_auth_client():
    """Gracefully close the persistent auth HTTP client on shutdown."""
    await _auth_client.aclose()
