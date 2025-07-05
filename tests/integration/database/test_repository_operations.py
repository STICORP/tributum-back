"""Integration tests for database repository operations.

This module tests the BaseRepository class with real database operations,
ensuring that all CRUD operations work correctly with PostgreSQL and
handle edge cases properly.
"""

from typing import Any

import pytest
from sqlalchemy import String, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import BaseModel
from src.infrastructure.database.repository import BaseRepository
from src.infrastructure.database.session import get_async_session


class RepositoryTestModel(BaseModel):
    """Test model for repository integration tests."""

    __tablename__ = "test_repository_model"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    value: Mapped[int] = mapped_column(nullable=False, default=0)


@pytest.fixture
async def test_repository(
    db_session: AsyncSession,
) -> BaseRepository[RepositoryTestModel]:
    """Create a test repository instance with a real database session."""
    # Create the test table using DDL text for async compatibility
    await db_session.execute(
        text(
            "CREATE TABLE IF NOT EXISTS test_repository_model ("
            "id SERIAL PRIMARY KEY, "
            "created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP, "
            "updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP, "
            "name VARCHAR(100) NOT NULL, "
            "description VARCHAR(500), "
            "value INTEGER NOT NULL DEFAULT 0"
            ")"
        )
    )
    await db_session.commit()

    return BaseRepository(db_session, RepositoryTestModel)


@pytest.fixture
async def sample_data() -> list[dict[str, Any]]:
    """Provide sample data for testing."""
    return [
        {"name": "Test Item 1", "description": "First item", "value": 100},
        {"name": "Test Item 2", "description": "Second item", "value": 200},
        {"name": "Test Item 3", "description": None, "value": 300},
        {"name": "Test Item 4", "description": "Fourth item", "value": 400},
        {"name": "Test Item 5", "description": "Fifth item", "value": 500},
    ]


@pytest.mark.integration
class TestRepositoryCreate:
    """Test repository create operations."""

    async def test_create_single_entity(
        self, test_repository: BaseRepository[RepositoryTestModel]
    ) -> None:
        """Test creating a single entity."""
        # Arrange
        entity = RepositoryTestModel(
            name="New Item", description="Test description", value=42
        )

        # Act
        created = await test_repository.create(entity)

        # Assert
        assert created.id is not None
        assert isinstance(created.id, int)
        assert created.name == "New Item"
        assert created.description == "Test description"
        assert created.value == 42
        assert created.created_at is not None
        assert created.updated_at is not None

    async def test_create_with_minimal_data(
        self, test_repository: BaseRepository[RepositoryTestModel]
    ) -> None:
        """Test creating an entity with only required fields."""
        # Arrange
        entity = RepositoryTestModel(name="Minimal Item")

        # Act
        created = await test_repository.create(entity)

        # Assert
        assert created.id is not None
        assert created.name == "Minimal Item"
        assert created.description is None
        assert created.value == 0  # Default value

    async def test_create_multiple_entities(
        self,
        test_repository: BaseRepository[RepositoryTestModel],
        sample_data: list[dict[str, Any]],
    ) -> None:
        """Test creating multiple entities in sequence."""
        # Act
        created_items = []
        for data in sample_data:
            entity = RepositoryTestModel(**data)
            created = await test_repository.create(entity)
            created_items.append(created)

        # Assert
        assert len(created_items) == len(sample_data)
        for i, item in enumerate(created_items):
            assert item.name == sample_data[i]["name"]
            assert item.description == sample_data[i]["description"]
            assert item.value == sample_data[i]["value"]


