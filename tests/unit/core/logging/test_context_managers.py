"""Unit tests for logging context managers."""

import asyncio
from collections.abc import Generator

import pytest
import structlog
from structlog.testing import LogCapture

from src.core.constants import MAX_CONTEXT_DEPTH
from src.core.logging import (
    LogContextManager,
    MergeStrategy,
    _context_manager,
    clear_logger_context,
    configure_structlog,
    get_logger,
    get_logger_context,
    inject_logger_context,
    log_context,
)


@pytest.mark.unit
class TestLogContext:
    """Test the log_context context manager."""

    @pytest.fixture(autouse=True)
    def setup_structlog(self) -> Generator[None]:
        """Set up structlog for tests."""
        configure_structlog()
        yield
        # Reset structlog
        structlog.reset_defaults()

    def test_log_context_adds_bindings(self) -> None:
        """Test that log_context adds temporary bindings."""
        cap = LogCapture()
        structlog.configure(
            processors=[
                structlog.stdlib.add_logger_name,
                cap,
            ]
        )

        with log_context(user_id=123, request_id="abc") as logger:
            logger.info("test event")

        assert len(cap.entries) == 1
        entry = cap.entries[0]
        assert entry["event"] == "test event"
        assert entry["user_id"] == 123
        assert entry["request_id"] == "abc"

    def test_log_context_isolation(self) -> None:
        """Test that context bindings are isolated."""
        cap = LogCapture()
        structlog.configure(processors=[cap])

        # Log before context
        logger1 = get_logger()
        logger1.info("before context")

        # Log within context
        with log_context(temp_key="temp_value") as logger2:
            logger2.info("within context")

        # Log after context
        logger3 = get_logger()
        logger3.info("after context")

        assert len(cap.entries) == 3

        # First log should not have temp_key
        assert "temp_key" not in cap.entries[0]

        # Second log should have temp_key
        assert cap.entries[1]["temp_key"] == "temp_value"

        # Third log should not have temp_key
        assert "temp_key" not in cap.entries[2]

    def test_nested_log_contexts(self) -> None:
        """Test nested log contexts."""
        cap = LogCapture()
        structlog.configure(processors=[cap])

        with log_context(level1="value1") as logger1:
            logger1.info("level 1")

            # Inner context should have both bindings
            with log_context(level2="value2") as logger2:
                logger2.info("level 2")

        assert len(cap.entries) == 2

        # First entry should only have level1
        assert cap.entries[0]["level1"] == "value1"
        assert "level2" not in cap.entries[0]

        # Second entry should have level2 but not level1
        # (because we get a new logger in the inner context)
        assert cap.entries[1]["level2"] == "value2"
        assert "level1" not in cap.entries[1]

    def test_log_context_with_empty_bindings(self) -> None:
        """Test log_context with no bindings."""
        cap = LogCapture()
        structlog.configure(processors=[cap])

        with log_context() as logger:
            logger.info("no bindings")

        assert len(cap.entries) == 1
        assert cap.entries[0]["event"] == "no bindings"


@pytest.mark.unit
class TestLogContextManager:
    """Test the LogContextManager class."""

    @pytest.fixture
    def manager(self) -> LogContextManager:
        """Create a fresh LogContextManager for each test."""
        return LogContextManager()

    def test_push_single_layer(self, manager: LogContextManager) -> None:
        """Test pushing a single context layer."""
        manager.push(user_id=123, action="login")

        assert manager.depth == 1
        assert manager.peek() == {"user_id": 123, "action": "login"}

    def test_push_multiple_layers(self, manager: LogContextManager) -> None:
        """Test pushing multiple context layers."""
        manager.push(level1="value1")
        manager.push(level2="value2")
        manager.push(level3="value3")

        assert manager.depth == 3
        # Later layers override earlier ones
        context = manager.peek()
        assert context == {"level1": "value1", "level2": "value2", "level3": "value3"}

    def test_push_max_depth_exceeded(self, manager: LogContextManager) -> None:
        """Test that pushing beyond max depth raises error."""
        # Push to max depth
        for i in range(MAX_CONTEXT_DEPTH):
            manager.push(layer=i)

        # Try to exceed max depth
        with pytest.raises(
            RuntimeError, match=f"Context depth exceeded maximum of {MAX_CONTEXT_DEPTH}"
        ):
            manager.push(extra="layer")

    def test_pop_single_layer(self, manager: LogContextManager) -> None:
        """Test popping a single context layer."""
        manager.push(user_id=123)

        popped = manager.pop()

        assert popped == {"user_id": 123}
        assert manager.depth == 0
        assert manager.peek() == {}

    def test_pop_multiple_layers(self, manager: LogContextManager) -> None:
        """Test popping multiple context layers."""
        manager.push(layer1="value1")
        manager.push(layer2="value2")

        # Pop second layer
        popped2 = manager.pop()
        assert popped2 == {"layer2": "value2"}
        assert manager.peek() == {"layer1": "value1"}

        # Pop first layer
        popped1 = manager.pop()
        assert popped1 == {"layer1": "value1"}
        assert manager.peek() == {}

    def test_pop_empty_stack(self, manager: LogContextManager) -> None:
        """Test popping from empty stack returns None."""
        result = manager.pop()
        assert result is None

    def test_peek_empty_stack(self, manager: LogContextManager) -> None:
        """Test peeking at empty stack returns empty dict."""
        assert manager.peek() == {}

    def test_merge_shallow_strategy(self, manager: LogContextManager) -> None:
        """Test shallow merge strategy."""
        manager.push(config={"a": 1, "b": 2}, user="alice")
        manager.merge(
            {"config": {"b": 3, "c": 4}, "user": "bob"}, MergeStrategy.SHALLOW
        )

        context = manager.peek()
        # Shallow merge replaces entire values
        assert context == {"config": {"b": 3, "c": 4}, "user": "bob"}

    def test_merge_deep_strategy(self, manager: LogContextManager) -> None:
        """Test deep merge strategy."""
        manager.push(config={"a": 1, "b": 2}, user="alice")
        manager.merge({"config": {"b": 3, "c": 4}, "user": "bob"}, MergeStrategy.DEEP)

        context = manager.peek()
        # Deep merge combines nested dicts
        assert context == {"config": {"a": 1, "b": 3, "c": 4}, "user": "bob"}

    def test_merge_deep_nested(self, manager: LogContextManager) -> None:
        """Test deep merge with multiple nesting levels."""
        manager.push(
            settings={
                "database": {"host": "localhost", "port": 5432},
                "cache": {"enabled": True},
            }
        )
        manager.merge(
            {
                "settings": {
                    "database": {"port": 3306, "user": "root"},
                    "cache": {"ttl": 300},
                }
            },
            MergeStrategy.DEEP,
        )

        context = manager.peek()
        assert context == {
            "settings": {
                "database": {"host": "localhost", "port": 3306, "user": "root"},
                "cache": {"enabled": True, "ttl": 300},
            }
        }

    def test_merge_empty_stack(self, manager: LogContextManager) -> None:
        """Test merging into empty stack creates new layer."""
        manager.merge({"key": "value"})

        assert manager.depth == 1
        assert manager.peek() == {"key": "value"}

    def test_context_var_integration(self, manager: LogContextManager) -> None:
        """Test that LogContextManager updates the context var."""
        manager.push(test_key="test_value")

        # Check that the context var was updated
        current = get_logger_context()
        assert current == {"test_key": "test_value"}

    def test_deep_copy_in_deep_merge(self, manager: LogContextManager) -> None:
        """Test that deep merge creates copies of nested dicts."""
        original_dict = {"nested": {"value": 1}}
        manager.push(data=original_dict)

        # Modify the original
        original_dict["nested"]["value"] = 2

        # Context should still have original value
        context = manager.peek()
        assert context["data"]["nested"]["value"] == 1


