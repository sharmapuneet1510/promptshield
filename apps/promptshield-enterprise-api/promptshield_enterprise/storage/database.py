"""
SQLAlchemy async database setup and dependency injection.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from promptshield_enterprise.settings import get_settings

# Module-level engine and session factory (initialized on first use or via init_db)
_engine = None
_session_factory = None


def get_engine():
    """Return the async SQLAlchemy engine, creating it if needed."""
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(
            settings.DATABASE_URL,
            echo=settings.is_development,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
        )
    return _engine


def get_session_factory():
    """Return the async session factory."""
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _session_factory


class Base(DeclarativeBase):
    """SQLAlchemy declarative base for all ORM models."""
    pass


async def init_db() -> None:
    """
    Create all database tables if they don't exist.

    In production, use Alembic migrations instead of this function.
    This is provided for development convenience.
    """
    from promptshield_enterprise.storage import models  # noqa: F401 - registers models

    async with get_engine().begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that yields an async database session.

    Usage::

        @router.get("/")
        async def endpoint(db: AsyncSession = Depends(get_db)):
            ...
    """
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
