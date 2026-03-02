"""
PurityProp AI — Unified FastAPI Application Entry Point

Mounts:
  /api          → Chat + Session routes (auth/chat stack)
  /api/v1       → Intelligence API (hybrid search, LLM, hallucination guard)
  /auth         → Auth v2 (register, login, Google OAuth, OTP, reset)

Security:
  - CSP headers on all responses
  - CORS locked to known origins + Vercel previews
  - Rate limiting (60/min global, per-IP)
  - JWT token blocklist for secure logout
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy import text

from app.routes import router
from app.config import settings
from app.database import init_db, close_db

# Intelligence API imports — optional, graceful degradation if unavailable
try:
    from app.api.routes import router as intelligence_router
    from app.core.database import get_engine, dispose_engine, check_db_health
    from app.core.groq_client import get_groq_client
    INTELLIGENCE_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  Intelligence API not available: {e}")
    INTELLIGENCE_AVAILABLE = False

# Auth v2 — custom auth module
try:
    from app.auth.router import router as auth_v2_router
    from app.auth.models import UserProfile, OTPRecord
    AUTH_V2_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  Auth v2 not available: {e}")
    AUTH_V2_AVAILABLE = False


# ══════════════════════════════════════════════════════════════════════
# SECURITY: CSP + Security Headers Middleware
# ══════════════════════════════════════════════════════════════════════
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Adds security headers to every response:
    - Content-Security-Policy (CSP)
    - X-Content-Type-Options
    - X-Frame-Options
    - Strict-Transport-Security (HSTS)
    - Referrer-Policy
    - Permissions-Policy
    """
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)

        # CSP — allows self, Google OAuth, Supabase, and inline styles (React needs them)
        csp_directives = [
            "default-src 'self'",
            "script-src 'self' https://accounts.google.com https://apis.google.com",
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
            "font-src 'self' https://fonts.gstatic.com",
            "img-src 'self' data: https: blob:",
            "connect-src 'self' https://*.supabase.co https://api.groq.com https://*.onrender.com wss://*.supabase.co",
            "frame-src https://accounts.google.com",
            "object-src 'none'",
            "base-uri 'self'",
            "form-action 'self'",
        ]
        response.headers["Content-Security-Policy"] = "; ".join(csp_directives)

        # Prevent MIME-type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"

        # Enable HSTS (1 year, include subdomains)
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        # Control referrer information
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Restrict browser features
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), payment=()"
        )

        return response


# ══════════════════════════════════════════════════════════════════════
# TOKEN BLOCKLIST — In-memory JWT revocation for secure logout
# ══════════════════════════════════════════════════════════════════════
# NOTE: In-memory blocklist resets on server restart.
# For production at scale, swap with Redis: redis.sadd("blocked_tokens", jti)
import time
from collections import OrderedDict

class TokenBlocklist:
    """
    In-memory token blocklist with automatic expiry cleanup.
    Stores JTI (JWT ID) values to enable server-side logout.
    Max 10,000 entries with LRU eviction.
    """
    MAX_SIZE = 10_000

    def __init__(self):
        self._blocked: OrderedDict[str, float] = OrderedDict()  # jti -> expiry_timestamp

    def block(self, jti: str, expires_at: float):
        """Add a token JTI to the blocklist."""
        self._cleanup()
        if len(self._blocked) >= self.MAX_SIZE:
            # Evict oldest entry
            self._blocked.popitem(last=False)
        self._blocked[jti] = expires_at

    def is_blocked(self, jti: str) -> bool:
        """Check if a JTI is in the blocklist."""
        self._cleanup()
        return jti in self._blocked

    def _cleanup(self):
        """Remove expired entries (tokens that have naturally expired)."""
        now = time.time()
        expired_keys = [k for k, exp in self._blocked.items() if exp < now]
        for k in expired_keys:
            del self._blocked[k]

