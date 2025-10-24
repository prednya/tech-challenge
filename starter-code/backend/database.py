"""
Database configuration and session management.

This module handles async database connections using SQLModel and SQLAlchemy's
async engine. Defaults to PostgreSQL but supports SQLite (aiosqlite) for tests.
"""

import os
from typing import AsyncGenerator

from sqlmodel import SQLModel
from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine, create_async_engine
from sqlalchemy.orm import sessionmaker


# Database configuration
DATABASE_URL = os.getenv(
    "DATABASE_URL",
)


def _create_engine(url: str) -> AsyncEngine:
    echo = os.getenv("SQL_ECHO", "false").lower() == "true"
    return create_async_engine(url, echo=echo, future=True)


# Create async engine
engine: AsyncEngine = _create_engine(DATABASE_URL)

# Session factory
AsyncSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False, autoflush=False, autocommit=False
)


async def init_db() -> None:
    # Initialize database tables
    async with engine.begin() as conn:
        # Import all models to ensure they're registered
        from models import Product, SessionContext, SearchContext, CartItem  # noqa: F401

        # Create all tables
        await conn.run_sync(SQLModel.metadata.create_all)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    # FastAPI dependency to yield an async session
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


def session_factory() -> sessionmaker:
    # Expose sessionmaker for use outside dependency injection (e.g., SSE)
    return AsyncSessionLocal
