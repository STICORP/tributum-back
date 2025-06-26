"""Unit tests for the context module."""

import asyncio
import re
import uuid

import pytest

from src.core.context import (
    RequestContext,
    generate_correlation_id,
    generate_request_id,
)


@pytest.mark.unit
class TestCorrelationIDGeneration:
    """Test correlation ID generation functionality."""

    def test_generate_correlation_id_returns_string(self) -> None:
        """Test that generate_correlation_id returns a string."""
        correlation_id = generate_correlation_id()
        assert isinstance(correlation_id, str)

    def test_generate_correlation_id_is_valid_uuid(self) -> None:
        """Test that generated correlation ID is a valid UUID."""
        correlation_id = generate_correlation_id()
        # Should not raise an exception
        parsed_uuid = uuid.UUID(correlation_id)
        assert str(parsed_uuid) == correlation_id

    def test_generate_correlation_id_is_uuid4(self) -> None:
        """Test that generated correlation ID is specifically a UUID4."""
        correlation_id = generate_correlation_id()
        parsed_uuid = uuid.UUID(correlation_id)
        assert parsed_uuid.version == 4

    def test_generate_correlation_id_format(self) -> None:
        """Test that correlation ID has the correct UUID format."""
        correlation_id = generate_correlation_id()
        # UUID4 format: xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx
        # where y is one of 8, 9, A, or B
        uuid_pattern = re.compile(
            r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
            re.IGNORECASE,
        )
        assert uuid_pattern.match(correlation_id) is not None

    def test_generate_correlation_id_uniqueness(self) -> None:
        """Test that each generated correlation ID is unique."""
        # Generate multiple IDs
        ids = [generate_correlation_id() for _ in range(100)]
        # Check all are unique
        assert len(ids) == len(set(ids))

    def test_generate_correlation_id_length(self) -> None:
        """Test that correlation ID has the expected length."""
        correlation_id = generate_correlation_id()
        # UUID string length is always 36 (32 hex chars + 4 hyphens)
        assert len(correlation_id) == 36


@pytest.mark.unit
class TestRequestContext:
    """Test RequestContext for storing and retrieving correlation IDs."""

    def test_set_and_get_correlation_id(self) -> None:
        """Test setting and getting a correlation ID."""
        test_id = "test-correlation-123"
        RequestContext.set_correlation_id(test_id)
        assert RequestContext.get_correlation_id() == test_id

    def test_get_correlation_id_returns_none_when_not_set(self) -> None:
        """Test getting correlation ID returns None when not set."""
        RequestContext.clear()  # Ensure clean state
        assert RequestContext.get_correlation_id() is None

    def test_clear_removes_correlation_id(self) -> None:
        """Test that clear() removes the correlation ID."""
        test_id = "test-correlation-456"
        RequestContext.set_correlation_id(test_id)
        assert RequestContext.get_correlation_id() == test_id

        RequestContext.clear()
        assert RequestContext.get_correlation_id() is None

    def test_overwrite_correlation_id(self) -> None:
        """Test that setting a new correlation ID overwrites the old one."""
        first_id = "first-correlation-id"
        second_id = "second-correlation-id"

        RequestContext.set_correlation_id(first_id)
        assert RequestContext.get_correlation_id() == first_id

        RequestContext.set_correlation_id(second_id)
        assert RequestContext.get_correlation_id() == second_id

    @pytest.mark.asyncio
    async def test_context_isolation_between_async_tasks(self) -> None:
        """Test that context is isolated between concurrent async tasks."""
        results = []

        async def task1() -> None:
            """First async task setting its own correlation ID."""
            RequestContext.set_correlation_id("task1-id")
            await asyncio.sleep(0.01)  # Simulate some async work
            results.append(("task1", RequestContext.get_correlation_id()))

        async def task2() -> None:
            """Second async task setting its own correlation ID."""
            RequestContext.set_correlation_id("task2-id")
            await asyncio.sleep(0.01)  # Simulate some async work
            results.append(("task2", RequestContext.get_correlation_id()))

        # Run tasks concurrently
        await asyncio.gather(task1(), task2())

        # Each task should see its own correlation ID
        assert ("task1", "task1-id") in results
        assert ("task2", "task2-id") in results

    @pytest.mark.asyncio
    async def test_context_propagation_in_async_chain(self) -> None:
        """Test that context propagates through async call chain."""
        correlation_id = "chain-correlation-id"

        async def inner_function() -> str | None:
            """Inner function that reads the correlation ID."""
            return RequestContext.get_correlation_id()

        async def middle_function() -> str | None:
            """Middle function in the call chain."""
            return await inner_function()

        async def outer_function() -> str | None:
            """Outer function that sets the correlation ID."""
            RequestContext.set_correlation_id(correlation_id)
            return await middle_function()

        result = await outer_function()
        assert result == correlation_id

    def test_context_with_generated_correlation_id(self) -> None:
        """Test using RequestContext with a generated correlation ID."""
        generated_id = generate_correlation_id()
        RequestContext.set_correlation_id(generated_id)

        retrieved_id = RequestContext.get_correlation_id()
        assert retrieved_id == generated_id
        assert uuid.UUID(retrieved_id)  # Verify it's a valid UUID


@pytest.mark.unit
class TestRequestIDGeneration:
    """Test request ID generation functionality."""

    def test_generate_request_id_returns_string(self) -> None:
        """Test that generate_request_id returns a string."""
        request_id = generate_request_id()
        assert isinstance(request_id, str)

    def test_generate_request_id_has_prefix(self) -> None:
        """Test that request ID has the correct prefix."""
        request_id = generate_request_id()
        assert request_id.startswith("req-")

    def test_generate_request_id_contains_valid_uuid(self) -> None:
        """Test that request ID contains a valid UUID after prefix."""
        request_id = generate_request_id()
        # Remove prefix and validate UUID
        uuid_part = request_id[4:]  # Skip "req-"
        parsed_uuid = uuid.UUID(uuid_part)
        assert str(parsed_uuid) == uuid_part

    def test_generate_request_id_format(self) -> None:
        """Test that request ID has the correct format."""
        request_id = generate_request_id()
        # Format: req-xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx
        request_id_pattern = re.compile(
            r"^req-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
            re.IGNORECASE,
        )
        assert request_id_pattern.match(request_id) is not None

    def test_generate_request_id_uniqueness(self) -> None:
        """Test that each generated request ID is unique."""
        # Generate multiple IDs
        ids = [generate_request_id() for _ in range(100)]
        # Check all are unique
        assert len(ids) == len(set(ids))

    def test_generate_request_id_length(self) -> None:
        """Test that request ID has the expected length."""
        request_id = generate_request_id()
        # Length is 4 (prefix) + 36 (UUID) = 40
        assert len(request_id) == 40

    def test_request_id_different_from_correlation_id(self) -> None:
        """Test that request ID format is different from correlation ID."""
        request_id = generate_request_id()
        correlation_id = generate_correlation_id()

        assert request_id.startswith("req-")
        assert not correlation_id.startswith("req-")
        assert len(request_id) > len(correlation_id)
