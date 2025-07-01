"""Basic tests for Loguru logging configuration."""

import asyncio
import logging
import logging as std_logging
import sys
from collections.abc import Generator
from io import StringIO
from typing import Literal, NoReturn

import pytest
from loguru import logger

from src.core.config import LogConfig, Settings
from src.core.logging import (
    InterceptHandler,
    _state,
    bind_context,
    get_logger,
    setup_logging,
)


@pytest.mark.unit
class TestLoggingSetup:
    """Test basic logging setup."""

    @pytest.fixture(autouse=True)
    def cleanup_logger(self) -> Generator[None]:
        """Clean up logger handlers after each test."""
        yield
        # Remove all handlers after test
        logger.remove()
        # Note: We don't restore handlers as they're complex objects
        # Tests should set up their own handlers as needed

    def test_setup_logging_basic(self) -> None:
        """Test basic logging setup."""
        # Remove existing handlers
        logger.remove()

        # Setup logging
        # Create a mock settings that implements the protocol
        class MockSettings:
            def __init__(
                self,
                log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
            ) -> None:
                self._log_config = LogConfig(log_level=log_level)
                self._debug = False

            @property
            def log_config(self) -> LogConfig:
                return self._log_config

            @property
            def debug(self) -> bool:
                return self._debug

        mock_settings = MockSettings("INFO")
        setup_logging(mock_settings)

        # Create string buffer to capture output
        output = StringIO()

        # Add test handler
        logger.add(output, format="{level} | {message}", level="INFO")

        # Test logging
        logger.info("Test message")

        # Check output
        assert "INFO | Test message" in output.getvalue()

    def test_get_logger_compatibility(self) -> None:
        """Test get_logger function for backward compatibility."""
        test_logger = get_logger("test.module")

        # Should return a bound logger
        assert hasattr(test_logger, "info")
        assert hasattr(test_logger, "error")
        assert hasattr(test_logger, "debug")

    def test_log_levels(self) -> None:
        """Test different log levels."""

        # Create a mock settings that implements the protocol
        class MockSettings:
            def __init__(self) -> None:
                self._log_config = LogConfig(log_level="WARNING")
                self._debug = False

            @property
            def log_config(self) -> LogConfig:
                return self._log_config

            @property
            def debug(self) -> bool:
                return self._debug

        mock_settings = MockSettings()

        logger.remove()
        setup_logging(mock_settings)

        # Create string buffer
        output = StringIO()
        logger.add(output, format="{level} | {message}", level="WARNING")

        # Test different levels
        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")

        output_text = output.getvalue()

        # Only WARNING and ERROR should appear
        assert "Debug message" not in output_text
        assert "Info message" not in output_text
        assert "WARNING | Warning message" in output_text
        assert "ERROR | Error message" in output_text

    def test_exception_logging(self) -> None:
        """Test exception logging."""
        output = StringIO()
        logger.remove()
        logger.add(output, format="{level} | {message}", level="ERROR")

        try:
            raise ValueError("Test error")
        except ValueError:
            logger.exception("Error occurred")

        output_text = output.getvalue()
        assert "ERROR | Error occurred" in output_text
        assert "ValueError: Test error" in output_text

    @pytest.mark.asyncio
    async def test_async_logging(self) -> None:
        """Test logging in async context."""
        output = StringIO()
        logger.remove()
        logger.add(output, format="{message}", level="INFO", enqueue=True)

        async def async_function() -> None:
            logger.info("Async log message")

        await async_function()

        # Allow time for enqueued message
        await asyncio.sleep(0.1)

        assert "Async log message" in output.getvalue()


@pytest.mark.unit
class TestInterceptHandler:
    """Test standard library logging interception."""

    def test_standard_library_interception(self) -> None:
        """Test that standard library logs are captured."""

        # Setup logging with mock
        class MockSettings:
            def __init__(self) -> None:
                self._log_config = LogConfig(log_level="INFO")
                self._debug = False

            @property
            def log_config(self) -> LogConfig:
                return self._log_config

            @property
            def debug(self) -> bool:
                return self._debug

        mock_settings = MockSettings()
        logger.remove()
        setup_logging(mock_settings)

        # Create string buffer
        output = StringIO()
        logger.add(output, format="{message}", level="INFO")

        # Use standard library logger
        std_logger = std_logging.getLogger("test.stdlib")
        std_logger.info("Standard library message")

        assert "Standard library message" in output.getvalue()


