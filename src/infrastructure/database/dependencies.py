"""Database dependencies for FastAPI.

This module provides dependency injection functions for database sessions
in FastAPI routes, ensuring proper lifecycle management and cleanup.
"""

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import get_logger, get_logger_context
from src.infrastructure.database.session import get_async_session

logger = get_logger(__name__)


async def get_db() -> AsyncGenerator[AsyncSession]:
    """Provide a database session for FastAPI dependency injection.

    This function is designed to be used with FastAPI's Depends mechanism
    to inject database sessions into route handlers. It ensures proper
    cleanup of the session after the request completes.

    Additionally tracks database query metrics in the logger context for
    aggregation at request completion.

    Yields:
        AsyncGenerator[AsyncSession]: An async SQLAlchemy session that will be
                                     automatically committed on success or rolled
                                     back on error.

    Example:
        @app.get("/users")
        async def get_users(db: DatabaseSession):
            result = await db.execute(select(User))
            return result.scalars().all()
    """
    # Initialize query metrics in logger context
    current_context = get_logger_context()

    # Initialize counters if not already present
    query_count_before = current_context.get("db_query_count", 0)
    query_duration_before = current_context.get("db_query_duration_ms", 0.0)

    async with get_async_session() as session:
        logger.debug("Providing database session for request")
        try:
            yield session
        finally:
            # Calculate metrics delta for this session
            final_context = get_logger_context()
            query_count_after = final_context.get("db_query_count", 0)
            query_duration_after = final_context.get("db_query_duration_ms", 0.0)

            # Calculate session-specific metrics
            session_query_count = query_count_after - query_count_before
            session_query_duration = query_duration_after - query_duration_before

            if session_query_count > 0:
                logger.debug(
                    "Database session dependency completed",
                    session_query_count=session_query_count,
                    session_query_duration_ms=round(session_query_duration, 2),
                )
            else:
                logger.debug("Database session dependency completed")


# Type alias for cleaner dependency injection
DatabaseSession = Annotated[AsyncSession, Depends(get_db)]