@pytest.mark.integration
class TestRepositoryRead:
    """Test repository read operations."""

    async def test_get_by_id(
        self, test_repository: BaseRepository[RepositoryTestModel]
    ) -> None:
        """Test retrieving an entity by ID."""
        # Arrange
        entity = RepositoryTestModel(name="Test Item", value=123)
        created = await test_repository.create(entity)

        # Act
        retrieved = await test_repository.get_by_id(created.id)

        # Assert
        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.name == created.name
        assert retrieved.value == created.value

    async def test_get_by_id_not_found(
        self, test_repository: BaseRepository[RepositoryTestModel]
    ) -> None:
        """Test retrieving a non-existent entity by ID."""
        # Arrange
        non_existent_id = 999999

        # Act
        result = await test_repository.get_by_id(non_existent_id)

        # Assert
        assert result is None

    async def test_get_all(
        self,
        test_repository: BaseRepository[RepositoryTestModel],
        sample_data: list[dict[str, Any]],
    ) -> None:
        """Test retrieving all entities."""
        # Arrange
        for data in sample_data:
            entity = RepositoryTestModel(**data)
            await test_repository.create(entity)

        # Act
        all_items = await test_repository.get_all()

        # Assert
        assert len(all_items) == len(sample_data)
        names = {item.name for item in all_items}
        expected_names = {data["name"] for data in sample_data}
        assert names == expected_names

    async def test_get_all_with_pagination(
        self,
        test_repository: BaseRepository[RepositoryTestModel],
        sample_data: list[dict[str, Any]],
    ) -> None:
        """Test retrieving entities with pagination."""
        # Arrange
        for data in sample_data:
            entity = RepositoryTestModel(**data)
            await test_repository.create(entity)

        # Act - First page
        page1 = await test_repository.get_all(skip=0, limit=2)

        # Assert - First page
        assert len(page1) == 2

        # Act - Second page
        page2 = await test_repository.get_all(skip=2, limit=2)

        # Assert - Second page
        assert len(page2) == 2

        # Act - Third page
        page3 = await test_repository.get_all(skip=4, limit=2)

        # Assert - Third page
        assert len(page3) == 1  # Only one item left

        # Ensure no overlap
        all_ids = {item.id for item in page1 + page2 + page3}
        assert len(all_ids) == 5  # All unique

    async def test_filter_by(
        self,
        test_repository: BaseRepository[RepositoryTestModel],
        sample_data: list[dict[str, Any]],
    ) -> None:
        """Test filtering entities by field values."""
        # Arrange
        for data in sample_data:
            entity = RepositoryTestModel(**data)
            await test_repository.create(entity)

        # Act - Filter by value
        high_value_items = await test_repository.filter_by(value=300)

        # Assert
        assert len(high_value_items) == 1
        assert high_value_items[0].value == 300

        # Act - Filter by description (including None)
        no_description = await test_repository.filter_by(description=None)

        # Assert
        assert len(no_description) == 1
        assert no_description[0].description is None

    async def test_filter_by_multiple_fields(
        self, test_repository: BaseRepository[RepositoryTestModel]
    ) -> None:
        """Test filtering by multiple fields."""
        # Arrange
        await test_repository.create(RepositoryTestModel(name="Item A", value=100))
        await test_repository.create(RepositoryTestModel(name="Item B", value=100))
        await test_repository.create(RepositoryTestModel(name="Item A", value=200))

        # Act
        filtered = await test_repository.filter_by(name="Item A", value=100)

        # Assert
        assert len(filtered) == 1
        assert filtered[0].name == "Item A"
        assert filtered[0].value == 100

    async def test_find_one_by(
        self, test_repository: BaseRepository[RepositoryTestModel]
    ) -> None:
        """Test finding a single entity by field values."""
        # Arrange
        entity = RepositoryTestModel(name="Unique Item", value=999)
        created = await test_repository.create(entity)

        # Act
        found = await test_repository.find_one_by(name="Unique Item")

        # Assert
        assert found is not None
        assert found.id == created.id
        assert found.value == 999

    async def test_find_one_by_not_found(
        self, test_repository: BaseRepository[RepositoryTestModel]
    ) -> None:
        """Test finding a non-existent entity."""
        # Act
        result = await test_repository.find_one_by(name="Non-existent")

        # Assert
        assert result is None


@pytest.mark.integration
class TestRepositoryUpdate:
    """Test repository update operations."""

    async def test_update_entity(
        self, test_repository: BaseRepository[RepositoryTestModel]
    ) -> None:
        """Test updating an entity."""
        # Arrange
        entity = RepositoryTestModel(name="Original", value=100)
        original = await test_repository.create(entity)
        original_updated_at = original.updated_at

        # Act
        updated = await test_repository.update(
            original.id, {"name": "Updated", "value": 200}
        )

        # Assert
        assert updated is not None
        assert updated.id == original.id
        assert updated.name == "Updated"
        assert updated.value == 200
        assert updated.created_at == original.created_at
        # Updated timestamp should be greater than or equal to original
        # (database timestamp precision might not capture microsecond differences)
        assert updated.updated_at >= original_updated_at

    async def test_update_partial_fields(
        self, test_repository: BaseRepository[RepositoryTestModel]
    ) -> None:
        """Test updating only some fields of an entity."""
        # Arrange
        entity = RepositoryTestModel(
            name="Original", description="Original description", value=100
        )
        original = await test_repository.create(entity)

        # Act - Update only value
        updated = await test_repository.update(original.id, {"value": 200})

        # Assert
        assert updated is not None
        assert updated.name == "Original"  # Unchanged
        assert updated.description == "Original description"  # Unchanged
        assert updated.value == 200  # Changed

    async def test_update_non_existent(
        self, test_repository: BaseRepository[RepositoryTestModel]
    ) -> None:
        """Test updating a non-existent entity."""
        # Arrange
        non_existent_id = 999999

        # Act
        result = await test_repository.update(non_existent_id, {"name": "Updated"})

        # Assert
        assert result is None


