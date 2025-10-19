"""
Fixed SQLAlchemy ORM Configuration for Reflex
=============================================
Reflex 이벤트 루프와 호환되도록 수정된 버전

Key Changes:
1. Lazy engine initialization
2. Background event compatible
3. No module-level async operations
"""
from __future__ import annotations

import os
import ssl
from typing import Optional, AsyncGenerator
from contextlib import asynccontextmanager
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
    AsyncEngine
)
from sqlalchemy.pool import NullPool, QueuePool
import logging
logger = logging.getLogger(__name__)

# ------------------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------------------
RAW_DSN = os.getenv(
    "TS_DSN",
    "postgresql://postgres:postgres@pgai-db:5432/ecoanp?sslmode=disable"
)

# Pool configuration
USE_POOLING = os.getenv("USE_DB_POOLING", "true").lower() == "true"
POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "20"))
MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "30"))
POOL_TIMEOUT = int(os.getenv("DB_POOL_TIMEOUT", "10"))
POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE", "3600"))

def normalize_asyncpg_url(raw: str) -> str:
    """
    asyncpg doesn't accept 'sslmode' in URL parameters
    Remove it and convert to postgresql+asyncpg://
    """
    parsed = urlparse(raw)

    # Change scheme to asyncpg
    if parsed.scheme in ("postgresql", "postgres"):
        scheme = "postgresql+asyncpg"
    elif "asyncpg" in parsed.scheme:
        scheme = parsed.scheme
    else:
        scheme = "postgresql+asyncpg"

    # Remove sslmode from query params for asyncpg
    query_params = parse_qs(parsed.query)
    query_params.pop('sslmode', None)

    # Rebuild URL
    new_query = urlencode(query_params, doseq=True) if query_params else ""
    new_url = urlunparse((
        scheme,
        parsed.netloc,
        parsed.path,
        parsed.params,
        new_query,
        parsed.fragment
    ))

    return new_url

ASYNC_URL = normalize_asyncpg_url(RAW_DSN)

# ------------------------------------------------------------------------------
# Global Engine Manager (Lazy Initialization)
# ------------------------------------------------------------------------------
class EngineManager:
    """
    Lazy engine initialization to avoid event loop conflicts
    Engine is created only when first needed
    """
    def __init__(self):
        self._engine: Optional[AsyncEngine] = None
        self._session_factory: Optional[async_sessionmaker] = None

    def get_engine(self) -> AsyncEngine:
        """Get or create engine (lazy initialization)"""
        if self._engine is None:
            # Use NullPool for Reflex - creates new connection per request
            # This avoids asyncio/greenlet compatibility issues
            logger.info("Creating async engine with NullPool for Reflex compatibility")

            self._engine = create_async_engine(
                ASYNC_URL,
                echo=False,
                poolclass=NullPool,  # CRITICAL: NullPool for Reflex compatibility
                connect_args={
                    "server_settings": {
                        "application_name": "reflex_app",
                        "jit": "off"
                    },
                    "timeout": 10,
                    "command_timeout": 10,  # Command timeout
                }
            )

            self._session_factory = async_sessionmaker(
                bind=self._engine,
                class_=AsyncSession,
                expire_on_commit=False
            )

        return self._engine

    def get_session_factory(self) -> async_sessionmaker:
        """Get session factory"""
        if self._session_factory is None:
            self.get_engine()  # Initialize engine first
        return self._session_factory

    async def close(self):
        """Close engine"""
        if self._engine is not None:
            await self._engine.dispose()
            self._engine = None
            self._session_factory = None

# Global manager instance
_manager = EngineManager()

# ------------------------------------------------------------------------------
# Public API
# ------------------------------------------------------------------------------
@asynccontextmanager
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Get async session for use in Reflex background events

    Usage in Reflex State:
    ```python
    @rx.event(background=True)  # REQUIRED!
    async def load_data(self):
        async with get_async_session() as session:
            result = await session.execute(select(Table))
            data = [row.to_dict() for row in result.scalars()]

        async with self:  # REQUIRED for state updates
            self.data = data
            yield  # Optional UI update
    ```
    """
    session_factory = _manager.get_session_factory()
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            await session.close()

def get_engine() -> AsyncEngine:
    """
    Get the async engine (for direct use if needed)
    WARNING: Usually you should use get_async_session() instead
    """
    return _manager.get_engine()

async def close_engine():
    """Close the engine and clean up connections"""
    await _manager.close()

# ------------------------------------------------------------------------------
# Test Connection
# ------------------------------------------------------------------------------
async def test_connection() -> bool:
    """Test database connection"""
    try:
        async with get_async_session() as session:
            result = await session.execute("SELECT 1")
            logger.info("Database connection successful")
            return True
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return False