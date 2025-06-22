"""Base repository pattern implementation for database operations.

This module provides a generic repository base class that implements
common CRUD operations for SQLAlchemy models using async patterns.
"""

from typing import TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import get_logger
from src.infrastructure.database.base import BaseModel

logger = get_logger(__name__)

# Type variable for generic model type
T = TypeVar("T", bound=BaseModel)


class BaseRepository[T: BaseModel]:
    """Base repository class providing common CRUD operations.

    This generic repository provides async methods for basic database
    operations on any model that inherits from BaseModel.

    Initialize the repository with a session and model class.

    Args:
        session: The async SQLAlchemy session to use for operations.
        model_class: The SQLAlchemy model class this repository manages.

    Example:
        class UserRepository(BaseRepository[User]):
            def __init__(self, session: AsyncSession) -> None:
                super().__init__(session, User)
    """

    def __init__(self, session: AsyncSession, model_class: type[T]) -> None:
        self.session = session
        self.model_class = model_class
        logger.debug(
            "Initialized repository",
            model=model_class.__name__,
        )

    async def get_by_id(self, entity_id: int) -> T | None:
        """Retrieve a model instance by its ID.

        Args:
            entity_id: The primary key ID of the model to retrieve.

        Returns:
            T | None: The model instance if found, None otherwise.
        """
        logger.debug(
            "Fetching by ID",
            model=self.model_class.__name__,
            id=entity_id,
        )

        stmt = select(self.model_class).where(self.model_class.id == entity_id)
        result = await self.session.execute(stmt)
        instance = result.scalar_one_or_none()

        if instance:
            logger.debug(
                "Found instance",
                model=self.model_class.__name__,
                id=entity_id,
            )
        else:
            logger.debug(
                "Instance not found",
                model=self.model_class.__name__,
                id=entity_id,
            )

        return instance

    async def get_all(self, skip: int = 0, limit: int = 100) -> list[T]:
        """Retrieve all model instances with pagination.

        Args:
            skip: Number of records to skip (for pagination).
            limit: Maximum number of records to return.

        Returns:
            list[T]: List of model instances.
        """
        logger.debug(
            "Fetching all with pagination",
            model=self.model_class.__name__,
            skip=skip,
            limit=limit,
        )

        stmt = (
            select(self.model_class)
            .offset(skip)
            .limit(limit)
            .order_by(self.model_class.id)
        )
        result = await self.session.execute(stmt)
        instances = list(result.scalars().all())

        logger.debug(
            "Retrieved instances",
            model=self.model_class.__name__,
            count=len(instances),
        )

        return instances

    async def create(self, obj: T) -> T:
        """Create a new model instance in the database.

        Args:
            obj: The model instance to create.

        Returns:
            T: The created model instance with populated ID and timestamps.
        """
        logger.debug(
            "Creating new instance",
            model=self.model_class.__name__,
        )

        self.session.add(obj)
        await self.session.flush()  # Flush to get the ID without committing

        # Refresh to get server-generated values (ID, timestamps)
        await self.session.refresh(obj)

        logger.info(
            "Created instance",
            model=self.model_class.__name__,
            id=obj.id,
        )

        return obj
