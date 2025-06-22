"""Base repository pattern implementation for database operations.

This module provides a generic repository base class that implements
common CRUD operations for SQLAlchemy models using async patterns.
"""

from collections.abc import Mapping
from typing import TypeVar

from sqlalchemy import delete as sql_delete
from sqlalchemy import func, select
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

    async def update(self, entity_id: int, data: Mapping[str, object]) -> T | None:
        """Update a model instance by its ID with partial data.

        Args:
            entity_id: The primary key ID of the model to update.
            data: Dictionary of fields to update.

        Returns:
            T | None: The updated model instance if found, None otherwise.
        """
        logger.debug(
            "Updating instance",
            model=self.model_class.__name__,
            id=entity_id,
            fields=list(data.keys()),
        )

        # First, get the instance
        instance = await self.get_by_id(entity_id)
        if not instance:
            logger.debug(
                "Instance not found for update",
                model=self.model_class.__name__,
                id=entity_id,
            )
            return None

        # Update the fields
        for key, value in data.items():
            if hasattr(instance, key):
                setattr(instance, key, value)
            else:
                logger.warning(
                    "Attempted to update non-existent field",
                    model=self.model_class.__name__,
                    field=key,
                )

        # Flush changes to database
        await self.session.flush()
        await self.session.refresh(instance)

        logger.info(
            "Updated instance",
            model=self.model_class.__name__,
            id=entity_id,
            updated_fields=list(data.keys()),
        )

        return instance

    async def delete(self, entity_id: int) -> bool:
        """Delete a model instance by its ID.

        Args:
            entity_id: The primary key ID of the model to delete.

        Returns:
            bool: True if the instance was deleted, False if not found.
        """
        logger.debug(
            "Deleting instance",
            model=self.model_class.__name__,
            id=entity_id,
        )

        # Build delete statement
        stmt = sql_delete(self.model_class).where(self.model_class.id == entity_id)
        result = await self.session.execute(stmt)

        # Check if any rows were affected
        deleted = result.rowcount > 0

        if deleted:
            logger.info(
                "Deleted instance",
                model=self.model_class.__name__,
                id=entity_id,
            )
        else:
            logger.debug(
                "Instance not found for deletion",
                model=self.model_class.__name__,
                id=entity_id,
            )

        return deleted

    async def count(self) -> int:
        """Count all instances of the model.

        Returns:
            int: The total number of instances.
        """
        logger.debug(
            "Counting instances",
            model=self.model_class.__name__,
        )

        stmt = select(func.count()).select_from(self.model_class)
        result = await self.session.execute(stmt)
        count_value = result.scalar() or 0

        logger.debug(
            "Counted instances",
            model=self.model_class.__name__,
            count=count_value,
        )

        return count_value

    async def exists(self, entity_id: int) -> bool:
        """Check if a model instance exists by its ID.

        Args:
            entity_id: The primary key ID to check.

        Returns:
            bool: True if the instance exists, False otherwise.
        """
        logger.debug(
            "Checking existence",
            model=self.model_class.__name__,
            id=entity_id,
        )

        stmt = (
            select(func.count())
            .select_from(self.model_class)
            .where(self.model_class.id == entity_id)
        )
        result = await self.session.execute(stmt)
        exists_value = (result.scalar() or 0) > 0

        logger.debug(
            "Existence check result",
            model=self.model_class.__name__,
            id=entity_id,
            exists=exists_value,
        )

        return exists_value