@pytest.mark.unit
class TestEnhancedLogContext:
    """Test the enhanced log_context context manager."""

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self) -> Generator[None]:
        """Set up structlog and clean up context after each test."""
        configure_structlog()
        clear_logger_context()
        _context_manager._context_stack.clear()
        yield
        clear_logger_context()
        _context_manager._context_stack.clear()
        structlog.reset_defaults()

    def test_log_context_uses_context_manager(self) -> None:
        """Test that log_context now uses LogContextManager."""
        cap = LogCapture()
        structlog.configure(
            processors=[
                inject_logger_context,
                cap,
            ]
        )

        # Before context
        assert _context_manager.depth == 0

        with log_context(user_id=123, request_id="abc") as logger:
            # Inside context
            assert _context_manager.depth == 1
            logger.info("test event")

        # After context
        assert _context_manager.depth == 0

        # Verify log entry
        assert len(cap.entries) == 1
        entry = cap.entries[0]
        assert entry["user_id"] == 123
        assert entry["request_id"] == "abc"
        assert entry["context_depth"] == 1

    def test_nested_log_contexts_with_manager(self) -> None:
        """Test nested log contexts using the enhanced system."""
        cap = LogCapture()
        structlog.configure(
            processors=[
                inject_logger_context,
                cap,
            ]
        )

        with log_context(level1="value1") as logger1:
            logger1.info("outer")

            with log_context(level2="value2") as logger2:
                logger2.info("inner")
                assert _context_manager.depth == 2

            logger1.info("outer again")
            assert _context_manager.depth == 1

        assert _context_manager.depth == 0

        # Check logs
        assert len(cap.entries) == 3

        # First log - only level1
        assert cap.entries[0]["level1"] == "value1"
        assert "level2" not in cap.entries[0]
        assert cap.entries[0]["context_depth"] == 1

        # Second log - both levels
        assert cap.entries[1]["level1"] == "value1"
        assert cap.entries[1]["level2"] == "value2"
        assert cap.entries[1]["context_depth"] == 2

        # Third log - back to only level1
        assert cap.entries[2]["level1"] == "value1"
        assert "level2" not in cap.entries[2]
        assert cap.entries[2]["context_depth"] == 1

    def test_log_context_exception_cleanup(self) -> None:
        """Test that context is cleaned up even on exception."""
        assert _context_manager.depth == 0

        try:
            with log_context(temp="value"):
                assert _context_manager.depth == 1
                raise ValueError("Test exception")
        except ValueError:
            pass

        # Context should be cleaned up
        assert _context_manager.depth == 0

    async def test_log_context_async_compatibility(self) -> None:
        """Test log_context works correctly in async code."""
        cap = LogCapture()
        structlog.configure(
            processors=[
                inject_logger_context,
                cap,
            ]
        )

        async def async_operation() -> None:
            """Async operation using log context."""
            with log_context(async_op="test") as logger:
                logger.info("async log")
                await asyncio.sleep(0.01)
                logger.info("after sleep")

        await async_operation()

        assert len(cap.entries) == 2
        assert all(entry["async_op"] == "test" for entry in cap.entries)
