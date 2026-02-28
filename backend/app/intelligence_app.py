"""
SUPABASE-NATIVE REAL ESTATE INTELLIGENCE SYSTEM
Main FastAPI Application Entry Point
"""
import time
import structlog
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.database import get_engine, dispose_engine, check_db_health
from app.core.groq_client import get_groq_client
from app.api.routes import router as api_router

# Configure structured logging
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(
        structlog.get_config()["wrapper_class"]._default_level
        if hasattr(structlog.get_config().get("wrapper_class", None), "_default_level")
        else 20  # INFO
    ),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management."""
    settings = get_settings()

    # Startup
    logger.info(
        "app_starting",
        env=settings.app_env,
        debug=settings.debug,
    )

    # Initialize database engine (triggers pool creation)
    engine = get_engine()
    logger.info("database_engine_initialized")

    # Verify DB health
    db_health = await check_db_health()
    if db_health["status"] == "healthy":
        logger.info("database_health_check_passed", extensions=db_health.get("extensions"))
    else:
        logger.error("database_health_check_failed", error=db_health.get("error"))

    # Initialize Groq client
    groq = get_groq_client()
    logger.info("groq_client_initialized", model=settings.groq_model)

    logger.info("app_started_successfully")

    yield

    # Shutdown
    logger.info("app_shutting_down")
    await groq.close()
    await dispose_engine()
    logger.info("app_shutdown_complete")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        description="Supabase-Native Real Estate Intelligence System with hybrid retrieval, "
                    "deterministic financial microservices, and zero-hallucination enforcement.",
        version="1.0.0",
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Request timing middleware
    @app.middleware("http")
    async def add_timing_header(request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        elapsed = time.perf_counter() - start
        response.headers["X-Process-Time-Ms"] = f"{elapsed * 1000:.2f}"
        response.headers["X-Request-Id"] = request.headers.get(
            "X-Request-Id", str(id(request))
        )
        return response

    # Global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(
            "unhandled_exception",
            path=str(request.url),
            method=request.method,
            error=str(exc),
        )
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal Server Error",
                "detail": str(exc) if settings.debug else "An unexpected error occurred",
            },
        )

    # Include routes
    app.include_router(api_router, prefix="/api/v1", tags=["Intelligence"])

    # Root endpoint
    @app.get("/", tags=["Root"])
    async def root():
        return {
            "service": settings.app_name,
            "version": "1.0.0",
            "status": "operational",
            "docs": "/docs" if settings.debug else "disabled",
        }

    return app


# Application instance
app = create_app()
