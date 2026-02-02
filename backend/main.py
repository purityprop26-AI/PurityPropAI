from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import router
from app.auth_routes import router as auth_router
from app.config import settings

app = FastAPI(
    title="Tamil Nadu Real Estate AI Assistant",
    version="1.0.0",
)

# ✅ CORS CONFIG (HARDCODED FOR STABILITY)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://puritypropai.onrender.com",
        "https://purityprop.onrender.com",
    ],
    allow_origin_regex="https://.*\\.vercel\\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ❌ Explicit OPTIONS handler removed to let CORSMiddleware handle preflights

# ✅ Routers
# auth_routes.py already defines /auth/*
app.include_router(auth_router, prefix="/api")

# other routes
app.include_router(router, prefix="/api")

# ✅ Health check

# ✅ Health check
@app.get("/")
def root():
    return {
        "message": "Tamil Nadu Real Estate AI Assistant API",
        "status": "active",
        "docs": "/docs",
    }

# ✅ Debug Endpoint (Temporary)
@app.get("/api/db-check")
async def db_check():
    try:
        from app.database import get_engine
        engine = get_engine()
        # Try a simple command
        await engine.client.admin.command('ping')
        return {"status": "ok", "message": "Connected to MongoDB Atlas!"}
    except Exception as e:
        import traceback
        return {
            "status": "error", 
            "error": str(e),
            "traceback": traceback.format_exc()
        }
