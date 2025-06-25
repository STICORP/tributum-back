"""Database session management for async SQLAlchemy.

This module provides the async engine and session factory configuration
for the Tributum application, with proper connection pooling and cleanup.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.core.config import get_settings
from src.core.logging import get_logger
from src.infrastructure.constants import COMMAND_TIMEOUT_SECONDS, POOL_RECYCLE_SECONDS

logger = get_logger(__name__)


def create_database_engine(database_url: str | None = None) -> AsyncEngine:
    """Create an async SQLAlchemy engine with connection pooling.

    Args:
        database_url: Optional database URL. If not provided, uses the
                     configured database URL from settings.

    Returns:
        AsyncEngine: Configured async engine instance.
    """
    settings = get_settings()
    db_config = settings.database_config

    # Use provided URL or fall back to configuration
    url = database_url or db_config.database_url

    # Create engine with configuration from settings
    engine = create_async_engine(
        url,
        pool_size=db_config.pool_size,
        max_overflow=db_config.max_overflow,
        pool_timeout=db_config.pool_timeout,
        pool_pre_ping=db_config.pool_pre_ping,
        echo=db_config.echo,
        # Additional performance and reliability settings
        pool_recycle=POOL_RECYCLE_SECONDS,
        connect_args={
            "server_settings": {
                "jit": "off"
            },  # Disable JIT for more predictable performance
            "command_timeout": COMMAND_TIMEOUT_SECONDS,
        },
    )

    logger.info(
        "Created database engine",
        pool_size=db_config.pool_size,
        max_overflow=db_config.max_overflow,
        pool_timeout=db_config.pool_timeout,
        pool_pre_ping=db_config.pool_pre_ping,
    )

    return engine


class _DatabaseManager:
    """Internal class to manage database engine and session factory instances.

    This class provides a singleton pattern without using global statements,
    which is preferred by our linting rules.
    """

    def __init__(self) -> None:
        self._engine: AsyncEngine | None = None
        self._async_session_factory: async_sessionmaker[AsyncSession] | None = None

    def get_engine(self) -> AsyncEngine:
        """Get or create the async engine instance.

        Returns:
            AsyncEngine: The engine instance.
        """
        if self._engine is None:
            self._engine = create_database_engine()
        return self._engine

    def get_session_factory(self) -> async_sessionmaker[AsyncSession]:
        """Get or create the async session factory.

        Returns:
            async_sessionmaker[AsyncSession]: The session factory.
        """
        if self._async_session_factory is None:
            engine = self.get_engine()
            self._async_session_factory = async_sessionmaker(
                engine,
                class_=AsyncSession,
                expire_on_commit=False,  # Don't expire objects after commit
            )
            logger.info("Created async session factory")
        return self._async_session_factory

    async def close(self) -> None:
        """Close the database engine and cleanup connections."""
        if self._engine is not None:
            await self._engine.dispose()
            logger.info("Database engine disposed")
            self._engine = None
            self._async_session_factory = None

    def reset(self) -> None:
        """Reset the manager state. Used primarily for testing."""
        self._engine = None
        self._async_session_factory = None


# Singleton instance
_db_manager = _DatabaseManager()


def get_engine() -> AsyncEngine:
    """Get or create the global async engine instance.

    This function ensures a single engine instance is used throughout
    the application lifecycle for proper connection pooling.

    Returns:
        AsyncEngine: The global engine instance.
    """
    return _db_manager.get_engine()


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Get or create the global async session factory.

    This function ensures a single session factory is used throughout
    the application lifecycle.

    Returns:
        async_sessionmaker[AsyncSession]: The global session factory.
    """
    return _db_manager.get_session_factory()


@asynccontextmanager
async def get_async_session() -> AsyncGenerator[AsyncSession]:
    """Get an async database session with automatic cleanup.

    This async generator provides a database session that is automatically
    cleaned up after use. The session is committed on success or rolled back
    on error.

    Yields:
        AsyncGenerator[AsyncSession]: Database session for performing operations.

    Raises:
        Exception: Any exception that occurs during session usage is re-raised
                  after rollback and cleanup.

    Example:
        async with get_async_session() as session:
            result = await session.execute(select(User))
            users = result.scalars().all()
    """
    async_session_factory = get_session_factory()
    async with async_session_factory() as session:
        logger.debug("Created new database session")
        try:
            yield session
            await session.commit()
            logger.debug("Database session committed successfully")
        except Exception:
            await session.rollback()
            logger.debug("Database session rolled back due to error")
            raise
        finally:
            await session.close()
            logger.debug("Database session closed")


async def close_database() -> None:
    """Close the database engine and cleanup connections.

    This should be called during application shutdown to ensure
    all database connections are properly closed.
    """
    await _db_manager.close()
