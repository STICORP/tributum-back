"""Unit tests for repository query operations."""

from datetime import UTC, datetime

import pytest
import pytest_check
from pytest_mock import MockerFixture
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.repository import BaseRepository

from .conftest import ModelForRepositoryTesting


@pytest.mark.unit
@pytest.mark.asyncio
class TestRepositoryQueries:
    """Test cases for BaseRepository query operations."""

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

        mock_execute = mocker.patch.object(
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
        mock_execute.assert_called_once()

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

        mock_execute = mocker.patch.object(
            mock_session, "execute", mocker.AsyncMock(return_value=mock_result)
        )

        # Call the method with pagination
        result = await test_repository.get_all(skip=10, limit=5)

        # Verify the result
        assert len(result) == 5
        assert result[0].id == 11

        # Verify the query was executed
        mock_execute.assert_called_once()

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

    async def test_count_with_instances(
        self,
        test_repository: BaseRepository[ModelForRepositoryTesting],
        mock_session: AsyncSession,
        mocker: MockerFixture,
    ) -> None:
        """Test count when instances exist."""
        # Mock the execute result
        mock_result = mocker.MagicMock()
        mock_result.scalar.return_value = 5

        mock_execute = mocker.patch.object(
            mock_session, "execute", mocker.AsyncMock(return_value=mock_result)
        )

        # Call the method
        result = await test_repository.count()

        # Verify count
        assert result == 5
        mock_execute.assert_called()

    async def test_count_empty_table(
        self,
        test_repository: BaseRepository[ModelForRepositoryTesting],
        mock_session: AsyncSession,
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
        mock_session: AsyncSession,
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
        mock_session: AsyncSession,
        mocker: MockerFixture,
    ) -> None:
        """Test exists when instance exists."""
        # Mock the execute result
        mock_result = mocker.MagicMock()
        mock_result.scalar.return_value = 1

        mock_execute = mocker.patch.object(
            mock_session, "execute", mocker.AsyncMock(return_value=mock_result)
        )

        # Call the method
        result = await test_repository.exists(1)

        # Verify exists is True
        assert result is True
        mock_execute.assert_called()

    async def test_exists_false(
        self,
        test_repository: BaseRepository[ModelForRepositoryTesting],
        mock_session: AsyncSession,
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
        mock_session: AsyncSession,
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
        mock_session: AsyncSession,
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

        mock_execute = mocker.patch.object(
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
        mock_execute.assert_called_once()

    async def test_filter_by_multiple_conditions(
        self,
        test_repository: BaseRepository[ModelForRepositoryTesting],
        mock_session: AsyncSession,
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

        mock_execute = mocker.patch.object(
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
        mock_execute.assert_called_once()

    async def test_filter_by_no_matches(
        self,
        test_repository: BaseRepository[ModelForRepositoryTesting],
        mock_session: AsyncSession,
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
        mock_session: AsyncSession,
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
        mock_session: AsyncSession,
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

        mock_execute = mocker.patch.object(
            mock_session, "execute", mocker.AsyncMock(return_value=mock_result)
        )

        # Call the method
        result = await test_repository.find_one_by(name="Test Name")

        # Verify the result
        assert result is not None
        assert result.id == 1
        assert result.name == "Test Name"

        # Verify the query was executed
        mock_execute.assert_called_once()

    async def test_find_one_by_multiple_conditions(
        self,
        test_repository: BaseRepository[ModelForRepositoryTesting],
        mock_session: AsyncSession,
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
        mock_session: AsyncSession,
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
        mock_session: AsyncSession,
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
        mock_session: AsyncSession,
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