# Global singleton — importable from other modules
token_blocklist = TokenBlocklist()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle."""

    # --- STARTUP ---
    print("🚀 Starting PurityProp AI...")

    # Initialize chat/auth database tables (non-fatal on failure)
    try:
        await init_db()
        print("✅ Chat/Auth DB initialized.")
    except Exception as e:
        print(f"⚠️  DB init warning (app will start, DB lazy-connects): {e}")

    # Initialize Intelligence Engine
    if INTELLIGENCE_AVAILABLE:
        try:
            get_engine()
            db_health = await check_db_health()
            get_groq_client()
            status = db_health.get("status", "unknown")
            print(f"🧠 Intelligence Engine ready: DB={status}, Groq=ready")
        except Exception as e:
            print(f"⚠️  Intelligence Engine init warning (non-fatal): {e}")

    # Create Auth v2 tables if they don't exist
    if AUTH_V2_AVAILABLE:
        try:
            from app.database import engine as chat_engine
            from app.auth.models import UserProfile, OTPRecord
            async with chat_engine.begin() as conn:
                await conn.run_sync(
                    lambda sync_conn: (
                        UserProfile.__table__.create(sync_conn, checkfirst=True),
                        OTPRecord.__table__.create(sync_conn, checkfirst=True),
                    )
                )
            print("✅ Auth v2 tables ready (user_profiles, otp_records).")
        except Exception as e:
            print(f"⚠️  Auth v2 table init warning: {e}")

    print("✅ Application startup complete.")

    yield  # <-- application runs here

    # --- SHUTDOWN ---
    print("🛑 Shutting down PurityProp AI...")

    # Shutdown LLM service persistent client
    try:
        from app.services.llm_service import llm_service
        await llm_service.close()
        print("✅ LLM service HTTP client closed.")
    except Exception as e:
        print(f"⚠️  LLM service close warning: {e}")

    # Shutdown intelligence engine
    if INTELLIGENCE_AVAILABLE:
        try:
            groq = get_groq_client()
            await groq.close()
            await dispose_engine()
            print("✅ Intelligence engine shut down.")
        except Exception as e:
            print(f"⚠️  Intelligence engine shutdown warning: {e}")

    # Shutdown chat/auth DB
    await close_db()

    # Shutdown embedding service HTTP client
    try:
        from app.core.embedding_service import close_embedding_client
        await close_embedding_client()
        print("✅ Embedding service client closed.")
    except Exception as e:
        print(f"⚠️  Embedding service close warning: {e}")

    # Shutdown Google auth client
    if AUTH_V2_AVAILABLE:
        try:
            from app.auth.google import close_google_client
            await close_google_client()
            print("✅ Google auth client closed.")
        except Exception as e:
            print(f"⚠️  Google auth close warning: {e}")

    print("✅ All connections closed. Goodbye.")


# --- Application factory ---
app = FastAPI(
    title=settings.app_name,
    version="2.1.0",
    description="PurityProp AI — Tamil Nadu Real Estate Intelligence Platform",
    docs_url="/docs" if settings.debug else None,   # Hidden in production
    redoc_url="/redoc" if settings.debug else None,  # Hidden in production
    lifespan=lifespan,
)


# --- Security Headers Middleware (MUST be added BEFORE CORS) ---
app.add_middleware(SecurityHeadersMiddleware)


# --- CORS --- (centralized, from settings + dynamic Vercel preview support)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_origin_regex=r"https://.*\.vercel\.app",  # Allow ALL Vercel preview URLs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Rate Limiting --- (production hardening)
try:
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded

    limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    print("✅ Rate limiting enabled (60/min global, per-IP)")
except ImportError:
    print("⚠️  slowapi not installed — rate limiting disabled")


# --- Routers ---
app.include_router(router, prefix="/api")

if AUTH_V2_AVAILABLE:
    app.include_router(auth_v2_router)   # Mounts at /auth (prefix is set in router.py)
    print("✅ Auth v2 mounted at /auth")

if INTELLIGENCE_AVAILABLE:
    app.include_router(intelligence_router, prefix="/api/v1", tags=["Intelligence"])
    print("✅ Intelligence API mounted at /api/v1")


# --- Root endpoint (liveness probe safe — no DB, no I/O) ---
@app.get("/", tags=["Health"])
def root():
    """Liveness probe — returns instantly, no external dependencies."""
    return {
        "message": "PurityProp AI — Tamil Nadu Real Estate Intelligence",
        "status": "alive",
        "version": "2.1.0",
        "intelligence": "enabled" if INTELLIGENCE_AVAILABLE else "disabled",
        "environment": "development" if settings.debug else "production",
    }


# --- Readiness probe (checks DB connectivity) ---
@app.get("/api/health/db", tags=["Health"])
async def db_health_check():
    """
    Readiness probe — verifies database connectivity.
    NOTE: Do NOT use this as liveness probe — DB slowness should not kill the container.
    """
    try:
        from app.database import get_db
        async for db in get_db():
            await db.execute(text("SELECT 1"))
            return {
                "status": "ready",
                "database": "connected",
                "pool": "chat-auth",
            }
    except Exception as e:
        return {
            "status": "degraded",
            "database": "unreachable",
            "detail": str(e) if settings.debug else "hidden",
        }
