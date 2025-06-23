"""Unit tests for the base repository implementation."""

from datetime import UTC, datetime
from typing import cast
from unittest.mock import MagicMock

import pytest
import pytest_check
from pytest_mock import MockerFixture
from sqlalchemy import String
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import BaseModel
from src.infrastructure.database.repository import BaseRepository


class ModelForRepositoryTesting(BaseModel):
    """Test model for repository testing."""

    __tablename__ = "model_repository_testing"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)


@pytest.fixture
def mock_session(mocker: MockerFixture) -> MagicMock:
    """Create a properly mocked async session."""
    mock = mocker.MagicMock(spec=AsyncSession)
    return cast("MagicMock", mock)


@pytest.fixture
def test_repository(
    mock_session: MagicMock,
) -> BaseRepository[ModelForRepositoryTesting]:
    """Create a test repository instance."""
    return BaseRepository(cast("AsyncSession", mock_session), ModelForRepositoryTesting)


@pytest.mark.unit
@pytest.mark.asyncio
class TestBaseRepository:
    """Test cases for BaseRepository class."""

    async def test_init(self, mock_session: MagicMock) -> None:
        """Test repository initialization."""
        repo = BaseRepository(
            cast("AsyncSession", mock_session), ModelForRepositoryTesting
        )
        assert repo.session is cast("AsyncSession", mock_session)
        assert repo.model_class is ModelForRepositoryTesting

    async def test_get_by_id_found(
        self,
        test_repository: BaseRepository[ModelForRepositoryTesting],
        mock_session: MagicMock,
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
        mocker.patch.object(
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
        mock_session.execute.assert_called_once()

    async def test_get_by_id_not_found(
        self,
        test_repository: BaseRepository[ModelForRepositoryTesting],
        mock_session: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        """Test get_by_id when the instance doesn't exist."""
        # Mock empty result
        mock_result = mocker.MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mocker.patch.object(
            mock_session, "execute", mocker.AsyncMock(return_value=mock_result)
        )

        # Call the method
        result = await test_repository.get_by_id(999)

        # Verify the result is None
        assert result is None

        # Verify the query was executed
        mock_session.execute.assert_called_once()

    async def test_get_all_with_results(
        self,
        test_repository: BaseRepository[ModelForRepositoryTesting],
        mock_session: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        """Test get_all with multiple results."""
        # Create test instances
        test_instances = [
            ModelForRepositoryTesting(
                id=i,
                name=f"Test Item {i}",
                description=f"Description {i}",
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            for i in range(1, 4)
        ]

        # Mock the query result chain
        mock_scalars = mocker.MagicMock()
        mock_scalars.all.return_value = test_instances

        mock_result = mocker.MagicMock()
        mock_result.scalars.return_value = mock_scalars

        mocker.patch.object(
            mock_session, "execute", mocker.AsyncMock(return_value=mock_result)
        )

        # Call the method
        result = await test_repository.get_all(skip=0, limit=10)

        # Verify the result
        assert len(result) == 3
        assert all(isinstance(item, ModelForRepositoryTesting) for item in result)
        assert result[0].id == 1
        assert result[0].name == "Test Item 1"

        # Verify the query was executed
        mock_session.execute.assert_called_once()

    async def test_get_all_with_pagination(
        self,
        test_repository: BaseRepository[ModelForRepositoryTesting],
        mock_session: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        """Test get_all with skip and limit parameters."""
        # Create test instances
        test_instances = [
            ModelForRepositoryTesting(
                id=i,
                name=f"Test Item {i}",
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            for i in range(11, 16)  # IDs 11-15
        ]

        # Mock the query result chain
        mock_scalars = mocker.MagicMock()
        mock_scalars.all.return_value = test_instances

        mock_result = mocker.MagicMock()
        mock_result.scalars.return_value = mock_scalars

        mocker.patch.object(
            mock_session, "execute", mocker.AsyncMock(return_value=mock_result)
        )

        # Call the method with pagination
        result = await test_repository.get_all(skip=10, limit=5)

        # Verify the result
        assert len(result) == 5
        assert result[0].id == 11

        # Verify the query was executed
        mock_session.execute.assert_called_once()

    async def test_get_all_empty_result(
        self,
        test_repository: BaseRepository[ModelForRepositoryTesting],
        mock_session: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        """Test get_all when no results are found."""
        # Mock empty result chain
        mock_scalars = mocker.MagicMock()
        mock_scalars.all.return_value = []

        mock_result = mocker.MagicMock()
        mock_result.scalars.return_value = mock_scalars

        mocker.patch.object(
            mock_session, "execute", mocker.AsyncMock(return_value=mock_result)
        )

        # Call the method
        result = await test_repository.get_all()

        # Verify empty list is returned
        assert result == []
        assert isinstance(result, list)

    async def test_create_success(
        self,
        test_repository: BaseRepository[ModelForRepositoryTesting],
        mock_session: MagicMock,
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

        mocker.patch.object(mock_session, "add", mocker.MagicMock())
        mocker.patch.object(mock_session, "flush", mocker.AsyncMock(side_effect=set_id))
        mocker.patch.object(
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
        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()
        mock_session.refresh.assert_called_once()

    async def test_create_with_minimal_data(
        self,
        test_repository: BaseRepository[ModelForRepositoryTesting],
        mock_session: MagicMock,
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
        self, mock_session: MagicMock, mocker: MockerFixture
    ) -> None:
        """Test that repository works with different model types."""

        class AnotherModel(BaseModel):
            """Another test model."""

            __tablename__ = "another_test_model"
            title: Mapped[str] = mapped_column(String(200))

        # Create repository for different model
        repo = BaseRepository(cast("AsyncSession", mock_session), AnotherModel)

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
        mock_session: MagicMock,
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

        mocker.patch.object(mock_session, "flush", mocker.AsyncMock())
        mocker.patch.object(
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
        mock_session.flush.assert_called_once()
        mock_session.refresh.assert_called_once()

    async def test_update_partial_data(
        self,
        test_repository: BaseRepository[ModelForRepositoryTesting],
        mock_session: MagicMock,
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
        mock_session: MagicMock,
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
        mock_session: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        """Test successful deletion of an instance."""
        # Mock the execute result
        mock_result = mocker.MagicMock()
        mock_result.rowcount = 1  # One row deleted

        mocker.patch.object(
            mock_session, "execute", mocker.AsyncMock(return_value=mock_result)
        )

        # Call the method
        result = await test_repository.delete(1)

        # Verify deletion was successful
        assert result is True
        mock_session.execute.assert_called()

    async def test_delete_not_found(
        self,
        test_repository: BaseRepository[ModelForRepositoryTesting],
        mock_session: MagicMock,
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

    async def test_count_with_instances(
        self,
        test_repository: BaseRepository[ModelForRepositoryTesting],
        mock_session: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        """Test count when instances exist."""
        # Mock the execute result
        mock_result = mocker.MagicMock()
        mock_result.scalar.return_value = 5

        mocker.patch.object(
            mock_session, "execute", mocker.AsyncMock(return_value=mock_result)
        )

        # Call the method
        result = await test_repository.count()

        # Verify count
        assert result == 5
        mock_session.execute.assert_called()

    async def test_count_empty_table(
        self,
        test_repository: BaseRepository[ModelForRepositoryTesting],
        mock_session: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        """Test count when no instances exist."""
        # Mock the execute result
        mock_result = mocker.MagicMock()
        mock_result.scalar.return_value = 0

        mocker.patch.object(
            mock_session, "execute", mocker.AsyncMock(return_value=mock_result)
        )

        # Call the method
        result = await test_repository.count()

        # Verify count is 0
        assert result == 0

    async def test_count_with_none_result(
        self,
        test_repository: BaseRepository[ModelForRepositoryTesting],
        mock_session: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        """Test count when database returns None."""
        # Mock the execute result
        mock_result = mocker.MagicMock()
        mock_result.scalar.return_value = None

        mocker.patch.object(
            mock_session, "execute", mocker.AsyncMock(return_value=mock_result)
        )

        # Call the method
        result = await test_repository.count()

        # Verify count defaults to 0
        assert result == 0

    async def test_exists_true(
        self,
        test_repository: BaseRepository[ModelForRepositoryTesting],
        mock_session: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        """Test exists when instance exists."""
        # Mock the execute result
        mock_result = mocker.MagicMock()
        mock_result.scalar.return_value = 1

        mocker.patch.object(
            mock_session, "execute", mocker.AsyncMock(return_value=mock_result)
        )

        # Call the method
        result = await test_repository.exists(1)

        # Verify exists is True
        assert result is True
        mock_session.execute.assert_called()

    async def test_exists_false(
        self,
        test_repository: BaseRepository[ModelForRepositoryTesting],
        mock_session: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        """Test exists when instance doesn't exist."""
        # Mock the execute result
        mock_result = mocker.MagicMock()
        mock_result.scalar.return_value = 0

        mocker.patch.object(
            mock_session, "execute", mocker.AsyncMock(return_value=mock_result)
        )

        # Call the method
        result = await test_repository.exists(999)

        # Verify exists is False
        assert result is False

    async def test_exists_with_none_result(
        self,
        test_repository: BaseRepository[ModelForRepositoryTesting],
        mock_session: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        """Test exists when database returns None."""
        # Mock the execute result
        mock_result = mocker.MagicMock()
        mock_result.scalar.return_value = None

        mocker.patch.object(
            mock_session, "execute", mocker.AsyncMock(return_value=mock_result)
        )

        # Call the method
        result = await test_repository.exists(1)

        # Verify exists is False
        assert result is False

    async def test_filter_by_single_condition(
        self,
        test_repository: BaseRepository[ModelForRepositoryTesting],
        mock_session: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        """Test filter_by with a single condition."""
        # Create test instances with same name
        test_instances = [
            ModelForRepositoryTesting(
                id=1,
                name="Test Name",
                description="Description 1",
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            ),
            ModelForRepositoryTesting(
                id=2,
                name="Test Name",
                description="Description 2",
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            ),
            ModelForRepositoryTesting(
                id=3,
                name="Other Name",
                description="Description 3",
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            ),
        ]

        # Mock the query result - only instances with "Test Name"
        filtered_instances = [test_instances[0], test_instances[1]]
        mock_scalars = mocker.MagicMock()
        mock_scalars.all.return_value = filtered_instances

        mock_result = mocker.MagicMock()
        mock_result.scalars.return_value = mock_scalars

        mocker.patch.object(
            mock_session, "execute", mocker.AsyncMock(return_value=mock_result)
        )

        # Call the method
        result = await test_repository.filter_by(name="Test Name")

        # Verify the result
        assert len(result) == 2
        assert all(item.name == "Test Name" for item in result)
        assert result[0].id == 1
        assert result[1].id == 2

        # Verify the query was executed
        mock_session.execute.assert_called_once()

    async def test_filter_by_multiple_conditions(
        self,
        test_repository: BaseRepository[ModelForRepositoryTesting],
        mock_session: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        """Test filter_by with multiple conditions."""
        # Create test instance matching both conditions
        test_instance = ModelForRepositoryTesting(
            id=1,
            name="Test Name",
            description="Specific Description",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        # Mock the query result
        mock_scalars = mocker.MagicMock()
        mock_scalars.all.return_value = [test_instance]

        mock_result = mocker.MagicMock()
        mock_result.scalars.return_value = mock_scalars

        mocker.patch.object(
            mock_session, "execute", mocker.AsyncMock(return_value=mock_result)
        )

        # Call the method with multiple conditions
        result = await test_repository.filter_by(
            name="Test Name", description="Specific Description"
        )

        # Verify the result with soft assertions
        with pytest_check.check:
            assert len(result) == 1
        with pytest_check.check:
            assert result[0].name == "Test Name"
        with pytest_check.check:
            assert result[0].description == "Specific Description"
        with pytest_check.check:
            assert result[0].id == 1

        # Verify the query was executed
        mock_session.execute.assert_called_once()

    async def test_filter_by_no_matches(
        self,
        test_repository: BaseRepository[ModelForRepositoryTesting],
        mock_session: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        """Test filter_by when no instances match."""
        # Mock empty result
        mock_scalars = mocker.MagicMock()
        mock_scalars.all.return_value = []

        mock_result = mocker.MagicMock()
        mock_result.scalars.return_value = mock_scalars

        mocker.patch.object(
            mock_session, "execute", mocker.AsyncMock(return_value=mock_result)
        )

        # Call the method
        result = await test_repository.filter_by(name="Non-existent Name")

        # Verify empty list is returned
        assert result == []
        assert isinstance(result, list)

    async def test_filter_by_with_nonexistent_field(
        self,
        test_repository: BaseRepository[ModelForRepositoryTesting],
        mock_session: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        """Test filter_by with a field that doesn't exist on the model."""
        # Mock empty result (since invalid field won't match)
        mock_scalars = mocker.MagicMock()
        mock_scalars.all.return_value = []

        mock_result = mocker.MagicMock()
        mock_result.scalars.return_value = mock_scalars

        mocker.patch.object(
            mock_session, "execute", mocker.AsyncMock(return_value=mock_result)
        )

        # Call the method with non-existent field
        result = await test_repository.filter_by(
            name="Test Name", nonexistent_field="Value"
        )

        # Verify result (warning should be logged for invalid field)
        assert result == []

    async def test_find_one_by_single_condition(
        self,
        test_repository: BaseRepository[ModelForRepositoryTesting],
        mock_session: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        """Test find_one_by with a single condition."""
        # Create test instance
        test_instance = ModelForRepositoryTesting(
            id=1,
            name="Test Name",
            description="Description",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        # Mock the query result
        mock_result = mocker.MagicMock()
        mock_result.scalar_one_or_none.return_value = test_instance

        mocker.patch.object(
            mock_session, "execute", mocker.AsyncMock(return_value=mock_result)
        )

        # Call the method
        result = await test_repository.find_one_by(name="Test Name")

        # Verify the result
        assert result is not None
        assert result.id == 1
        assert result.name == "Test Name"

        # Verify the query was executed
        mock_session.execute.assert_called_once()

    async def test_find_one_by_multiple_conditions(
        self,
        test_repository: BaseRepository[ModelForRepositoryTesting],
        mock_session: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        """Test find_one_by with multiple conditions."""
        # Create test instance
        test_instance = ModelForRepositoryTesting(
            id=2,
            name="Test Name",
            description="Specific Description",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        # Mock the query result
        mock_result = mocker.MagicMock()
        mock_result.scalar_one_or_none.return_value = test_instance

        mocker.patch.object(
            mock_session, "execute", mocker.AsyncMock(return_value=mock_result)
        )

        # Call the method
        result = await test_repository.find_one_by(
            name="Test Name", description="Specific Description"
        )

        # Verify the result with soft assertions
        with pytest_check.check:
            assert result is not None
        with pytest_check.check:
            assert result.id == 2
        with pytest_check.check:
            assert result.name == "Test Name"
        with pytest_check.check:
            assert result.description == "Specific Description"

    async def test_find_one_by_no_match(
        self,
        test_repository: BaseRepository[ModelForRepositoryTesting],
        mock_session: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        """Test find_one_by when no instance matches."""
        # Mock empty result
        mock_result = mocker.MagicMock()
        mock_result.scalar_one_or_none.return_value = None

        mocker.patch.object(
            mock_session, "execute", mocker.AsyncMock(return_value=mock_result)
        )

        # Call the method
        result = await test_repository.find_one_by(name="Non-existent Name")

        # Verify result is None
        assert result is None

    async def test_find_one_by_returns_first_match(
        self,
        test_repository: BaseRepository[ModelForRepositoryTesting],
        mock_session: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        """Test find_one_by returns only the first match when multiple exist."""
        # Create first instance (should be returned due to ID ordering)
        first_instance = ModelForRepositoryTesting(
            id=1,
            name="Test Name",
            description="First",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        # Mock the query result - returns only first instance
        mock_result = mocker.MagicMock()
        mock_result.scalar_one_or_none.return_value = first_instance

        mocker.patch.object(
            mock_session, "execute", mocker.AsyncMock(return_value=mock_result)
        )

        # Call the method
        result = await test_repository.find_one_by(name="Test Name")

        # Verify only first instance is returned
        assert result is not None
        assert result.id == 1
        assert result.description == "First"

    async def test_find_one_by_with_nonexistent_field(
        self,
        test_repository: BaseRepository[ModelForRepositoryTesting],
        mock_session: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        """Test find_one_by with a field that doesn't exist on the model."""
        # Mock empty result
        mock_result = mocker.MagicMock()
        mock_result.scalar_one_or_none.return_value = None

        mocker.patch.object(
            mock_session, "execute", mocker.AsyncMock(return_value=mock_result)
        )

        # Call the method with non-existent field
        result = await test_repository.find_one_by(
            name="Test Name", nonexistent_field="Value"
        )

        # Verify result is None (warning should be logged)
        assert result is None
