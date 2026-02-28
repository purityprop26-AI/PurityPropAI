"""
Database Configuration for PostgreSQL (Supabase) — Chat/Auth Stack

FIX [CRIT-B2]: Pool size reduced (pool_size=3, max_overflow=5 → total 8).
Combined with intelligence pool (pool_size=5, max_overflow=10 → total 15),
grand total = 23 active connections max. Well within Supabase free tier (60 limit).
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.config import settings

# FIX [CRIT-B2]: Reduced from pool_size=5, max_overflow=10 (total 15)
#                to pool_size=3, max_overflow=5 (total 8).
#                Chat/auth stack handles lower concurrency than intelligence API.
engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_size=3,
    max_overflow=5,
    pool_pre_ping=True,
    pool_recycle=1800,   # Recycle connections after 30 min (prevents stale SSL connections)
    connect_args={
        "ssl": "require",
        "server_settings": {
            "application_name": "PurityPropAI-Chat",
            "statement_timeout": "30000",  # 30s max per statement
        },
    },
)

# Session factory
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db():
    """
    Dependency that provides a database session.
    Automatically closes session after request.
    """
    async with async_session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """
    Create all tables in the database.
    Called on application startup.
    """
    from app.models import User, ChatSession, ChatMessage  # noqa: F401
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ PostgreSQL chat/auth tables created/verified")


async def close_db():
    """Close the database engine on shutdown."""
    await engine.dispose()
    print("✅ PostgreSQL chat/auth connection pool closed")
