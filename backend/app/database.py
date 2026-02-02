from motor.motor_asyncio import AsyncIOMotorClient
from odmantic import AIOEngine
from app.config import settings

# Global variables to store the client and engine
_client = None
_engine = None

def get_engine():
    """
    Return the database engine (Lazy Initialization).
    Creates the connection only when valid request comes in.
    """
    global _client, _engine
    
    if _engine is None:
        # Create MongoDB client only when needed
        _client = AsyncIOMotorClient(settings.database_url)
        _engine = AIOEngine(client=_client, database=settings.database_name)
        print("✅ MongoDB connection initialized (Lazy)")
        
    return _engine

def init_db():
    """No initialization needed for MongoDB (schemaless)."""
    pass
