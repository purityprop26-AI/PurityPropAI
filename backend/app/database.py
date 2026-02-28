"""
Database Configuration for PostgreSQL (Supabase) — Chat/Auth Stack

FIX [CRIT-B2]: Pool size reduced (pool_size=3, max_overflow=5 → total 8).
Combined with intelligence pool (pool_size=5, max_overflow=10 → total 15),
grand total = 23 active connections max. Well within Supabase free tier (60 limit).
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.config import settings

import ssl as _ssl

# Build SSL context that works with both direct and pooler Supabase connections
try:
    ssl_context = _ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = _ssl.CERT_NONE
    _connect_args = {"ssl": ssl_context}
except Exception:
    _connect_args = {"ssl": "require"}

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
    connect_args=_connect_args,
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
