"""
SUPABASE-NATIVE REAL ESTATE INTELLIGENCE SYSTEM
Async Database Engine — SQLAlchemy + asyncpg
"""
import structlog
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from app.core.config import get_settings

logger = structlog.get_logger(__name__)


class Base(DeclarativeBase):
    """SQLAlchemy declarative base."""
    pass


# Global engine and session factory
_engine = None
_session_factory = None


def get_engine():
    """Get or create the async engine with connection pooling."""
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(
            settings.database_url,
            pool_size=settings.db_pool_size,
            max_overflow=settings.db_max_overflow,
            pool_timeout=settings.db_pool_timeout,
            pool_recycle=settings.db_pool_recycle,
            pool_pre_ping=True,
            echo=settings.db_echo,
            connect_args={
                "ssl": "require",
                "server_settings": {
                    "hnsw.iterative_scan": "relaxed_order",
                    "statement_timeout": "30000",
                },
            },
        )
        logger.info(
            "async_engine_created",
            pool_size=settings.db_pool_size,
            max_overflow=settings.db_max_overflow,
        )
    return _engine


def get_session_factory():
    """Get or create the async session factory."""
    global _session_factory
    if _session_factory is None:
        engine = get_engine()
        _session_factory = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
    return _session_factory


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for database sessions."""
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    """Context manager for database sessions outside of FastAPI."""
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def check_db_health() -> dict:
    """Check database connectivity and extension status."""
    try:
        async with get_db_context() as session:
            # Basic connectivity
            result = await session.execute(text("SELECT 1"))
            result.scalar()

            # Extensions
            ext_result = await session.execute(
                text("SELECT extname FROM pg_extension ORDER BY extname")
            )
            extensions = [row[0] for row in ext_result.fetchall()]

            # pgvector test
            await session.execute(text("SELECT '[1,2,3]'::vector"))

            # PostGIS test
            postgis_ver = await session.execute(text("SELECT PostGIS_Version()"))
            postgis_version = postgis_ver.scalar()

            return {
                "status": "healthy",
                "extensions": extensions,
                "postgis_version": postgis_version,
                "pgvector": True,
            }
    except Exception as e:
        logger.error("db_health_check_failed", error=str(e))
        return {"status": "unhealthy", "error": str(e)}


async def dispose_engine():
    """Dispose of the engine on shutdown."""
    global _engine, _session_factory
    if _engine:
        await _engine.dispose()
        _engine = None
        _session_factory = None
        logger.info("async_engine_disposed")