@pytest.mark.integration
class TestRepositoryDelete:
    """Test repository delete operations."""

    async def test_delete_entity(
        self, test_repository: BaseRepository[RepositoryTestModel]
    ) -> None:
        """Test deleting an entity."""
        # Arrange
        entity = RepositoryTestModel(name="To Delete", value=100)
        created = await test_repository.create(entity)

        # Act
        deleted = await test_repository.delete(created.id)

        # Assert
        assert deleted is True

        # Verify it's gone
        retrieved = await test_repository.get_by_id(created.id)
        assert retrieved is None

    async def test_delete_non_existent(
        self, test_repository: BaseRepository[RepositoryTestModel]
    ) -> None:
        """Test deleting a non-existent entity."""
        # Arrange
        non_existent_id = 999999

        # Act
        result = await test_repository.delete(non_existent_id)

        # Assert
        assert result is False


@pytest.mark.integration
class TestRepositoryUtilityMethods:
    """Test repository utility methods."""

    async def test_count(
        self,
        test_repository: BaseRepository[RepositoryTestModel],
        sample_data: list[dict[str, Any]],
    ) -> None:
        """Test counting entities."""
        # Act - Count empty repository
        initial_count = await test_repository.count()
        assert initial_count == 0

        # Arrange - Add items
        for data in sample_data:
            entity = RepositoryTestModel(**data)
            await test_repository.create(entity)

        # Act - Count after adding
        final_count = await test_repository.count()

        # Assert
        assert final_count == len(sample_data)

    async def test_count_with_filter(
        self, test_repository: BaseRepository[RepositoryTestModel]
    ) -> None:
        """Test counting entities with filter conditions."""
        # Arrange
        await test_repository.create(RepositoryTestModel(name="Item 1", value=100))
        await test_repository.create(RepositoryTestModel(name="Item 2", value=200))
        await test_repository.create(RepositoryTestModel(name="Item 3", value=100))

        # Act - Use filter_by to count
        items_with_100 = await test_repository.filter_by(value=100)
        count_100 = len(items_with_100)

        # Assert
        assert count_100 == 2

    async def test_exists(
        self, test_repository: BaseRepository[RepositoryTestModel]
    ) -> None:
        """Test checking entity existence."""
        # Arrange
        entity = RepositoryTestModel(name="Exists", value=123)
        created = await test_repository.create(entity)

        # Act & Assert - Existing entity
        assert await test_repository.exists(created.id) is True

        # Check existence using filter_by
        exists_by_name = await test_repository.filter_by(name="Exists")
        assert len(exists_by_name) > 0

        exists_by_value = await test_repository.filter_by(value=123)
        assert len(exists_by_value) > 0

        # Act & Assert - Non-existent entity
        assert await test_repository.exists(999999) is False

        not_exists_by_name = await test_repository.filter_by(name="Not Exists")
        assert len(not_exists_by_name) == 0

        not_exists_by_value = await test_repository.filter_by(value=999)
        assert len(not_exists_by_value) == 0

    async def test_exists_with_multiple_conditions(
        self, test_repository: BaseRepository[RepositoryTestModel]
    ) -> None:
        """Test checking existence with multiple conditions."""
        # Arrange
        await test_repository.create(RepositoryTestModel(name="Test", value=100))
        await test_repository.create(RepositoryTestModel(name="Test", value=200))

        # Act & Assert using filter_by
        exists_100 = await test_repository.filter_by(name="Test", value=100)
        assert len(exists_100) == 1

        not_exists_300 = await test_repository.filter_by(name="Test", value=300)
        assert len(not_exists_300) == 0