@pytest.mark.unit
class TestUtilityFunctions:
    """Test utility functions in logging module."""

    def test_bind_context(self) -> None:
        """Test bind_context function."""
        # Remove handlers first
        logger.remove()

        # Create string buffer
        output = StringIO()
        logger.add(output, format="{extra[user_id]} | {message}", level="INFO")

        # Bind context
        bind_context(user_id=123, request_id="test")

        # Test logging with bound context
        logger.info("Test message")

        output_text = output.getvalue()
        assert "123 | Test message" in output_text

    def test_setup_logging_only_once(self) -> None:
        """Test that setup_logging is only called once."""
        # Reset state for this test
        _state.configured = False

        class MockSettings:
            def __init__(self) -> None:
                self._log_config = LogConfig(log_level="INFO")
                self._debug = False

            @property
            def log_config(self) -> LogConfig:
                return self._log_config

            @property
            def debug(self) -> bool:
                return self._debug

        mock_settings = MockSettings()

        # Clear handlers
        logger.remove()

        # First call should configure
        setup_logging(mock_settings)
        assert _state.configured is True

        # Add a test handler to track if setup_logging adds more handlers
        test_output = StringIO()
        logger.add(test_output, format="{message}", level="INFO")

        # Log a test message
        logger.info("Test message 1")

        # Second call should be a no-op due to _state.configured check
        setup_logging(mock_settings)

        # The same test handler should still work without duplication
        logger.info("Test message 2")
        second_output = test_output.getvalue()

        # Verify we still have our messages without handler duplication
        assert "Test message 1" in second_output
        assert "Test message 2" in second_output
        # If handlers were duplicated, we might see duplicate messages
        assert second_output.count("Test message 1") == 1


@pytest.mark.unit
class TestInterceptHandlerEdgeCases:
    """Test edge cases in InterceptHandler."""

    def test_intercept_handler_frame_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test InterceptHandler when frame access fails."""
        handler = InterceptHandler()

        # Create a mock log record
        record = std_logging.LogRecord(
            name="test",
            level=std_logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        def mock_getframe(depth: int) -> NoReturn:
            del depth  # Unused in mock
            raise ValueError("call stack is not deep enough")

        # Use monkeypatch to properly mock sys._getframe
        monkeypatch.setattr(sys, "_getframe", mock_getframe)

        # This should not raise an exception
        logger.remove()
        output = StringIO()
        logger.add(output, format="{message}", level="INFO")

        handler.emit(record)

        # Should still log the message
        assert "Test message" in output.getvalue()

    def test_intercept_handler_constructor(self) -> None:
        """Test InterceptHandler constructor."""
        # Should be able to create instance
        handler = InterceptHandler()
        assert isinstance(handler, std_logging.Handler)

    def test_intercept_handler_while_loop(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test InterceptHandler frame traversal logic."""
        handler = InterceptHandler()

        # Create a mock log record
        record = std_logging.LogRecord(
            name="test",
            level=std_logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        # Store original for fallback
        original_getframe = sys._getframe

        call_count = 0

        def mock_getframe(depth: int) -> object:
            nonlocal call_count
            call_count += 1

            if call_count == 1:
                # Return a frame that matches logging.__file__ with f_back
                # that continues loop
                class MockFrame:
                    f_code = type("obj", (object,), {"co_filename": logging.__file__})()
                    f_back = type(
                        "obj",
                        (object,),
                        {
                            "f_code": type(
                                "obj", (object,), {"co_filename": logging.__file__}
                            )(),
                            "f_back": None,  # This will eventually trigger break
                        },
                    )()

                # Return the mock frame
                return MockFrame()
            return original_getframe(depth)

        # Use monkeypatch to properly mock sys._getframe
        monkeypatch.setattr(sys, "_getframe", mock_getframe)

        logger.remove()
        output = StringIO()
        logger.add(output, format="{message}", level="INFO")

        handler.emit(record)

        # Should still log the message after frame traversal
        assert "Test message" in output.getvalue()

    def test_structured_sink_coverage(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test structured sink function in setup_logging for coverage."""
        # Track calls
        write_calls = []
        flush_calls = []

        # Mock stdout to verify write/flush calls
        class MockStdout:
            def write(self, data: str) -> None:
                write_calls.append(data)

            def flush(self) -> None:
                flush_calls.append(True)

        mock_stdout = MockStdout()
        monkeypatch.setattr("sys.stdout", mock_stdout)

        # Setup with JSON formatter to use structured sink
        settings = Settings(log_config=LogConfig(log_formatter_type="json"))

        logger.remove()
        _state.configured = False
        setup_logging(settings)

        # Log a message to trigger the structured sink
        logger.info("Test structured sink coverage")

        # Wait for async processing
        logger.complete()

        # Verify write and flush were called
        assert len(write_calls) > 0
        assert len(flush_calls) > 0
