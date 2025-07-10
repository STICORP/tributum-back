"""Async database engine and session lifecycle management.

This module implements comprehensive database connection management using
SQLAlchemy's async capabilities, providing efficient connection pooling,
session lifecycle handling, and observability features.

Core functionality:
- **Connection pooling**: Configurable pool with overflow and recycling
- **Session factory**: Async session creation with proper cleanup
- **Health checks**: Database connectivity validation for monitoring
- **Query monitoring**: Performance tracking and slow query detection
- **Event listeners**: Custom hooks for query execution metrics

Advanced features:
- **Pool pre-ping**: Validates connections before use
- **Connection recycling**: Prevents stale connections (1-hour default)
- **Command timeout**: Prevents hanging queries (60-second default)
- **Weak references**: Memory-efficient query timing storage
- **Sanitized logging**: Secure parameter logging for debugging

The module uses a singleton pattern through _DatabaseManager to ensure
a single engine instance across the application lifecycle, maximizing
connection pool efficiency.
"""

import threading
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any
from weakref import WeakKeyDictionary

from loguru import logger
from sqlalchemy import event, text
from sqlalchemy.engine import Connection
from sqlalchemy.engine.interfaces import DBAPICursor, ExecutionContext
from sqlalchemy.exc import ArgumentError, InvalidRequestError, SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.core.config import get_settings
from src.core.context import RequestContext
from src.core.error_context import sanitize_sql_params

POOL_RECYCLE_SECONDS = 3600  # 1 hour
COMMAND_TIMEOUT_SECONDS = 60

# Store query start times for execution contexts
_query_start_times: WeakKeyDictionary[ExecutionContext, float] = WeakKeyDictionary()


def _before_cursor_execute(
    _conn: Connection,
    _cursor: DBAPICursor,
    _statement: str,
    _parameters: dict[str, Any] | list[Any] | tuple[Any, ...] | None,
    context: ExecutionContext,
    _executemany: bool,
) -> None:
    """Track query start time for performance monitoring.

    Args:
        _conn: Database connection (unused).
        _cursor: Database cursor (unused).
        _statement: SQL statement being executed (unused).
        _parameters: Query parameters (unused).
        context: SQLAlchemy execution context.
        _executemany: Whether this is an executemany operation (unused).
    """
    # Store start time in the weak dictionary
    _query_start_times[context] = time.time()


def _after_cursor_execute(
    _conn: Connection,
    _cursor: DBAPICursor,
    statement: str,
    parameters: dict[str, Any] | list[Any] | tuple[Any, ...] | None,
    context: ExecutionContext,
    executemany: bool,
) -> None:
    """Log slow queries and track query metrics.

    Args:
        _conn: Database connection (unused).
        _cursor: Database cursor (unused).
        statement: SQL statement that was executed.
        parameters: Query parameters.
        context: SQLAlchemy execution context.
        executemany: Whether this was an executemany operation.
    """
    settings = get_settings()

    # Calculate query duration
    duration_ms = 0.0
    start_time = _query_start_times.get(context)
    if start_time is not None:
        duration_ms = (time.time() - start_time) * 1000
        # Clean up the entry
        _query_start_times.pop(context, None)

    # Get rows affected
    rows_affected: int | None = getattr(_cursor, "rowcount", -1)
    if rows_affected is None:
        rows_affected = -1

    # Get current correlation ID for request tracking
    correlation_id = RequestContext.get_correlation_id()

    # Log slow queries
    if (
        settings.log_config.enable_sql_logging
        and duration_ms >= settings.log_config.slow_query_threshold_ms
    ):
        # Parameters logging - now sanitized
        sanitized_params = sanitize_sql_params(parameters)

        # Clean up the SQL statement for logging
        clean_statement = " ".join(statement.split())[:500]  # Limit length

        logger.warning(
            "Slow query detected: {}... Duration: {:.2f}ms Rows: {}",
            clean_statement[:100],
            round(duration_ms, 2),
            rows_affected,
            query=clean_statement,
            duration_ms=round(duration_ms, 2),
            rows_affected=rows_affected,
            parameters=sanitized_params,
            correlation_id=correlation_id,
            executemany=executemany,
            threshold_ms=settings.log_config.slow_query_threshold_ms,
        )


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

    # Add custom event listeners for detailed query logging if SQL logging is enabled
    if settings.log_config.enable_sql_logging:
        try:
            # Add custom event listeners for detailed query logging
            # Use the sync_engine for event listeners as they work with sync events
            event.listen(
                engine.sync_engine, "before_cursor_execute", _before_cursor_execute
            )
            event.listen(
                engine.sync_engine, "after_cursor_execute", _after_cursor_execute
            )
            logger.info("Registered custom query performance event listeners")
        except (InvalidRequestError, ArgumentError, AttributeError, TypeError) as e:
            # InvalidRequestError: Invalid event name or target type mismatch
            # ArgumentError: Invalid function arguments or listener signature
            # AttributeError: Target doesn't support event listening
            # TypeError: Invalid arguments to event.listen
            logger.warning(
                "Failed to register query performance event listeners: {}: {}",
                type(e).__name__,
                str(e),
            )

    logger.info(
        "Created database engine - pool_size: {}, max_overflow: {}, sql_logging: {}",
        db_config.pool_size,
        db_config.max_overflow,
        settings.log_config.enable_sql_logging,
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
        self._lock = threading.Lock()

    def get_engine(self) -> AsyncEngine:
        """Get or create the async engine instance.

        Returns:
            AsyncEngine: The engine instance.
        """
        if self._engine is None:
            with self._lock:
                # Double-checked locking pattern
                if self._engine is None:
                    self._engine = create_database_engine()
        return self._engine

    def get_session_factory(self) -> async_sessionmaker[AsyncSession]:
        """Get or create the async session factory.

        Returns:
            async_sessionmaker[AsyncSession]: The session factory.
        """
        if self._async_session_factory is None:
            with self._lock:
                # Double-checked locking pattern
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


async def check_database_connection() -> tuple[bool, str | None]:
    """Check if database connection is available.

    This function is used for health checks and startup validation.

    Returns:
        tuple[bool, str | None]: A tuple containing:
            - bool: True if connection successful, False otherwise
            - str | None: Error message if connection failed, None if successful

    Example:
        is_healthy, error = await check_database_connection()
        if not is_healthy:
            logger.error(f"Database unhealthy: {error}")
    """
    try:
        engine = get_engine()
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            _ = result.scalar()
    except SQLAlchemyError as e:
        return False, str(e)
    else:
        return True, None
