from pydantic_settings import BaseSettings
from typing import List, Optional
import os

class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    CRITICAL SECURITY NOTICE:
    - NO defaults for secrets.
    - Application will FAIL TO START if secrets are missing.
    """
    
    # API Configuration
    groq_api_key: str  # REQUIRED: No default
    
    # Database Configuration
    database_url: str  # REQUIRED: No default
    database_name: str = "real_estate_ai"
    
    # Application Settings
    app_name: str = "Tamil Nadu Real Estate AI Assistant"
    debug: bool = False  # Default to False for safety
    
    # CORS Configuration
    # Default to restrictive, overwrite via env var in production
    cors_origins: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
        "https://purity-prop-f.vercel.app",  # Old Vercel URL
        "https://purity-prop-ai.vercel.app", # Current Vercel URL
        "https://puritypropai-9ri1.onrender.com", # Backend self-reference
        "https://puritypropai.onrender.com", # Backend alternate
        "https://purityprop.com",            # Custom Domain
        "https://www.purityprop.com",        # Custom Domain (WWW)
    ]
    
    # LLM Settings
    llm_model: str = "llama-3.1-8b-instant"
    llm_temperature: float = 0.7
    llm_max_tokens: int = 1024
    
    # JWT Authentication
    jwt_secret_key: str  # REQUIRED: No default
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_minutes: int = 10080  # 7 days
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"
        # Parse comma-separated strings for lists
        env_file_encoding = "utf-8"

    def get_cors_origins(self) -> List[str]:
        """
        Safe CORS origin retrieval.
        Allows adding origins via parsing a separate env var if needed, 
        or just relying on the list above.
        """
        # If we have a comma-separated string in env, parse it
        env_origins = os.getenv("ADDITIONAL_CORS_ORIGINS")
        origins = self.cors_origins.copy()
        if env_origins:
            origins.extend([origin.strip() for origin in env_origins.split(",") if origin.strip()])
        return origins

# Global settings instance
try:
    settings = Settings()
except Exception as e:
    # Fail fast if configuration is invalid
    import sys
    print(f"CRITICAL: Configuration validation failed: {e}")
    print("Ensure all required environment variables are set.")
    sys.exit(1)
