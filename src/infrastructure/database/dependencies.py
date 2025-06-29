"""Database dependencies for FastAPI.

This module provides dependency injection functions for database sessions
in FastAPI routes, ensuring proper lifecycle management and cleanup.
"""

import logging
from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.session import get_async_session

logger = logging.getLogger(__name__)


async def get_db() -> AsyncGenerator[AsyncSession]:
    """Provide a database session for FastAPI dependency injection.

    This function is designed to be used with FastAPI's Depends mechanism
    to inject database sessions into route handlers. It ensures proper
    cleanup of the session after the request completes.

    Session lifecycle is managed automatically - committed on success,
    rolled back on error.

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
    async with get_async_session() as session:
        logger.debug("Providing database session for request")
        try:
            yield session
        finally:
            logger.debug("Database session dependency completed")


# Type alias for cleaner dependency injection
DatabaseSession = Annotated[AsyncSession, Depends(get_db)]
