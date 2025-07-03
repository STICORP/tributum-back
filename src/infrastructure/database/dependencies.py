"""FastAPI dependency injection for database session management.

This module provides the integration between FastAPI's dependency injection
system and SQLAlchemy's async sessions, ensuring proper session lifecycle
management across HTTP requests.

Key features:
- **Automatic cleanup**: Sessions are properly closed after each request
- **Transaction management**: Auto-commit on success, rollback on error
- **Type safety**: Annotated type for clear dependency declaration
- **Async support**: Full compatibility with async route handlers

The DatabaseSession type alias provides a clean way to inject database
sessions into route handlers without repeating the Depends() pattern,
improving code readability and maintainability.
"""

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.session import get_async_session


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
