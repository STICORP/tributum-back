"""Unit tests for repository CRUD operations."""

from datetime import UTC, datetime

import pytest
import pytest_check
from pytest_mock import MockerFixture
from sqlalchemy import String
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import BaseModel
from src.infrastructure.database.repository import BaseRepository

from .conftest import ModelForRepositoryTesting


@pytest.mark.unit
@pytest.mark.asyncio
class TestRepositoryCRUD:
    """Test cases for BaseRepository CRUD operations."""

    async def test_init(self, mock_session: AsyncSession) -> None:
        """Test repository initialization."""
        repo = BaseRepository(mock_session, ModelForRepositoryTesting)
        assert repo.session is mock_session
        assert repo.model_class is ModelForRepositoryTesting

    async def test_get_by_id_found(
        self,
        test_repository: BaseRepository[ModelForRepositoryTesting],
        mock_session: AsyncSession,
        mocker: MockerFixture,
    ) -> None:
        """Test get_by_id when the instance exists."""
        # Create a test instance
        test_instance = ModelForRepositoryTesting(
            id=1,
            name="Test Item",
            description="Test Description",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        # Mock the query result
        mock_result = mocker.MagicMock()
        mock_result.scalar_one_or_none.return_value = test_instance
        mock_execute = mocker.patch.object(
            mock_session, "execute", mocker.AsyncMock(return_value=mock_result)
        )

        # Call the method
        result = await test_repository.get_by_id(1)

        # Verify the result with soft assertions
        with pytest_check.check:
            assert result is test_instance
        with pytest_check.check:
            assert result is not None  # Type guard for pyright
        with pytest_check.check:
            assert result.id == 1
        with pytest_check.check:
            assert result.name == "Test Item"

        # Verify the query was executed
        mock_execute.assert_called_once()

    async def test_get_by_id_not_found(
        self,
        test_repository: BaseRepository[ModelForRepositoryTesting],
        mock_session: AsyncSession,
        mocker: MockerFixture,
    ) -> None:
        """Test get_by_id when the instance doesn't exist."""
        # Mock empty result
        mock_result = mocker.MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_execute = mocker.patch.object(
            mock_session, "execute", mocker.AsyncMock(return_value=mock_result)
        )

        # Call the method
        result = await test_repository.get_by_id(999)

        # Verify the result is None
        assert result is None

        # Verify the query was executed
        mock_execute.assert_called_once()

    async def test_create_success(
        self,
        test_repository: BaseRepository[ModelForRepositoryTesting],
        mock_session: AsyncSession,
        mocker: MockerFixture,
    ) -> None:
        """Test successful creation of a new instance."""
        # Create a new instance without ID
        new_instance = ModelForRepositoryTesting(
            name="New Item", description="New Description"
        )

        # Mock the session methods
        def set_id() -> None:
            new_instance.id = 42

        def set_timestamps(obj: ModelForRepositoryTesting) -> None:
            obj.created_at = datetime.now(UTC)
            obj.updated_at = datetime.now(UTC)

        mock_add = mocker.patch.object(mock_session, "add", mocker.MagicMock())
        mock_flush = mocker.patch.object(
            mock_session, "flush", mocker.AsyncMock(side_effect=set_id)
        )
        mock_refresh = mocker.patch.object(
            mock_session, "refresh", mocker.AsyncMock(side_effect=set_timestamps)
        )

        # Call the method
        result = await test_repository.create(new_instance)

        # Verify the result with soft assertions
        with pytest_check.check:
            assert result is new_instance
        with pytest_check.check:
            assert result.id == 42
        with pytest_check.check:
            assert result.name == "New Item"
        with pytest_check.check:
            assert result.description == "New Description"
        with pytest_check.check:
            assert result.created_at is not None
        with pytest_check.check:
            assert result.updated_at is not None

        # Verify the session methods were called
        mock_add.assert_called_once()
        mock_flush.assert_called_once()
        mock_refresh.assert_called_once()

    async def test_create_with_minimal_data(
        self,
        test_repository: BaseRepository[ModelForRepositoryTesting],
        mock_session: AsyncSession,
        mocker: MockerFixture,
    ) -> None:
        """Test creation with only required fields."""
        # Create instance with only required fields
        new_instance = ModelForRepositoryTesting(name="Minimal Item")

        # Mock the session methods
        def set_id() -> None:
            new_instance.id = 100

        def set_timestamps(obj: ModelForRepositoryTesting) -> None:
            obj.created_at = datetime.now(UTC)
            obj.updated_at = datetime.now(UTC)

        mocker.patch.object(mock_session, "add", mocker.MagicMock())
        mocker.patch.object(mock_session, "flush", mocker.AsyncMock(side_effect=set_id))
        mocker.patch.object(
            mock_session, "refresh", mocker.AsyncMock(side_effect=set_timestamps)
        )

        # Call the method
        result = await test_repository.create(new_instance)

        # Verify the result with soft assertions
        with pytest_check.check:
            assert result.id == 100
        with pytest_check.check:
            assert result.name == "Minimal Item"
        with pytest_check.check:
            assert result.description is None  # Optional field
        with pytest_check.check:
            assert result.created_at is not None
        with pytest_check.check:
            assert result.updated_at is not None

    async def test_repository_with_different_model(
        self, mock_session: AsyncSession, mocker: MockerFixture
    ) -> None:
        """Test that repository works with different model types."""

        class AnotherModel(BaseModel):
            """Another test model."""

            __tablename__ = "another_test_model"
            title: Mapped[str] = mapped_column(String(200))

        # Create repository for different model
        repo = BaseRepository(mock_session, AnotherModel)

        # Create instance
        instance = AnotherModel(title="Another Test")

        # Mock the session methods
        def set_id() -> None:
            instance.id = 1

        def set_timestamps(obj: BaseModel) -> None:
            obj.created_at = datetime.now(UTC)
            obj.updated_at = datetime.now(UTC)

        mocker.patch.object(mock_session, "add", mocker.MagicMock())
        mocker.patch.object(mock_session, "flush", mocker.AsyncMock(side_effect=set_id))
        mocker.patch.object(
            mock_session, "refresh", mocker.AsyncMock(side_effect=set_timestamps)
        )

        # Create the instance
        result = await repo.create(instance)

        # Verify it works with different model
        assert isinstance(result, AnotherModel)
        assert result.title == "Another Test"
        assert result.id == 1

    async def test_update_success(
        self,
        test_repository: BaseRepository[ModelForRepositoryTesting],
        mock_session: AsyncSession,
        mocker: MockerFixture,
    ) -> None:
        """Test successful update of an existing instance."""
        # Create an existing instance
        existing_instance = ModelForRepositoryTesting(
            id=1,
            name="Original Name",
            description="Original Description",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        # Mock get_by_id to return the existing instance
        mock_get_by_id = mocker.patch.object(
            test_repository,
            "get_by_id",
            mocker.AsyncMock(return_value=existing_instance),
        )

        # Mock session methods
        def update_timestamps(obj: ModelForRepositoryTesting) -> None:
            obj.updated_at = datetime.now(UTC)

        mock_flush = mocker.patch.object(mock_session, "flush", mocker.AsyncMock())
        mock_refresh = mocker.patch.object(
            mock_session, "refresh", mocker.AsyncMock(side_effect=update_timestamps)
        )

        # Update data
        update_data = {"name": "Updated Name", "description": "Updated Description"}

        # Call the method
        result = await test_repository.update(1, update_data)

        # Verify the result with soft assertions
        with pytest_check.check:
            assert result is not None
        with pytest_check.check:
            assert result.id == 1
        with pytest_check.check:
            assert result.name == "Updated Name"
        with pytest_check.check:
            assert result.description == "Updated Description"
        with pytest_check.check:
            assert result.updated_at > existing_instance.created_at

        # Verify methods were called
        mock_get_by_id.assert_called_once_with(1)
        mock_flush.assert_called_once()
        mock_refresh.assert_called_once()

    async def test_update_partial_data(
        self,
        test_repository: BaseRepository[ModelForRepositoryTesting],
        mock_session: AsyncSession,
        mocker: MockerFixture,
    ) -> None:
        """Test update with partial data (only some fields)."""
        # Create an existing instance
        existing_instance = ModelForRepositoryTesting(
            id=1,
            name="Original Name",
            description="Original Description",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        # Mock get_by_id
        mocker.patch.object(
            test_repository,
            "get_by_id",
            mocker.AsyncMock(return_value=existing_instance),
        )

        # Mock session methods
        mocker.patch.object(mock_session, "flush", mocker.AsyncMock())
        mocker.patch.object(mock_session, "refresh", mocker.AsyncMock())

        # Update only name
        update_data = {"name": "Updated Name Only"}

        # Call the method
        result = await test_repository.update(1, update_data)

        # Verify partial update
        assert result is not None
        assert result.name == "Updated Name Only"
        assert result.description == "Original Description"  # Unchanged

    async def test_update_not_found(
        self,
        test_repository: BaseRepository[ModelForRepositoryTesting],
        mocker: MockerFixture,
    ) -> None:
        """Test update when instance doesn't exist."""
        # Mock get_by_id to return None
        mocker.patch.object(
            test_repository, "get_by_id", mocker.AsyncMock(return_value=None)
        )

        # Call the method
        result = await test_repository.update(999, {"name": "New Name"})

        # Verify result is None
        assert result is None

    async def test_update_with_nonexistent_field(
        self,
        test_repository: BaseRepository[ModelForRepositoryTesting],
        mock_session: AsyncSession,
        mocker: MockerFixture,
    ) -> None:
        """Test update with a field that doesn't exist on the model."""
        # Create an existing instance
        existing_instance = ModelForRepositoryTesting(
            id=1,
            name="Original Name",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        # Mock get_by_id
        mocker.patch.object(
            test_repository,
            "get_by_id",
            mocker.AsyncMock(return_value=existing_instance),
        )

        # Mock session methods
        mocker.patch.object(mock_session, "flush", mocker.AsyncMock())
        mocker.patch.object(mock_session, "refresh", mocker.AsyncMock())

        # Update with non-existent field
        update_data = {"name": "Updated Name", "nonexistent_field": "Value"}

        # Call the method
        result = await test_repository.update(1, update_data)

        # Verify update succeeded for valid fields
        assert result is not None
        assert result.name == "Updated Name"
        # The nonexistent field should be ignored with a warning logged

    async def test_delete_success(
        self,
        test_repository: BaseRepository[ModelForRepositoryTesting],
        mock_session: AsyncSession,
        mocker: MockerFixture,
    ) -> None:
        """Test successful deletion of an instance."""
        # Mock the execute result
        mock_result = mocker.MagicMock()
        mock_result.rowcount = 1  # One row deleted

        mock_execute = mocker.patch.object(
            mock_session, "execute", mocker.AsyncMock(return_value=mock_result)
        )

        # Call the method
        result = await test_repository.delete(1)

        # Verify deletion was successful
        assert result is True
        mock_execute.assert_called()

    async def test_delete_not_found(
        self,
        test_repository: BaseRepository[ModelForRepositoryTesting],
        mock_session: AsyncSession,
        mocker: MockerFixture,
    ) -> None:
        """Test deletion when instance doesn't exist."""
        # Mock the execute result
        mock_result = mocker.MagicMock()
        mock_result.rowcount = 0  # No rows deleted

        mocker.patch.object(
            mock_session, "execute", mocker.AsyncMock(return_value=mock_result)
        )

        # Call the method
        result = await test_repository.delete(999)

        # Verify deletion failed
        assert result is False
