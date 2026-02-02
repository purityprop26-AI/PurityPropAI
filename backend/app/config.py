from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # API Configuration
    groq_api_key: Optional[str] = None
    
    # Database Configuration
    database_url: str = "mongodb+srv://naveenkumart949_db_user:VmMnHAV49sjgyu68@cluster0.dch6vry.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
    database_name: str = "real_estate_ai"
    
    # Application Settings
    app_name: str = "Tamil Nadu Real Estate AI Assistant"
    debug: bool = True
    
    cors_origins: list = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
        "https://purity-prop-b.vercel.app",
        "https://*.vercel.app",
        "https://puritypropai.onrender.com",  # Render Frontend
        "https://purityprop.onrender.com",    # Render Frontend (alternative)
    ]
    
    # LLM Settings
    llm_model: str = "llama-3.1-8b-instant"
    llm_temperature: float = 0.7
    llm_max_tokens: int = 1024
    
    # JWT Authentication
    jwt_secret_key: str = "your-secret-key-change-this-in-production-min-32-chars"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30  # 30 minutes
    refresh_token_expire_minutes: int = 10080  # 7 days
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"


# Global settings instance
settings = Settings()