@pytest.mark.integration
class TestRepositoryTransactions:
    """Test repository transaction handling."""

    async def test_rollback_on_error(self, db_session: AsyncSession) -> None:
        """Test that transactions are rolled back on error."""
        # Create the test table first
        await db_session.execute(
            text(
                "CREATE TABLE IF NOT EXISTS test_repository_model ("
                "id SERIAL PRIMARY KEY, "
                "created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP, "
                "updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP, "
                "name VARCHAR(100) NOT NULL, "
                "description VARCHAR(500), "
                "value INTEGER NOT NULL DEFAULT 0"
                ")"
            )
        )
        await db_session.commit()

        # Create repository for checking counts
        repository = BaseRepository(db_session, RepositoryTestModel)
        initial_count = await repository.count()

        # Act & Assert - Use a new session for this test
        try:
            async with get_async_session() as session:
                # Ensure table exists in this session too
                await session.execute(
                    text(
                        "CREATE TABLE IF NOT EXISTS test_repository_model ("
                        "id SERIAL PRIMARY KEY, "
                        "created_at TIMESTAMP WITH TIME ZONE "
                        "DEFAULT CURRENT_TIMESTAMP, "
                        "updated_at TIMESTAMP WITH TIME ZONE "
                        "DEFAULT CURRENT_TIMESTAMP, "
                        "name VARCHAR(100) NOT NULL, "
                        "description VARCHAR(500), "
                        "value INTEGER NOT NULL DEFAULT 0"
                        ")"
                    )
                )
                await session.commit()

                temp_repository = BaseRepository(session, RepositoryTestModel)
                async with session.begin():
                    # Create an item
                    entity = RepositoryTestModel(name="Rollback Test", value=100)
                    await temp_repository.create(entity)

                    # Force an error
                    raise RuntimeError("Simulated error")
        except RuntimeError:
            pass  # Expected error

        # Verify rollback
        final_count = await repository.count()
        assert final_count == initial_count

    async def test_concurrent_operations(
        self, test_repository: BaseRepository[RepositoryTestModel]
    ) -> None:
        """Test handling concurrent operations."""
        # Arrange
        entity = RepositoryTestModel(name="Concurrent", value=100)
        created = await test_repository.create(entity)

        # Act - Simulate concurrent updates
        # In a real scenario, these would be from different sessions
        update1 = await test_repository.update(created.id, {"value": 200})
        update2 = await test_repository.update(created.id, {"value": 300})

        # Assert - Last update wins
        assert update1 is not None
        assert update2 is not None
        assert update2.value == 300

        # Verify final state
        final = await test_repository.get_by_id(created.id)
        assert final is not None
        assert final.value == 300


@pytest.mark.integration
class TestRepositoryComplexQueries:
    """Test repository with complex query scenarios."""

    async def test_custom_statement_execution(
        self,
        test_repository: BaseRepository[RepositoryTestModel],
        db_session: AsyncSession,
    ) -> None:
        """Test executing custom SQL statements through the repository."""
        # Arrange
        await test_repository.create(RepositoryTestModel(name="Item 1", value=150))
        await test_repository.create(RepositoryTestModel(name="Item 2", value=250))
        await test_repository.create(RepositoryTestModel(name="Item 3", value=350))

        # Act - Use custom query to find items with value > 200
        stmt = select(RepositoryTestModel).where(RepositoryTestModel.value > 200)
        result = await db_session.execute(stmt)
        high_value_items = result.scalars().all()

        # Assert
        assert len(high_value_items) == 2
        assert all(item.value > 200 for item in high_value_items)

    async def test_bulk_operations_performance(
        self, test_repository: BaseRepository[RepositoryTestModel]
    ) -> None:
        """Test performance with bulk operations."""
        # Arrange
        bulk_data = [{"name": f"Bulk Item {i}", "value": i * 10} for i in range(100)]

        # Act - Create many items
        created_items = []
        for data in bulk_data:
            entity = RepositoryTestModel(**data)
            created = await test_repository.create(entity)
            created_items.append(created)

        # Assert
        assert len(created_items) == 100

        # Test pagination with large dataset
        page_size = 20
        all_pages = []
        for offset in range(0, 100, page_size):
            page = await test_repository.get_all(skip=offset, limit=page_size)
            all_pages.extend(page)

        assert len(all_pages) == 100
        assert len({item.id for item in all_pages}) == 100  # All unique
