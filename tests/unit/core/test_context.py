"""Unit tests for src/core/context.py.

This module tests the thread-safe and async-safe context management functionality,
including correlation ID propagation and request ID generation.
"""

import asyncio
import threading
import uuid
from typing import Any

import pytest

from src.core.context import (
    RequestContext,
    generate_correlation_id,
    generate_request_id,
)


@pytest.mark.unit
class TestCoreContext:
    """Test suite for core context management functionality."""

    # RequestContext.set_correlation_id() Tests

    def test_set_correlation_id_stores_value(self) -> None:
        """Test that setting a correlation ID stores it correctly in context."""
        test_id = "test-correlation-id-123"
        RequestContext.set_correlation_id(test_id)

        retrieved_id = RequestContext.get_correlation_id()
        assert retrieved_id == test_id, f"Expected '{test_id}', got '{retrieved_id}'"

    def test_set_correlation_id_overwrites_existing(self) -> None:
        """Test that setting a new correlation ID overwrites the previous one."""
        first_id = "first-correlation-id"
        second_id = "second-correlation-id"

        RequestContext.set_correlation_id(first_id)
        assert RequestContext.get_correlation_id() == first_id

        RequestContext.set_correlation_id(second_id)
        assert RequestContext.get_correlation_id() == second_id
        assert RequestContext.get_correlation_id() != first_id

    def test_set_correlation_id_with_empty_string(self) -> None:
        """Test that empty string correlation ID is handled correctly."""
        RequestContext.set_correlation_id("")

        retrieved_id = RequestContext.get_correlation_id()
        assert retrieved_id == "", "Empty string should be stored as-is"

    # RequestContext.get_correlation_id() Tests

    def test_get_correlation_id_returns_set_value(self) -> None:
        """Test retrieval of previously set correlation ID."""
        expected_id = "retrieve-test-id"
        RequestContext.set_correlation_id(expected_id)

        actual_id = RequestContext.get_correlation_id()
        assert actual_id == expected_id, f"Expected '{expected_id}', got '{actual_id}'"

    def test_get_correlation_id_returns_none_when_not_set(self) -> None:
        """Test that getting correlation ID returns None when no ID is set."""
        result = RequestContext.get_correlation_id()
        assert result is None, "Should return None when no correlation ID is set"

    def test_get_correlation_id_returns_none_after_clear(self) -> None:
        """Test that getting correlation ID returns None after context is cleared."""
        RequestContext.set_correlation_id("will-be-cleared")
        RequestContext.clear()

        result = RequestContext.get_correlation_id()
        assert result is None, "Should return None after clearing context"

    # RequestContext.clear() Tests

    def test_clear_removes_correlation_id(self) -> None:
        """Test that clear() removes the correlation ID from context."""
        test_id = "to-be-cleared"
        RequestContext.set_correlation_id(test_id)
        assert RequestContext.get_correlation_id() == test_id

        RequestContext.clear()
        assert RequestContext.get_correlation_id() is None

    def test_clear_idempotent_when_nothing_set(self) -> None:
        """Test that clear() can be called safely when no correlation ID is set."""
        # Should not raise any exceptions
        RequestContext.clear()
        assert RequestContext.get_correlation_id() is None

    def test_clear_multiple_calls_safe(self) -> None:
        """Test that multiple clear() calls are safe."""
        RequestContext.set_correlation_id("multiple-clear-test")

        # Multiple clears should not cause issues
        RequestContext.clear()
        RequestContext.clear()
        RequestContext.clear()

        assert RequestContext.get_correlation_id() is None

    # Thread Safety Tests

    def test_context_isolation_between_threads(
        self, thread_sync: dict[str, Any]
    ) -> None:
        """Test that each thread maintains its own correlation ID context."""
        num_threads = 3
        barrier = thread_sync["barrier"](num_threads)
        results = thread_sync["create_results"]()

        def thread_task(thread_id: int) -> None:
            """Set unique correlation ID and verify isolation."""
            correlation_id = f"thread-{thread_id}-id"
            RequestContext.set_correlation_id(correlation_id)

            # Synchronize all threads
            barrier.wait()

            # Verify each thread sees its own correlation ID
            retrieved_id = RequestContext.get_correlation_id()
            results.append((thread_id, retrieved_id))

        threads = []
        for i in range(num_threads):
            thread = threading.Thread(target=thread_task, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=5.0)

        # Verify results
        assert len(results) == num_threads
        for thread_id, correlation_id in results:
            expected = f"thread-{thread_id}-id"
            assert correlation_id == expected, (
                f"Thread {thread_id} expected '{expected}', got '{correlation_id}'"
            )

    def test_context_does_not_leak_between_threads(
        self, thread_sync: dict[str, Any]
    ) -> None:
        """Test that setting correlation ID in one thread doesn't affect others."""
        barrier = thread_sync["barrier"](2)
        results = thread_sync["create_results"]()

        def setter_thread() -> None:
            """Thread that sets a correlation ID."""
            RequestContext.set_correlation_id("setter-thread-id")
            barrier.wait()
            results.append(("setter", RequestContext.get_correlation_id()))

        def getter_thread() -> None:
            """Thread that only reads correlation ID."""
            barrier.wait()
            results.append(("getter", RequestContext.get_correlation_id()))

        thread1 = threading.Thread(target=setter_thread)
        thread2 = threading.Thread(target=getter_thread)

        thread1.start()
        thread2.start()

        thread1.join(timeout=5.0)
        thread2.join(timeout=5.0)

        # Verify results
        assert len(results) == 2
        for thread_name, correlation_id in results:
            if thread_name == "setter":
                assert correlation_id == "setter-thread-id"
            else:  # getter
                assert correlation_id is None, "Getter thread should see None"

    # Async Safety Tests

    async def test_context_inheritance_in_async_tasks(self) -> None:
        """Test that correlation ID is inherited by child async tasks."""
        parent_id = "parent-task-id"
        RequestContext.set_correlation_id(parent_id)

        async def child_task() -> str | None:
            """Child task that reads the correlation ID."""
            return RequestContext.get_correlation_id()

        # Create and await child task
        child_result = await child_task()

        assert child_result == parent_id, (
            f"Child task should inherit parent's correlation ID: "
            f"expected '{parent_id}', got '{child_result}'"
        )

    async def test_context_isolation_between_async_tasks(self) -> None:
        """Test that async tasks can have independent contexts."""
        results: list[tuple[int, str | None]] = []

        async def async_task(task_id: int) -> None:
            """Set unique correlation ID for each task."""
            correlation_id = f"async-task-{task_id}"
            RequestContext.set_correlation_id(correlation_id)

            # Small delay to ensure tasks overlap
            await asyncio.sleep(0.01)

            retrieved_id = RequestContext.get_correlation_id()
            results.append((task_id, retrieved_id))

        # Create multiple concurrent tasks
        tasks = [async_task(i) for i in range(3)]
        await asyncio.gather(*tasks)

        # Verify each task maintained its own context
        assert len(results) == 3
        for task_id, correlation_id in results:
            expected = f"async-task-{task_id}"
            assert correlation_id == expected, (
                f"Task {task_id} expected '{expected}', got '{correlation_id}'"
            )

    async def test_context_modification_in_child_task_does_not_affect_parent(
        self,
    ) -> None:
        """Test that child task modifying context doesn't affect parent."""
        parent_id = "parent-unchanged"
        RequestContext.set_correlation_id(parent_id)

        async def child_modifier() -> None:
            """Child task that modifies the correlation ID."""
            RequestContext.set_correlation_id("child-modified")

        # Run child task in separate context using create_task
        task = asyncio.create_task(child_modifier())
        await task

        # Verify parent context unchanged
        parent_result = RequestContext.get_correlation_id()
        assert parent_result == parent_id, (
            f"Parent context should remain unchanged: "
            f"expected '{parent_id}', got '{parent_result}'"
        )

    # generate_correlation_id() Tests

    def test_generate_correlation_id_returns_string(self) -> None:
        """Test that generate_correlation_id returns a string."""
        result = generate_correlation_id()
        assert isinstance(result, str), f"Expected string, got {type(result).__name__}"

    def test_generate_correlation_id_returns_valid_uuid4(self) -> None:
        """Test that generate_correlation_id returns valid UUID4 format."""
        correlation_id = generate_correlation_id()

        # Validate UUID4 format
        try:
            parsed_uuid = uuid.UUID(correlation_id, version=4)
            assert str(parsed_uuid) == correlation_id
        except (ValueError, AttributeError) as e:
            pytest.fail(f"Invalid UUID4 format: {correlation_id}, error: {e}")

    @pytest.mark.parametrize("count", [2, 5, 10])
    def test_generate_correlation_id_returns_unique_values(self, count: int) -> None:
        """Test that generate_correlation_id generates unique values."""
        generated_ids = [generate_correlation_id() for _ in range(count)]

        # Check all IDs are unique
        unique_ids = set(generated_ids)
        assert len(unique_ids) == count, (
            f"Expected {count} unique IDs, got {len(unique_ids)}"
        )

    def test_generate_correlation_id_length_is_36_characters(self) -> None:
        """Test that UUID4 string is exactly 36 characters."""
        correlation_id = generate_correlation_id()
        assert len(correlation_id) == 36, (
            f"UUID4 should be 36 characters, got {len(correlation_id)}"
        )

    # generate_request_id() Tests

    def test_generate_request_id_returns_string(self) -> None:
        """Test that generate_request_id returns a string."""
        result = generate_request_id()
        assert isinstance(result, str), f"Expected string, got {type(result).__name__}"

    def test_generate_request_id_has_req_prefix(self) -> None:
        """Test that generate_request_id returns string starting with 'req-'."""
        request_id = generate_request_id()
        assert request_id.startswith("req-"), (
            f"Request ID should start with 'req-', got: {request_id}"
        )

    def test_generate_request_id_returns_valid_uuid4_after_prefix(self) -> None:
        """Test that the part after 'req-' is valid UUID4."""
        request_id = generate_request_id()

        # Extract UUID part
        prefix = "req-"
        assert request_id.startswith(prefix)
        uuid_part = request_id[len(prefix) :]

        # Validate UUID4 format
        try:
            parsed_uuid = uuid.UUID(uuid_part, version=4)
            assert str(parsed_uuid) == uuid_part
        except (ValueError, AttributeError) as e:
            pytest.fail(f"Invalid UUID4 format after prefix: {uuid_part}, error: {e}")

    @pytest.mark.parametrize("count", [2, 5, 10])
    def test_generate_request_id_returns_unique_values(self, count: int) -> None:
        """Test that generate_request_id generates unique values."""
        generated_ids = [generate_request_id() for _ in range(count)]

        # Check all IDs are unique
        unique_ids = set(generated_ids)
        assert len(unique_ids) == count, (
            f"Expected {count} unique IDs, got {len(unique_ids)}"
        )

    def test_generate_request_id_length_is_40_characters(self) -> None:
        """Test that request ID is exactly 40 characters."""
        request_id = generate_request_id()
        assert len(request_id) == 40, (
            f"Request ID should be 40 characters (req- + 36), got {len(request_id)}"
        )

    # Integration and Edge Case Tests

    def test_full_workflow_set_get_clear(self) -> None:
        """Test complete workflow of setting, getting, and clearing correlation ID."""
        # Initial state - should be None
        assert RequestContext.get_correlation_id() is None

        # Set correlation ID
        test_id = "workflow-test-id"
        RequestContext.set_correlation_id(test_id)
        assert RequestContext.get_correlation_id() == test_id

        # Clear context
        RequestContext.clear()
        assert RequestContext.get_correlation_id() is None

        # Set new ID after clear
        new_id = "new-workflow-id"
        RequestContext.set_correlation_id(new_id)
        assert RequestContext.get_correlation_id() == new_id

    def test_context_survives_multiple_operations(self) -> None:
        """Test that context remains stable through multiple get operations."""
        test_id = "stable-context-id"
        RequestContext.set_correlation_id(test_id)

        # Multiple get operations should return same value
        for i in range(10):
            result = RequestContext.get_correlation_id()
            assert result == test_id, (
                f"Get operation {i} returned unexpected value: "
                f"expected '{test_id}', got '{result}'"
            )
