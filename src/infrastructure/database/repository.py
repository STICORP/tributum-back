"""Base repository pattern implementation for database operations.

This module provides a generic repository base class that implements
common CRUD operations for SQLAlchemy models using async patterns.
"""

import logging
from collections.abc import Mapping
from typing import TypeVar

from sqlalchemy import delete as sql_delete
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.constants import DEFAULT_PAGINATION_LIMIT
from src.infrastructure.database.base import BaseModel

logger = logging.getLogger(__name__)

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
        logger.debug("Initialized repository for %s", model_class.__name__)

    async def get_by_id(self, entity_id: int) -> T | None:
        """Retrieve a model instance by its ID.

        Args:
            entity_id: The primary key ID of the model to retrieve.

        Returns:
            T | None: The model instance if found, None otherwise.
        """
        logger.debug("Fetching %s by ID: %d", self.model_class.__name__, entity_id)

        stmt = select(self.model_class).where(self.model_class.id == entity_id)
        result = await self.session.execute(stmt)
        instance = result.scalar_one_or_none()

        if instance:
            logger.debug(
                "Found %s instance with ID: %d", self.model_class.__name__, entity_id
            )
        else:
            logger.debug(
                "%s instance not found with ID: %d",
                self.model_class.__name__,
                entity_id,
            )

        return instance

    async def get_all(
        self, skip: int = 0, limit: int = DEFAULT_PAGINATION_LIMIT
    ) -> list[T]:
        """Retrieve all model instances with pagination.

        Args:
            skip: Number of records to skip (for pagination).
            limit: Maximum number of records to return.

        Returns:
            list[T]: List of model instances.
        """
        logger.debug(
            "Fetching all %s with pagination - skip: %d, limit: %d",
            self.model_class.__name__,
            skip,
            limit,
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
            "Retrieved %d %s instances", len(instances), self.model_class.__name__
        )

        return instances

    async def create(self, obj: T) -> T:
        """Create a new model instance in the database.

        Args:
            obj: The model instance to create.

        Returns:
            T: The created model instance with populated ID and timestamps.
        """
        logger.debug("Creating new %s instance", self.model_class.__name__)

        self.session.add(obj)
        await self.session.flush()  # Flush to get the ID without committing

        # Refresh to get server-generated values (ID, timestamps)
        await self.session.refresh(obj)

        logger.info(
            "Created %s instance with ID: %d", self.model_class.__name__, obj.id
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
            "Updating %s instance ID %d - fields: %s",
            self.model_class.__name__,
            entity_id,
            list(data.keys()),
        )

        # First, get the instance
        instance = await self.get_by_id(entity_id)
        if not instance:
            logger.debug(
                "%s instance not found for update - ID: %d",
                self.model_class.__name__,
                entity_id,
            )
            return None

        # Update the fields
        for key, value in data.items():
            if hasattr(instance, key):
                setattr(instance, key, value)
            else:
                logger.warning(
                    "Attempted to update non-existent field '%s' on %s",
                    key,
                    self.model_class.__name__,
                )

        # Flush changes to database
        await self.session.flush()
        await self.session.refresh(instance)

        logger.info(
            "Updated %s instance ID %d - fields: %s",
            self.model_class.__name__,
            entity_id,
            list(data.keys()),
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
            "Deleting %s instance with ID: %d", self.model_class.__name__, entity_id
        )

        # Build delete statement
        stmt = sql_delete(self.model_class).where(self.model_class.id == entity_id)
        result = await self.session.execute(stmt)

        # Check if any rows were affected
        deleted = result.rowcount > 0

        if deleted:
            logger.info(
                "Deleted %s instance with ID: %d", self.model_class.__name__, entity_id
            )
        else:
            logger.debug(
                "%s instance not found for deletion - ID: %d",
                self.model_class.__name__,
                entity_id,
            )

        return deleted

    async def count(self) -> int:
        """Count all instances of the model.

        Returns:
            int: The total number of instances.
        """
        logger.debug("Counting %s instances", self.model_class.__name__)

        stmt = select(func.count()).select_from(self.model_class)
        result = await self.session.execute(stmt)
        count_value = result.scalar() or 0

        logger.debug("Counted %d %s instances", count_value, self.model_class.__name__)

        return count_value

    async def exists(self, entity_id: int) -> bool:
        """Check if a model instance exists by its ID.

        Args:
            entity_id: The primary key ID to check.

        Returns:
            bool: True if the instance exists, False otherwise.
        """
        logger.debug(
            "Checking existence of %s with ID: %d", self.model_class.__name__, entity_id
        )

        stmt = (
            select(func.count())
            .select_from(self.model_class)
            .where(self.model_class.id == entity_id)
        )
        result = await self.session.execute(stmt)
        exists_value = (result.scalar() or 0) > 0

        logger.debug(
            "Existence check result for %s with ID %d: %s",
            self.model_class.__name__,
            entity_id,
            exists_value,
        )

        return exists_value

    async def filter_by(self, **kwargs: object) -> list[T]:
        """Filter model instances by multiple conditions.

        Args:
            **kwargs: Field-value pairs to filter by.

        Returns:
            list[T]: List of model instances matching all conditions.
        """
        logger.debug(
            "Filtering %s instances with filters: %s",
            self.model_class.__name__,
            kwargs,
        )

        # Build query with all filter conditions
        stmt = select(self.model_class)
        for field, value in kwargs.items():
            if hasattr(self.model_class, field):
                stmt = stmt.where(getattr(self.model_class, field) == value)
            else:
                logger.warning(
                    "Attempted to filter by non-existent field '%s' on %s",
                    field,
                    self.model_class.__name__,
                )

        # Order by ID for consistent results
        stmt = stmt.order_by(self.model_class.id)

        result = await self.session.execute(stmt)
        instances = list(result.scalars().all())

        logger.debug(
            "Filtered %s - found %d instances with filters: %s",
            self.model_class.__name__,
            len(instances),
            kwargs,
        )

        return instances

    async def find_one_by(self, **kwargs: object) -> T | None:
        """Find the first model instance matching the given conditions.

        Args:
            **kwargs: Field-value pairs to filter by.

        Returns:
            T | None: The first matching instance if found, None otherwise.
        """
        logger.debug(
            "Finding one %s instance with filters: %s",
            self.model_class.__name__,
            kwargs,
        )

        # Build query with all filter conditions
        stmt = select(self.model_class)
        for field, value in kwargs.items():
            if hasattr(self.model_class, field):
                stmt = stmt.where(getattr(self.model_class, field) == value)
            else:
                logger.warning(
                    "Attempted to filter by non-existent field '%s' on %s",
                    field,
                    self.model_class.__name__,
                )

        # Order by ID and limit to 1 for consistent results
        stmt = stmt.order_by(self.model_class.id).limit(1)

        result = await self.session.execute(stmt)
        instance = result.scalar_one_or_none()

        if instance:
            logger.debug(
                "Found %s instance ID %d with filters: %s",
                self.model_class.__name__,
                instance.id,
                kwargs,
            )
        else:
            logger.debug(
                "%s instance not found with filters: %s",
                self.model_class.__name__,
                kwargs,
            )

        return instance
