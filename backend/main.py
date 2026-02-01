"""
Tamil Nadu Real Estate AI Assistant - FastAPI Backend
Main application entry point (Vercel-compatible)
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import router
from app.auth_routes import router as auth_router

app = FastAPI(
    title="Tamil Nadu Real Estate AI Assistant",
    version="1.0.0",
)

# ✅ CORS CONFIG (FIXED)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://purity-prop-f.vercel.app",
        "https://purity-prop-f-git-main-naveens-projects-36f95ce0.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Explicit OPTIONS handler (important for Vercel)
@app.options("/{path:path}")
async def options_handler(path: str):
    return {}

# ✅ Routers
# auth_routes.py already defines /auth/*
app.include_router(auth_router, prefix="/api")

# other routes
app.include_router(router, prefix="/api")

# ✅ Health check
@app.get("/")
def root():
    return {
        "message": "Tamil Nadu Real Estate AI Assistant API",
        "status": "active",
        "docs": "/docs",
    }
