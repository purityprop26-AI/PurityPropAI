from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import router
from app.auth_routes import router as auth_router
from app.config import settings

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    docs_url="/docs" if settings.debug else None,
    redoc_url=None,
)

# ✅ CENTRALIZED CORS CONFIGURATION
# Loaded dynamically from verified settings
origins = settings.get_cors_origins()

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Routers
app.include_router(auth_router, prefix="/api")
app.include_router(router, prefix="/api")

# ✅ Health check
@app.get("/")
def root():
    return {
        "message": "Tamil Nadu Real Estate AI Assistant API",
        "status": "active",
        "environment": "development" if settings.debug else "production"
    }

# ✅ Database Connection Check
@app.get("/api/health/db")
async def db_health_check():
    """
    Verifies database connectivity without exposing secrets.
    """
    try:
        from app.database import get_engine
        engine = get_engine()
        # Perform a lightweight command to verify connection
        await engine.client.admin.command('ping')
        return {"status": "ok", "message": "Database connected"}
    except Exception:
        # Do not expose error details in production
        return {"status": "error", "message": "Database connection failed"}
