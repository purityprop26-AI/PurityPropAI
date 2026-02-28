"""
PurityProp AI — Unified FastAPI Application Entry Point

Mounts:
  /api          → Chat + Session routes (auth/chat stack)
  /api          → Auth routes (Supabase auth)
  /api/v1       → Intelligence API (hybrid search, LLM, hallucination guard)

Fixes applied:
  [MED-B6]   Raw SQL now wrapped in text() — SQLAlchemy 2.x compliance
  [CRIT-B1]  LLM service shutdown registered on app teardown (async close)
  [LOW-B4]   /health and /api/health/db separated (liveness vs readiness)
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.routes import router
from app.auth_routes import router as auth_router
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
            from sqlalchemy import inspect
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

    # Shutdown LLM service persistent client (FIX: graceful async close)
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
    version="2.0.0",
    description="PurityProp AI — Tamil Nadu Real Estate Intelligence Platform",
    docs_url="/docs" if settings.debug else None,   # Hidden in production
    redoc_url="/redoc" if settings.debug else None, # Hidden in production
    lifespan=lifespan,
)


# --- CORS --- (centralized, from settings)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
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
app.include_router(auth_router, prefix="/api")
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
        "version": "2.0.0",
        "intelligence": "enabled" if INTELLIGENCE_AVAILABLE else "disabled",
        "environment": "development" if settings.debug else "production",
    }


# --- Readiness probe (checks DB connectivity) ---
@app.get("/api/health/db", tags=["Health"])
async def db_health_check():
    """
    Readiness probe — verifies database connectivity.
    FIX [MED-B6]: Raw SQL now uses text() wrapper (SQLAlchemy 2.x compliant).
    NOTE: Do NOT use this as liveness probe — DB slowness should not kill the container.
    """
    try:
        from app.database import get_db
        async for db in get_db():
            # FIX [MED-B6]: correct text() wrapper — was missing before
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
