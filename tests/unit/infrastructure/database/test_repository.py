"""Unit tests for the base repository implementation."""

from datetime import UTC, datetime
from typing import cast

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
def mock_session(mocker: MockerFixture) -> AsyncSession:
    """Create a properly mocked async session."""
    return cast("AsyncSession", mocker.MagicMock(spec=AsyncSession))


@pytest.fixture
def test_repository(
    mock_session: AsyncSession,
) -> BaseRepository[ModelForRepositoryTesting]:
    """Create a test repository instance."""
    return BaseRepository(mock_session, ModelForRepositoryTesting)


@pytest.mark.asyncio
class TestBaseRepository:
    """Test cases for BaseRepository class."""

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
        assert mock_session.execute.called  # type: ignore[attr-defined]
        assert mock_session.execute.call_count == 1  # type: ignore[attr-defined]

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
        mocker.patch.object(
            mock_session, "execute", mocker.AsyncMock(return_value=mock_result)
        )

        # Call the method
        result = await test_repository.get_by_id(999)

        # Verify the result is None
        assert result is None

        # Verify the query was executed
        assert mock_session.execute.called  # type: ignore[attr-defined]

    async def test_get_all_with_results(
        self,
        test_repository: BaseRepository[ModelForRepositoryTesting],
        mock_session: AsyncSession,
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
        assert mock_session.execute.called  # type: ignore[attr-defined]

    async def test_get_all_with_pagination(
        self,
        test_repository: BaseRepository[ModelForRepositoryTesting],
        mock_session: AsyncSession,
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
        assert mock_session.execute.called  # type: ignore[attr-defined]

    async def test_get_all_empty_result(
        self,
        test_repository: BaseRepository[ModelForRepositoryTesting],
        mock_session: AsyncSession,
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
        assert mock_session.add.called  # type: ignore[attr-defined]
        assert mock_session.flush.called  # type: ignore[attr-defined]
        assert mock_session.refresh.called  # type: ignore[attr-defined]

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
