"""Tests for edge cases in logging module."""

import logging

import pytest
from pytest_mock import MockerFixture

from src.core.logging import (
    InterceptHandler,
    _format_extra_field,
    _format_level,
    _format_priority_field,
    _format_timestamp,
    format_console_with_context,
)


@pytest.mark.unit
class TestLoggingEdgeCases:
    """Test edge cases and error conditions in logging functions."""

    def test_format_priority_field_status_code_200(self) -> None:
        """Test formatting 2xx status codes (green)."""
        result = _format_priority_field("status_code", 200)
        assert result == "<green>200</green>"

    def test_format_priority_field_status_code_300(self) -> None:
        """Test formatting 3xx status codes (yellow)."""
        result = _format_priority_field("status_code", 301)
        assert result == "<yellow>301</yellow>"

    def test_format_priority_field_status_code_500(self) -> None:
        """Test formatting 5xx status codes (red bold)."""
        result = _format_priority_field("status_code", 503)
        assert result == "<red><bold>503</bold></red>"

    def test_format_priority_field_with_exception(self, mocker: MockerFixture) -> None:
        """Test format_priority_field when an exception occurs."""

        # Create a custom object that will cause AttributeError
        class BadValue:
            def __str__(self) -> str:
                raise AttributeError("Cannot convert to string")

        bad_value = BadValue()

        # Mock logger.trace to verify it's called
        mock_trace = mocker.patch("src.core.logging.logger.trace")

        result = _format_priority_field("test_field", bad_value)

        assert result is None
        mock_trace.assert_called_once()
        assert (
            "Failed to format priority field test_field" in mock_trace.call_args[0][0]
        )

    def test_format_extra_field_with_exception(self, mocker: MockerFixture) -> None:
        """Test format_extra_field when an exception occurs."""

        # Create a custom object that will cause TypeError
        class BadValue:
            def __str__(self) -> str:
                raise TypeError("Cannot convert")

        bad_value = BadValue()

        # Mock logger.trace to verify it's called
        mock_trace = mocker.patch("src.core.logging.logger.trace")

        result = _format_extra_field("bad_key", bad_value)

        assert result is None
        mock_trace.assert_called_once()
        assert "Failed to format extra field bad_key" in mock_trace.call_args[0][0]

    def test_format_timestamp_without_time(self) -> None:
        """Test _format_timestamp when time is missing."""
        record = {"time": None}
        result = _format_timestamp(record)
        assert result == "unknown"

    def test_format_level_without_name_attribute(self) -> None:
        """Test _format_level when level doesn't have name attribute."""
        record = {"level": "INFO"}  # String instead of object with name
        result = _format_level(record)
        assert result == "INFO"

    def test_format_console_with_context_exception(self, mocker: MockerFixture) -> None:
        """Test format_console_with_context when an exception occurs."""
        # Create a record that will cause an error
        bad_record = {"time": "not_a_datetime"}  # This will fail strftime

        # Mock logger.trace to verify it's called
        mock_trace = mocker.patch("src.core.logging.logger.trace")

        result = format_console_with_context(bad_record)

        # Should return default format
        assert "{time:" in result  # Default format contains this
        mock_trace.assert_called_once()
        assert "Failed to format log record" in mock_trace.call_args[0][0]

    def test_intercept_handler_uvicorn_access_logs(self, mocker: MockerFixture) -> None:
        """Test InterceptHandler processing uvicorn access logs with scope."""
        handler = InterceptHandler()

        # Create a mock LogRecord with uvicorn access log attributes
        record = logging.LogRecord(
            name="uvicorn.access",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        # Add uvicorn-specific scope attribute
        record.scope = {
            "method": "GET",
            "path": "/api/test",
            "client": ["192.168.1.100", 8000],
            "headers": [
                (b"x-correlation-id", b"test-correlation-id-123"),
                (b"user-agent", b"TestClient/1.0"),
            ],
        }

        # Mock logger methods
        mock_logger = mocker.patch("src.core.logging.logger")

        # Emit the record
        handler.emit(record)

        # Verify logger was called with proper context
        mock_logger.opt.assert_called_once()
        bind_call = mock_logger.opt.return_value.bind
        bind_call.assert_called_once()

        # Check that extra fields were extracted
        extra = bind_call.call_args[1]
        assert extra["method"] == "GET"
        assert extra["path"] == "/api/test"
        assert extra["client_host"] == "192.168.1.100"
        assert extra["correlation_id"] == "test-correlation-id-123"

    def test_intercept_handler_uvicorn_access_logs_empty_headers(
        self, mocker: MockerFixture
    ) -> None:
        """Test InterceptHandler with uvicorn logs but no correlation ID."""
        handler = InterceptHandler()

        # Create a mock LogRecord with uvicorn access log attributes
        record = logging.LogRecord(
            name="uvicorn.access",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        # Add uvicorn-specific scope attribute without correlation ID
        record.scope = {
            "method": "POST",
            "path": "/api/data",
            "client": ["10.0.0.1", 8080],
            "headers": [],  # Empty headers
        }

        # Mock logger methods
        mock_logger = mocker.patch("src.core.logging.logger")

        # Emit the record
        handler.emit(record)

        # Verify logger was called
        mock_logger.opt.assert_called_once()
        bind_call = mock_logger.opt.return_value.bind
        bind_call.assert_called_once()

        # Check that extra fields were extracted but no correlation_id
        extra = bind_call.call_args[1]
        assert extra["method"] == "POST"
        assert extra["path"] == "/api/data"
        assert extra["client_host"] == "10.0.0.1"
        assert "correlation_id" not in extra
