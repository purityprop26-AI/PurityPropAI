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
    version="1.0.0"
)

# ✅ CORS MUST BE HERE (Backend responsibility)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",                     # local dev
        "https://purity-prop-f-git-main-naveens-projects-36f95ce0.vercel.app"    # frontend on vercel
        "https://purity-prop-f.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Explicit OPTIONS handler (FIXES preflight failure)
@app.options("/{path:path}")
async def options_handler(path: str):
    return {}


# ✅ Routers
app.include_router(auth_router, prefix="/api/auth")

app.include_router(router)

# ✅ Health / Root endpoint
@app.get("/")
def root():
    return {
        "message": "Tamil Nadu Real Estate AI Assistant API",
        "status": "active",
        "docs": "/docs"
    }
