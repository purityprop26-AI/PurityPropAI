"""
Auth v2 — Google ID Token Verification

Verifies a Google ID token server-side using Google's tokeninfo endpoint.
No google-auth library required — pure httpx call.

Flow:
  Frontend → Google OAuth → receives id_token
  Frontend → POST /auth/google { id_token }
  Backend  → GET https://oauth2.googleapis.com/tokeninfo?id_token=<token>
  Google   → { sub, email, name, picture, email_verified, aud, ... }
  Backend  → validates aud (client ID) → creates/fetches user → issues JWT
"""
from __future__ import annotations

import os
from typing import Optional

import httpx
import structlog

logger = structlog.get_logger(__name__)

GOOGLE_TOKENINFO_URL = "https://oauth2.googleapis.com/tokeninfo"
GOOGLE_CLIENT_ID     = os.getenv("GOOGLE_CLIENT_ID", "")   # Must match frontend client ID

# Persistent client — avoids repeated TLS handshakes
_client: Optional[httpx.AsyncClient] = None


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(
            timeout=httpx.Timeout(8.0, connect=4.0),
            limits=httpx.Limits(max_keepalive_connections=3, max_connections=5),
        )
    return _client


async def close_google_client() -> None:
    global _client
    if _client and not _client.is_closed:
        await _client.aclose()
        _client = None


async def verify_google_token(id_token: str) -> dict:
    """
    Verify a Google ID token and return the payload.

    Returns dict with keys: sub, email, name, picture, email_verified
    Raises ValueError on any validation failure.
    """
    if not id_token:
        raise ValueError("ID token is required")

    try:
        client = _get_client()
        response = await client.get(
            GOOGLE_TOKENINFO_URL,
            params={"id_token": id_token},
        )
    except httpx.RequestError as exc:
        logger.error("google_tokeninfo_network_error", error=str(exc))
        raise ValueError("Could not reach Google servers. Try again.") from exc

    if response.status_code != 200:
        logger.warning("google_tokeninfo_rejected", status=response.status_code)
        raise ValueError("Invalid or expired Google token.")

    payload = response.json()

    # Validate audience matches our app's client ID (prevent token theft attacks)
    if GOOGLE_CLIENT_ID:
        aud = payload.get("aud", "")
        if aud != GOOGLE_CLIENT_ID:
            logger.warning("google_token_wrong_audience", aud=aud)
            raise ValueError("Google token was not issued for this application.")

    # Validate email is verified by Google
    if payload.get("email_verified") not in (True, "true"):
        raise ValueError("Google account email is not verified.")

    required = ("sub", "email")
    for field in required:
        if not payload.get(field):
            raise ValueError(f"Google token missing required field: {field}")

    logger.info(
        "google_token_verified",
        sub=payload["sub"],
        email=payload["email"],
    )

    return {
        "sub":            payload["sub"],
        "email":          payload["email"].lower().strip(),
        "name":           payload.get("name", ""),
        "picture":        payload.get("picture", ""),
        "email_verified": True,
    }
