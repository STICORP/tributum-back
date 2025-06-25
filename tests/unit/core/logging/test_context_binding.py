"""Unit tests for logger context binding functionality."""

import asyncio
from collections.abc import Generator
from typing import Any

import pytest
import structlog
from structlog.testing import LogCapture

from src.core.context import RequestContext
from src.core.logging import (
    add_log_level_upper,
    bind_logger_context,
    clear_logger_context,
    configure_structlog,
    get_logger,
    inject_correlation_id,
    inject_logger_context,
)


@pytest.mark.unit
class TestLoggerContextBinding:
    """Test logger context binding and propagation."""

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self) -> Generator[None]:
        """Set up structlog and clean up context after each test."""
        configure_structlog()
        yield
        clear_logger_context()
        RequestContext.clear()
        structlog.reset_defaults()

    def test_bind_logger_context_adds_fields(self) -> None:
        """Test that bind_logger_context adds fields to all logs."""
        cap = LogCapture()
        structlog.configure(
            processors=[
                add_log_level_upper,
                inject_logger_context,
                cap,
            ]
        )

        # Bind context
        bind_logger_context(user_id=123, session_id="abc-123")

        # Create logger and log
        logger = get_logger("test")
        logger.info("test message")

        assert len(cap.entries) == 1
        entry = cap.entries[0]
        assert entry["user_id"] == 123
        assert entry["session_id"] == "abc-123"
        assert entry["event"] == "test message"

    def test_clear_logger_context_removes_fields(self) -> None:
        """Test that clear_logger_context removes all context fields."""
        cap = LogCapture()
        structlog.configure(
            processors=[
                inject_logger_context,
                cap,
            ]
        )

        # Bind and then clear context
        bind_logger_context(user_id=123)
        clear_logger_context()

        # Log should not have context fields
        logger = get_logger()
        logger.info("after clear")

        assert len(cap.entries) == 1
        entry = cap.entries[0]
        assert "user_id" not in entry

    def test_multiple_bind_calls_accumulate(self) -> None:
        """Test that multiple bind calls accumulate context."""
        cap = LogCapture()
        structlog.configure(
            processors=[
                inject_logger_context,
                cap,
            ]
        )

        # Bind context in multiple calls
        bind_logger_context(user_id=123)
        bind_logger_context(session_id="session-456")
        bind_logger_context(request_id="req-789")

        logger = get_logger()
        logger.info("accumulated context")

        assert len(cap.entries) == 1
        entry = cap.entries[0]
        assert entry["user_id"] == 123
        assert entry["session_id"] == "session-456"
        assert entry["request_id"] == "req-789"

    def test_bind_overwrites_existing_keys(self) -> None:
        """Test that binding the same key overwrites the previous value."""
        cap = LogCapture()
        structlog.configure(
            processors=[
                inject_logger_context,
                cap,
            ]
        )

        bind_logger_context(user_id=123)
        bind_logger_context(user_id=456)  # Overwrite

        logger = get_logger()
        logger.info("overwritten context")

        assert len(cap.entries) == 1
        assert cap.entries[0]["user_id"] == 456

    async def test_async_context_propagation(self) -> None:
        """Test that context propagates correctly across async calls."""
        cap = LogCapture()
        structlog.configure(
            processors=[
                inject_logger_context,
                cap,
            ]
        )

        async def async_function() -> None:
            """Log within async function."""
            logger = get_logger()
            logger.info("async log")

        # Bind context and call async function
        bind_logger_context(async_context="test-async")
        await async_function()

        assert len(cap.entries) == 1
        assert cap.entries[0]["async_context"] == "test-async"

    async def test_multiple_concurrent_contexts(self) -> None:
        """Test that multiple concurrent async contexts remain isolated."""
        cap = LogCapture()
        structlog.configure(
            processors=[
                inject_logger_context,
                cap,
            ]
        )

        async def task_with_context(task_id: int, delay: float) -> None:
            """Simulate a task with its own context."""
            bind_logger_context(task_id=task_id)
            logger = get_logger()
            logger.info("task start")
            await asyncio.sleep(delay)
            logger.info("task end")

        # Run multiple tasks concurrently
        await asyncio.gather(
            task_with_context(1, 0.01),
            task_with_context(2, 0.02),
            task_with_context(3, 0.01),
        )

        # Verify each task maintained its own context
        assert len(cap.entries) == 6  # 2 logs per task

        # Group entries by task_id
        task_logs: dict[int, list[dict[str, Any]]] = {}
        for entry in cap.entries:
            task_id = entry["task_id"]
            if task_id not in task_logs:
                task_logs[task_id] = []
            task_logs[task_id].append(dict(entry))

        # Verify each task has consistent context
        for task_id, logs in task_logs.items():
            assert len(logs) == 2
            assert all(log["task_id"] == task_id for log in logs)
            assert logs[0]["event"] == "task start"
            assert logs[1]["event"] == "task end"

    async def test_context_cleanup_after_async_task(self) -> None:
        """Test that context is properly cleaned up after async tasks."""
        cap = LogCapture()
        structlog.configure(
            processors=[
                inject_logger_context,
                cap,
            ]
        )

        async def task_with_cleanup() -> None:
            """Task that sets and clears context."""
            bind_logger_context(task_context="temporary")
            logger = get_logger()
            logger.info("with context")
            clear_logger_context()
            logger.info("after cleanup")

        await task_with_cleanup()

        assert len(cap.entries) == 2
        assert cap.entries[0]["task_context"] == "temporary"
        assert "task_context" not in cap.entries[1]

    def test_context_with_correlation_id(self) -> None:
        """Test that logger context works alongside correlation ID."""
        cap = LogCapture()
        structlog.configure(
            processors=[
                inject_correlation_id,
                inject_logger_context,
                cap,
            ]
        )

        # Set both correlation ID and logger context
        RequestContext.set_correlation_id("corr-123")
        bind_logger_context(user_id=456)

        logger = get_logger()
        logger.info("both contexts")

        assert len(cap.entries) == 1
        entry = cap.entries[0]
        assert entry["correlation_id"] == "corr-123"
        assert entry["user_id"] == 456

    async def test_nested_async_context_isolation(self) -> None:
        """Test that nested async contexts maintain proper isolation."""
        cap = LogCapture()
        structlog.configure(
            processors=[
                inject_logger_context,
                cap,
            ]
        )

        async def outer_task() -> None:
            """Outer async task."""
            bind_logger_context(level="outer")
            logger = get_logger()
            logger.info("outer start")

            async def inner_task() -> None:
                """Inner async task with its own context."""
                bind_logger_context(level="inner", inner_only="yes")
                inner_logger = get_logger()
                inner_logger.info("inner log")

            await inner_task()
            logger.info("outer end")

        await outer_task()

        assert len(cap.entries) == 3
        # Outer start should only have outer context
        assert cap.entries[0]["level"] == "outer"
        assert "inner_only" not in cap.entries[0]

        # Inner should have both contexts merged
        assert cap.entries[1]["level"] == "inner"
        assert cap.entries[1]["inner_only"] == "yes"

        # Outer end should have updated level from inner
        assert cap.entries[2]["level"] == "inner"
        assert cap.entries[2]["inner_only"] == "yes"
