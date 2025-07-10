"""Unit tests for src/infrastructure/database/repository.py module.

This module contains comprehensive unit tests for the BaseRepository generic class,
including CRUD operations, edge cases, error handling, logging, and thread safety.
"""

import asyncio
import collections
import threading
import types
from typing import Any, cast

import pytest
from pytest_mock import MockerFixture, MockType
from sqlalchemy.exc import SQLAlchemyError

from src.infrastructure.database.base import BaseModel
from src.infrastructure.database.repository import (
    DEFAULT_PAGINATION_LIMIT,
    BaseRepository,
)


@pytest.mark.unit
class TestBaseRepository:
    """Test the BaseRepository generic class with all CRUD operations and edge cases."""

    def test_repository_initialization(
        self,
        mock_async_session: MockType,
        mock_model_class: type[BaseModel],
        mocker: MockerFixture,
    ) -> None:
        """Verify repository initializes correctly with session and model class."""
        # Setup
        mock_logger = mocker.patch("src.infrastructure.database.repository.logger")

        # Execute
        repository = BaseRepository(mock_async_session, mock_model_class)

        # Assert
        assert repository.session is mock_async_session
        assert repository.model_class is mock_model_class
        mock_logger.debug.assert_called_once_with(
            "Initialized repository for {}", "TestModel"
        )

    async def test_get_by_id_found(
        self,
        repository_factory: MockType,
        mock_async_session: MockType,
        mock_model_class: type[BaseModel],
        sample_model_instances: list[BaseModel],
        mock_repository_query_result: MockType,
        mocker: MockerFixture,
    ) -> None:
        """Verify successful retrieval of entity by ID."""
        # Setup
        mock_logger = mocker.patch("src.infrastructure.database.repository.logger")
        test_instance = sample_model_instances[0]
        mock_repository_query_result.scalar_one_or_none.return_value = test_instance
        mock_async_session.execute.return_value = mock_repository_query_result

        repository = repository_factory(mock_async_session, mock_model_class)

        # Execute
        result = await repository.get_by_id(1)

        # Assert
        assert result is test_instance
        assert mock_async_session.execute.called
        mock_logger.debug.assert_any_call("Fetching {} by ID: {}", "TestModel", 1)
        mock_logger.debug.assert_any_call(
            "Found {} instance with ID: {}", "TestModel", 1
        )

    async def test_get_by_id_not_found(
        self,
        repository_factory: MockType,
        mock_async_session: MockType,
        mock_model_class: type[BaseModel],
        mock_repository_query_result: MockType,
        mocker: MockerFixture,
    ) -> None:
        """Verify behavior when entity doesn't exist."""
        # Setup
        mock_logger = mocker.patch("src.infrastructure.database.repository.logger")
        mock_repository_query_result.scalar_one_or_none.return_value = None
        mock_async_session.execute.return_value = mock_repository_query_result

        repository = repository_factory(mock_async_session, mock_model_class)

        # Execute
        result = await repository.get_by_id(999)

        # Assert
        assert result is None
        mock_logger.debug.assert_any_call("Fetching {} by ID: {}", "TestModel", 999)
        mock_logger.debug.assert_any_call(
            "{} instance not found with ID: {}", "TestModel", 999
        )

    @pytest.mark.parametrize("entity_id", [1, 999, 0, -1, 2**31 - 1])
    async def test_get_by_id_with_different_id_types(
        self,
        entity_id: int,
        repository_factory: MockType,
        mock_async_session: MockType,
        mock_model_class: type[BaseModel],
        mock_repository_query_result: MockType,
    ) -> None:
        """Test with various ID types using parametrization."""
        # Setup
        mock_repository_query_result.scalar_one_or_none.return_value = None
        mock_async_session.execute.return_value = mock_repository_query_result

        repository = repository_factory(mock_async_session, mock_model_class)

        # Execute
        result = await repository.get_by_id(entity_id)

        # Assert
        assert result is None
        mock_async_session.execute.assert_called_once()

    async def test_get_all_default_pagination(
        self,
        repository_factory: MockType,
        mock_async_session: MockType,
        mock_model_class: MockType,
        sample_model_instances: list[MockType],
        mock_repository_query_result: MockType,
        mocker: MockerFixture,
    ) -> None:
        """Verify retrieval with default pagination."""
        # Setup
        mock_logger = mocker.patch("src.infrastructure.database.repository.logger")
        mock_repository_query_result.scalars.return_value.all.return_value = (
            sample_model_instances[:3]
        )
        mock_async_session.execute.return_value = mock_repository_query_result

        repository = repository_factory(mock_async_session, mock_model_class)

        # Execute - no limit provided, should use DEFAULT_PAGINATION_LIMIT
        result = await repository.get_all()

        # Assert
        assert result == sample_model_instances[:3]
        assert len(result) == 3
        mock_logger.debug.assert_any_call(
            "Fetching all {} with pagination - skip: {}, limit: {}",
            "TestModel",
            0,
            DEFAULT_PAGINATION_LIMIT,
        )
        mock_logger.debug.assert_any_call("Retrieved {} {} instances", 3, "TestModel")

    def test_default_pagination_limit_constant(self) -> None:
        """Verify DEFAULT_PAGINATION_LIMIT constant is used correctly."""
        assert DEFAULT_PAGINATION_LIMIT == 100

    @pytest.mark.parametrize(
        ("skip", "limit"),
        [(0, 10), (10, 20), (100, 50)],
    )
    async def test_get_all_custom_pagination(
        self,
        skip: int,
        limit: int,
        repository_factory: MockType,
        mock_async_session: MockType,
        mock_model_class: type[BaseModel],
        mock_repository_query_result: MockType,
    ) -> None:
        """Test with custom skip and limit."""
        # Setup
        mock_repository_query_result.scalars.return_value.all.return_value = []
        mock_async_session.execute.return_value = mock_repository_query_result

        repository = repository_factory(mock_async_session, mock_model_class)

        # Execute
        result = await repository.get_all(skip=skip, limit=limit)

        # Assert
        assert result == []
        mock_async_session.execute.assert_called_once()

    @pytest.mark.parametrize(
        ("skip", "limit"),
        [(0, 0), (0, 1), (1, 1000), (1000, 1)],
    )
    async def test_get_all_pagination_edge_cases(
        self,
        skip: int,
        limit: int,
        repository_factory: MockType,
        mock_async_session: MockType,
        mock_model_class: type[BaseModel],
        mock_repository_query_result: MockType,
    ) -> None:
        """Test pagination with edge case values."""
        # Setup
        mock_repository_query_result.scalars.return_value.all.return_value = []
        mock_async_session.execute.return_value = mock_repository_query_result

        repository = repository_factory(mock_async_session, mock_model_class)

        # Execute
        result = await repository.get_all(skip=skip, limit=limit)

        # Assert
        assert result == []
        mock_async_session.execute.assert_called_once()

    async def test_get_all_empty_result(
        self,
        repository_factory: MockType,
        mock_async_session: MockType,
        mock_model_class: type[BaseModel],
        mock_repository_query_result: MockType,
    ) -> None:
        """Verify behavior with no results."""
        # Setup
        mock_repository_query_result.scalars.return_value.all.return_value = []
        mock_async_session.execute.return_value = mock_repository_query_result

        repository = repository_factory(mock_async_session, mock_model_class)

        # Execute
        result = await repository.get_all()

        # Assert
        assert result == []

    async def test_create_success(
        self,
        repository_factory: MockType,
        mock_async_session: MockType,
        mock_model_class: MockType,
        mocker: MockerFixture,
    ) -> None:
        """Verify successful entity creation."""
        # Setup
        mock_logger = mocker.patch("src.infrastructure.database.repository.logger")
        test_obj = mocker.Mock()
        test_obj.id = None

        repository = repository_factory(mock_async_session, mock_model_class)

        # Simulate server-generated ID
        def set_id(*args: object) -> None:
            del args  # Unused
            test_obj.id = 42

        mock_async_session.refresh.side_effect = set_id

        # Execute
        result = await repository.create(test_obj)

        # Assert
        assert result is test_obj
        assert result.id == 42
        mock_async_session.add.assert_called_once_with(test_obj)
        mock_async_session.flush.assert_called_once()
        mock_async_session.refresh.assert_called_once_with(test_obj)
        mock_logger.debug.assert_called_with("Creating new {} instance", "TestModel")
        mock_logger.info.assert_called_with(
            "Created {} instance with ID: {}", "TestModel", 42
        )

    async def test_create_with_server_generated_values(
        self,
        repository_factory: MockType,
        mock_async_session: MockType,
        mock_model_class: MockType,
        mocker: MockerFixture,
    ) -> None:
        """Test that server-generated ID and timestamps are populated."""
        # Setup
        test_obj = mocker.Mock()
        test_obj.id = None
        test_obj.created_at = None
        test_obj.updated_at = None

        repository = repository_factory(mock_async_session, mock_model_class)

        # Simulate server-generated values
        def populate_values(*args: object) -> None:
            del args  # Unused
            test_obj.id = 123
            test_obj.created_at = "2024-01-01T00:00:00"
            test_obj.updated_at = "2024-01-01T00:00:00"

        mock_async_session.refresh.side_effect = populate_values

        # Execute
        result = await repository.create(test_obj)

        # Assert
        assert result.id == 123
        assert result.created_at == "2024-01-01T00:00:00"
        assert result.updated_at == "2024-01-01T00:00:00"

    async def test_update_existing_entity(
        self,
        repository_factory: MockType,
        mock_async_session: MockType,
        mock_model_class: type[BaseModel],
        sample_model_instances: list[BaseModel],
        mock_repository_query_result: MockType,
        mocker: MockerFixture,
    ) -> None:
        """Verify successful partial update."""
        # Setup
        mock_logger = mocker.patch("src.infrastructure.database.repository.logger")
        test_instance = sample_model_instances[0]
        mock_repository_query_result.scalar_one_or_none.return_value = test_instance
        mock_async_session.execute.return_value = mock_repository_query_result

        repository = repository_factory(mock_async_session, mock_model_class)

        update_data = {"name": "Updated Name", "status": "updated"}

        # Execute
        result = await repository.update(1, update_data)

        # Assert
        assert result is test_instance
        assert hasattr(test_instance, "name")
        assert test_instance.name == "Updated Name"
        assert hasattr(test_instance, "status")
        assert test_instance.status == "updated"
        mock_async_session.flush.assert_called_once()
        mock_async_session.refresh.assert_called_once_with(test_instance)
        mock_logger.info.assert_called_with(
            "Updated {} instance ID {} - fields: {}",
            "TestModel",
            1,
            ["name", "status"],
        )

    async def test_update_non_existent_entity(
        self,
        repository_factory: MockType,
        mock_async_session: MockType,
        mock_model_class: type[BaseModel],
        mock_repository_query_result: MockType,
        mocker: MockerFixture,
    ) -> None:
        """Verify behavior when entity doesn't exist."""
        # Setup
        mock_logger = mocker.patch("src.infrastructure.database.repository.logger")
        mock_repository_query_result.scalar_one_or_none.return_value = None
        mock_async_session.execute.return_value = mock_repository_query_result

        repository = repository_factory(mock_async_session, mock_model_class)

        # Execute
        result = await repository.update(999, {"name": "Test"})

        # Assert
        assert result is None
        mock_logger.debug.assert_any_call(
            "{} instance not found for update - ID: {}", "TestModel", 999
        )

    async def test_update_with_invalid_fields(
        self,
        repository_factory: MockType,
        mock_async_session: MockType,
        mock_model_class: type[BaseModel],
        sample_model_instances: list[BaseModel],
        mock_repository_query_result: MockType,
        mocker: MockerFixture,
    ) -> None:
        """Test updating non-existent attributes."""
        # Setup
        mock_logger = mocker.patch("src.infrastructure.database.repository.logger")
        test_instance = sample_model_instances[0]
        mock_repository_query_result.scalar_one_or_none.return_value = test_instance
        mock_async_session.execute.return_value = mock_repository_query_result

        repository = repository_factory(mock_async_session, mock_model_class)

        # Test with a field that doesn't exist on our model
        update_data = {"name": "Valid Update", "invalid_field": "Invalid Value"}

        # Execute
        result = await repository.update(1, update_data)

        # Assert
        assert result is test_instance
        assert hasattr(test_instance, "name")
        assert test_instance.name == "Valid Update"
        mock_logger.warning.assert_called_once_with(
            "Attempted to update non-existent field '{}' on {}",
            "invalid_field",
            "TestModel",
        )

    async def test_update_empty_data(
        self,
        repository_factory: MockType,
        mock_async_session: MockType,
        mock_model_class: type[BaseModel],
        sample_model_instances: list[BaseModel],
        mock_repository_query_result: MockType,
    ) -> None:
        """Test with empty update dictionary."""
        # Setup
        test_instance = sample_model_instances[0]
        mock_repository_query_result.scalar_one_or_none.return_value = test_instance
        mock_async_session.execute.return_value = mock_repository_query_result

        repository = repository_factory(mock_async_session, mock_model_class)

        # Execute
        result = await repository.update(1, {})

        # Assert
        assert result is test_instance
        mock_async_session.flush.assert_called_once()
        mock_async_session.refresh.assert_called_once()

    @pytest.mark.parametrize(
        "data_type_name",
        [
            "dict",
            "OrderedDict",
            "MappingProxyType",
        ],
    )
    async def test_update_with_different_mapping_types(
        self,
        data_type_name: str,
        repository_factory: MockType,
        mock_async_session: MockType,
        mock_model_class: type[BaseModel],
        sample_model_instances: list[BaseModel],
        mock_repository_query_result: MockType,
    ) -> None:
        """Test update with various Mapping implementations."""
        # Setup
        test_instance = sample_model_instances[0]
        mock_repository_query_result.scalar_one_or_none.return_value = test_instance
        mock_async_session.execute.return_value = mock_repository_query_result

        repository = repository_factory(mock_async_session, mock_model_class)

        # Create update data with the specific type
        update_data: Any
        if data_type_name == "dict":
            update_data = {"name": "Updated"}
        elif data_type_name == "OrderedDict":
            update_data = collections.OrderedDict({"name": "Updated"})
        else:  # MappingProxyType
            # MappingProxyType implements Mapping protocol
            update_data = types.MappingProxyType({"name": "Updated"})

        # Execute
        result = await repository.update(1, update_data)

        # Assert
        assert result is test_instance
        assert hasattr(test_instance, "name")
        assert test_instance.name == "Updated"

    async def test_delete_existing_entity(
        self,
        repository_factory: MockType,
        mock_async_session: MockType,
        mock_model_class: MockType,
        mocker: MockerFixture,
    ) -> None:
        """Verify successful deletion."""
        # Setup
        mock_logger = mocker.patch("src.infrastructure.database.repository.logger")
        mock_result = mocker.Mock()
        mock_result.rowcount = 1
        mock_async_session.execute.return_value = mock_result

        repository = repository_factory(mock_async_session, mock_model_class)

        # Execute
        result = await repository.delete(1)

        # Assert
        assert result is True
        mock_async_session.execute.assert_called_once()
        mock_logger.info.assert_called_with(
            "Deleted {} instance with ID: {}", "TestModel", 1
        )

    async def test_delete_non_existent_entity(
        self,
        repository_factory: MockType,
        mock_async_session: MockType,
        mock_model_class: MockType,
        mocker: MockerFixture,
    ) -> None:
        """Verify behavior when entity doesn't exist."""
        # Setup
        mock_logger = mocker.patch("src.infrastructure.database.repository.logger")
        mock_result = mocker.Mock()
        mock_result.rowcount = 0
        mock_async_session.execute.return_value = mock_result

        repository = repository_factory(mock_async_session, mock_model_class)

        # Execute
        result = await repository.delete(999)

        # Assert
        assert result is False
        mock_logger.debug.assert_any_call(
            "{} instance not found for deletion - ID: {}", "TestModel", 999
        )

    @pytest.mark.parametrize("count", [0, 1, 10, 100, 1000])
    async def test_count_with_results(
        self,
        count: int,
        repository_factory: MockType,
        mock_async_session: MockType,
        mock_model_class: type[BaseModel],
        mock_repository_query_result: MockType,
    ) -> None:
        """Verify count returns correct number."""
        # Setup
        mock_repository_query_result.scalar.return_value = count
        mock_async_session.execute.return_value = mock_repository_query_result

        repository = repository_factory(mock_async_session, mock_model_class)

        # Execute
        result = await repository.count()

        # Assert
        assert result == count

    async def test_count_with_none_result(
        self,
        repository_factory: MockType,
        mock_async_session: MockType,
        mock_model_class: type[BaseModel],
        mock_repository_query_result: MockType,
    ) -> None:
        """Test when scalar returns None."""
        # Setup
        mock_repository_query_result.scalar.return_value = None
        mock_async_session.execute.return_value = mock_repository_query_result

        repository = repository_factory(mock_async_session, mock_model_class)

        # Execute
        result = await repository.count()

        # Assert
        assert result == 0

    async def test_exists_when_true(
        self,
        repository_factory: MockType,
        mock_async_session: MockType,
        mock_model_class: type[BaseModel],
        mock_repository_query_result: MockType,
    ) -> None:
        """Verify existence check returns True."""
        # Setup
        mock_repository_query_result.scalar.return_value = 1
        mock_async_session.execute.return_value = mock_repository_query_result

        repository = repository_factory(mock_async_session, mock_model_class)

        # Execute
        result = await repository.exists(1)

        # Assert
        assert result is True

    async def test_exists_when_false(
        self,
        repository_factory: MockType,
        mock_async_session: MockType,
        mock_model_class: type[BaseModel],
        mock_repository_query_result: MockType,
    ) -> None:
        """Verify existence check returns False."""
        # Setup
        mock_repository_query_result.scalar.return_value = 0
        mock_async_session.execute.return_value = mock_repository_query_result

        repository = repository_factory(mock_async_session, mock_model_class)

        # Execute
        result = await repository.exists(999)

        # Assert
        assert result is False

    async def test_filter_by_single_field(
        self,
        repository_factory: MockType,
        mock_async_session: MockType,
        mock_model_class: MockType,
        sample_model_instances: list[MockType],
        mock_repository_query_result: MockType,
    ) -> None:
        """Test filtering by one field."""
        # Setup
        filtered_instances = [sample_model_instances[1], sample_model_instances[3]]
        mock_repository_query_result.scalars.return_value.all.return_value = (
            filtered_instances
        )
        mock_async_session.execute.return_value = mock_repository_query_result

        repository = repository_factory(mock_async_session, mock_model_class)

        # Execute
        result = await repository.filter_by(status="active")

        # Assert
        assert result == filtered_instances
        assert len(result) == 2

    async def test_filter_by_multiple_fields(
        self,
        repository_factory: MockType,
        mock_async_session: MockType,
        mock_model_class: MockType,
        sample_model_instances: list[MockType],
        mock_repository_query_result: MockType,
    ) -> None:
        """Test filtering by multiple fields."""
        # Setup
        filtered_instances = [sample_model_instances[1]]
        mock_repository_query_result.scalars.return_value.all.return_value = (
            filtered_instances
        )
        mock_async_session.execute.return_value = mock_repository_query_result

        repository = repository_factory(mock_async_session, mock_model_class)

        # Execute
        result = await repository.filter_by(status="active", name="Test2")

        # Assert
        assert result == filtered_instances
        assert len(result) == 1

    async def test_filter_by_invalid_field(
        self,
        repository_factory: MockType,
        mock_async_session: MockType,
        mock_model_class: type[BaseModel],
        mock_repository_query_result: MockType,
        mocker: MockerFixture,
    ) -> None:
        """Test with non-existent field."""
        # Setup
        mock_logger = mocker.patch("src.infrastructure.database.repository.logger")
        mock_repository_query_result.scalars.return_value.all.return_value = []
        mock_async_session.execute.return_value = mock_repository_query_result

        repository = repository_factory(mock_async_session, mock_model_class)

        # Execute - we know 'invalid_field' doesn't exist on our test model
        result = await repository.filter_by(invalid_field="value")

        # Assert
        assert result == []
        mock_logger.warning.assert_called_with(
            "Attempted to filter by non-existent field '{}' on {}",
            "invalid_field",
            "TestModel",
        )

    async def test_filter_by_empty_kwargs(
        self,
        repository_factory: MockType,
        mock_async_session: MockType,
        mock_model_class: MockType,
        sample_model_instances: list[MockType],
        mock_repository_query_result: MockType,
    ) -> None:
        """Test with no filter conditions."""
        # Setup
        mock_repository_query_result.scalars.return_value.all.return_value = (
            sample_model_instances
        )
        mock_async_session.execute.return_value = mock_repository_query_result

        repository = repository_factory(mock_async_session, mock_model_class)

        # Execute
        result = await repository.filter_by()

        # Assert
        assert result == sample_model_instances

    async def test_find_one_by_match_found(
        self,
        repository_factory: MockType,
        mock_async_session: MockType,
        mock_model_class: MockType,
        sample_model_instances: list[MockType],
        mock_repository_query_result: MockType,
    ) -> None:
        """Verify returns first matching instance."""
        # Setup
        test_instance = sample_model_instances[0]
        mock_repository_query_result.scalar_one_or_none.return_value = test_instance
        mock_async_session.execute.return_value = mock_repository_query_result

        repository = repository_factory(mock_async_session, mock_model_class)

        # Execute
        result = await repository.find_one_by(name="Test1")

        # Assert
        assert result is test_instance

    async def test_find_one_by_no_match(
        self,
        repository_factory: MockType,
        mock_async_session: MockType,
        mock_model_class: type[BaseModel],
        mock_repository_query_result: MockType,
    ) -> None:
        """Verify returns None when no match."""
        # Setup
        mock_repository_query_result.scalar_one_or_none.return_value = None
        mock_async_session.execute.return_value = mock_repository_query_result

        repository = repository_factory(mock_async_session, mock_model_class)

        # Execute
        result = await repository.find_one_by(name="NonExistent")

        # Assert
        assert result is None

    async def test_find_one_by_multiple_matches(
        self,
        repository_factory: MockType,
        mock_async_session: MockType,
        mock_model_class: MockType,
        sample_model_instances: list[MockType],
        mock_repository_query_result: MockType,
    ) -> None:
        """Verify returns only first result."""
        # Setup
        # Even with multiple matches, scalar_one_or_none returns first
        mock_repository_query_result.scalar_one_or_none.return_value = (
            sample_model_instances[0]
        )
        mock_async_session.execute.return_value = mock_repository_query_result

        repository = repository_factory(mock_async_session, mock_model_class)

        # Execute
        result = await repository.find_one_by(status="active")

        # Assert
        assert result is sample_model_instances[0]
        # Verify limit was applied (though we don't test SQL construction directly)
        mock_async_session.execute.assert_called_once()

    async def test_find_one_by_invalid_field(
        self,
        repository_factory: MockType,
        mock_async_session: MockType,
        mock_model_class: type[BaseModel],
        mock_repository_query_result: MockType,
        mocker: MockerFixture,
    ) -> None:
        """Test find_one_by with non-existent field."""
        # Setup
        mock_logger = mocker.patch("src.infrastructure.database.repository.logger")
        mock_repository_query_result.scalar_one_or_none.return_value = None
        mock_async_session.execute.return_value = mock_repository_query_result

        repository = repository_factory(mock_async_session, mock_model_class)

        # Execute - we know 'invalid_field' doesn't exist on our test model
        result = await repository.find_one_by(invalid_field="value")

        # Assert
        assert result is None
        mock_logger.warning.assert_called_with(
            "Attempted to filter by non-existent field '{}' on {}",
            "invalid_field",
            "TestModel",
        )

    def test_concurrent_read_operations(
        self,
        thread_sync: dict[str, Any],
        repository_factory: MockType,
        mock_async_session: MockType,
        mock_model_class: type[BaseModel],
        mocker: MockerFixture,
    ) -> None:
        """Verify concurrent read operations don't interfere."""
        # Setup
        num_threads = 5
        barrier = thread_sync["barrier"](num_threads)
        results = thread_sync["create_results"]()
        errors: list[Exception] = []

        # Create different results for each thread
        thread_results = {}
        for i in range(num_threads):
            instance = mocker.Mock()
            instance.id = i + 1
            thread_results[i + 1] = instance

        def mock_execute_side_effect(stmt: object) -> MockType:
            # We ignore the stmt parameter for testing purposes
            # In real scenario, we'd parse the SQL but we're testing behavior
            del stmt  # Explicitly ignore the parameter
            result = mocker.Mock()
            result.scalar_one_or_none = mocker.Mock(return_value=thread_results.get(1))
            return cast("MockType", result)

        mock_async_session.execute.side_effect = mock_execute_side_effect

        repository = repository_factory(mock_async_session, mock_model_class)

        def run_get_by_id(entity_id: int) -> None:
            try:
                barrier.wait()
                # Run async code in thread
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(repository.get_by_id(entity_id))
                results.append((entity_id, result))
            except Exception as e:
                errors.append(e)

        # Execute
        threads = []
        for i in range(num_threads):
            t = threading.Thread(target=run_get_by_id, args=(i + 1,))
            threads.append(t)
            t.start()

        # Wait for completion
        for t in threads:
            t.join(timeout=5.0)

        # Assert
        assert len(errors) == 0
        assert len(results) == num_threads

    def test_concurrent_mixed_operations(
        self,
        thread_sync: dict[str, Any],
        repository_factory: MockType,
        mock_async_session: MockType,
        mock_model_class: type[BaseModel],
        mocker: MockerFixture,
    ) -> None:
        """Verify mixed read/write operations handle concurrency."""
        # Setup
        barrier = thread_sync["barrier"](4)
        results = thread_sync["create_results"]()
        errors: list[Exception] = []

        repository = repository_factory(mock_async_session, mock_model_class)

        # Mock different operations
        mock_async_session.execute.return_value = mocker.Mock(
            scalar_one_or_none=mocker.Mock(return_value=None),
            scalar=mocker.Mock(return_value=0),
            rowcount=0,
        )

        def run_operation(operation: str, entity_id: int) -> None:
            try:
                barrier.wait()
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                if operation == "get":
                    result = loop.run_until_complete(repository.get_by_id(entity_id))
                elif operation == "create":
                    obj = mocker.Mock()
                    result = loop.run_until_complete(repository.create(obj))
                elif operation == "update":
                    result = loop.run_until_complete(
                        repository.update(entity_id, {"name": "Updated"})
                    )
                elif operation == "delete":
                    result = loop.run_until_complete(repository.delete(entity_id))
                else:
                    result = None

                results.append((operation, result))
            except Exception as e:
                errors.append(e)

        # Execute
        operations = [
            ("get", 1),
            ("create", 0),
            ("update", 2),
            ("delete", 3),
        ]

        threads = []
        for op, eid in operations:
            t = threading.Thread(target=run_operation, args=(op, eid))
            threads.append(t)
            t.start()

        # Wait for completion
        for t in threads:
            t.join(timeout=5.0)

        # Assert
        assert len(errors) == 0
        assert len(results) == 4

    async def test_logging_levels(
        self,
        repository_factory: MockType,
        mock_async_session: MockType,
        mock_model_class: type[BaseModel],
        mock_repository_query_result: MockType,
        mocker: MockerFixture,
    ) -> None:
        """Verify correct log levels used."""
        # Setup
        mock_logger = mocker.patch("src.infrastructure.database.repository.logger")
        repository = repository_factory(mock_async_session, mock_model_class)

        # Test DEBUG for queries
        mock_repository_query_result.scalar_one_or_none.return_value = None
        mock_async_session.execute.return_value = mock_repository_query_result
        await repository.get_by_id(1)
        assert any("debug" in str(call) for call in mock_logger.method_calls)

        # Test INFO for mutations
        test_obj = mocker.Mock()
        test_obj.id = 1
        await repository.create(test_obj)
        assert any("info" in str(call) for call in mock_logger.method_calls)

        # Test WARNING for errors
        # Create a real model instance to test hasattr behavior
        real_instance = mock_model_class()
        real_instance.id = 1
        if hasattr(real_instance, "name"):
            real_instance.name = "Test"
        mock_repository_query_result.scalar_one_or_none.return_value = real_instance

        # Test with a field that doesn't exist on our model
        # Use hasattr to verify the field doesn't exist before testing
        assert not hasattr(real_instance, "invalid_field")
        await repository.update(1, {"invalid_field": "value"})
        assert any("warning" in str(call) for call in mock_logger.method_calls)

    async def test_database_error_handling(
        self,
        repository_factory: MockType,
        mock_async_session: MockType,
        mock_model_class: MockType,
        mocker: MockerFixture,
    ) -> None:
        """Test behavior when session operations fail."""
        # Setup
        repository = repository_factory(mock_async_session, mock_model_class)
        mock_async_session.execute.side_effect = SQLAlchemyError("Database error")

        # Execute & Assert - exceptions should propagate
        with pytest.raises(SQLAlchemyError, match="Database error"):
            await repository.get_by_id(1)

        # Test with flush error
        mock_async_session.execute.side_effect = None
        mock_async_session.flush.side_effect = SQLAlchemyError("Flush error")

        test_obj = mocker.Mock()
        with pytest.raises(SQLAlchemyError, match="Flush error"):
            await repository.create(test_obj)

    def test_generic_type_constraints(
        self,
        repository_factory: MockType,
        mock_async_session: MockType,
        mock_model_class: type[BaseModel],
    ) -> None:
        """Verify TypeVar[T: BaseModel] constraint works."""
        # Verify that the repository works with a concrete BaseModel subclass
        repository = repository_factory(mock_async_session, mock_model_class)

        # Assert
        assert repository.model_class is mock_model_class
        assert hasattr(repository.model_class, "id")
