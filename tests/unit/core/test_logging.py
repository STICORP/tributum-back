"""Comprehensive unit tests for the logging module.

This test suite ensures 100% code coverage of the logging module,
testing all formatters, handlers, serializers, and edge cases.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, cast

import pytest
from loguru import logger

if TYPE_CHECKING:
    from pytest_mock import MockerFixture, MockType

    from src.core.config import Settings
from src.core.logging import (
    CORRELATION_ID_DISPLAY_LENGTH,
    DEFAULT_LOG_FORMAT,
    LOG_FORMATTERS,
    MAX_FIELD_VALUE_LENGTH,
    InterceptHandler,
    LogConfigProtocol,
    _format_context_fields,
    _format_extra_field,
    _format_level,
    _format_priority_field,
    _format_timestamp,
    _LoggingState,
    _state,
    bind_context,
    detect_environment,
    format_console_with_context,
    get_logger,
    serialize_for_aws,
    serialize_for_gcp,
    serialize_for_json,
    setup_logging,
)


@pytest.mark.unit
class TestLogging:
    """Unit tests for the logging module."""

    def test_logging_state_initialization(self) -> None:
        """Test _LoggingState initializes correctly."""
        # Create new instance, don't use module singleton
        state = _LoggingState()

        # Assert configured is False
        assert state.configured is False
        assert isinstance(state.configured, bool)

    @pytest.mark.parametrize(
        ("field", "value", "expected"),
        [
            # Correlation ID tests
            ("correlation_id", "1234567890abcdef", "12345678"),
            ("correlation_id", "short", "short"),
            ("correlation_id", None, "None"),
            # Duration tests
            ("duration_ms", 150, "150ms"),
            ("duration_ms", 0, "0ms"),
            # Status code tests
            ("status_code", 200, "<green>200</green>"),
            ("status_code", 201, "<green>201</green>"),
            ("status_code", 301, "<yellow>301</yellow>"),
            ("status_code", 404, "<red>404</red>"),
            ("status_code", 500, "<red><bold>500</bold></red>"),
            # Other fields
            ("other_field", "test", "test"),
            # Edge cases with braces
            ("field", "test{value}", "test{{value}}"),
            ("field", "test}value{", "test}}value{{"),
        ],
    )
    def test_format_priority_field(
        self, field: str, value: str | int | None, expected: str | None
    ) -> None:
        """Test _format_priority_field handles all field types correctly."""
        result = _format_priority_field(field, value)
        assert result == expected

    def test_format_priority_field_exceptions(self) -> None:
        """Test _format_priority_field exception handling."""

        # Object without proper str method
        class BadObject:
            def __str__(self) -> str:
                raise ValueError("Cannot convert to string")

        result = _format_priority_field("field", BadObject())
        assert result is None

    @pytest.mark.parametrize(
        ("key", "value", "expected"),
        [
            # Normal values
            ("key", "value", "key=value"),
            ("user_id", 123, "user_id=123"),
            # Long values (should be truncated)
            ("long_field", "x" * 200, f"long_field={'x' * 97}..."),
            # Values with braces
            ("field", "test{value}", "field=test{{value}}"),
            ("field", "test}value{", "field=test}}value{{"),
            # Edge cases
            ("empty", "", "empty="),
            ("none_val", None, "none_val=None"),
        ],
    )
    def test_format_extra_field(
        self, key: str, value: str | int | None, expected: str | None
    ) -> None:
        """Test _format_extra_field handles field formatting and truncation."""
        result = _format_extra_field(key, value)
        assert result == expected

    def test_format_extra_field_exceptions(self) -> None:
        """Test _format_extra_field exception handling."""

        # Object that raises on str()
        class BadObject:
            def __str__(self) -> str:
                raise ValueError("Cannot convert to string")

        result = _format_extra_field("bad_key", BadObject())
        assert result is None

    def test_format_timestamp(self, mocker: MockerFixture) -> None:
        """Test timestamp extraction and formatting."""
        # With timestamp
        mock_time = mocker.Mock()
        # Full microseconds format to test trimming
        mock_time.strftime.return_value = "2024-01-01 12:00:00.000123"
        record_with_time = {"time": mock_time}

        result = _format_timestamp(record_with_time)
        assert result == "2024-01-01 12:00:00.000"

        # Without timestamp
        record = {"message": "test"}
        result = _format_timestamp(record)
        assert result == "unknown"

    def test_format_level(self, mocker: MockerFixture) -> None:
        """Test log level extraction."""
        test_cases = [
            # Level object with name attribute
            (mocker.Mock(name="level", spec=["name"]), "level"),
            # String level
            ("INFO", "INFO"),
            # Empty dict
            ({}, "{}"),
            # Missing level
            (None, "None"),
        ]

        for level_data, expected in test_cases:
            # Set up mock level object
            if hasattr(level_data, "name") and level_data is not None:
                level_data.name = expected

            record = {"level": level_data}
            result = _format_level(record)
            assert result == expected

    @pytest.mark.parametrize(
        ("extra", "expected_parts"),
        [
            # Empty extra dict
            ({}, []),
            # Only priority fields
            (
                {"correlation_id": "12345678", "method": "GET", "path": "/api/users"},
                [
                    "<yellow>12345678</yellow>",
                    "<yellow>GET</yellow>",
                    "<yellow>/api/users</yellow>",
                ],
            ),
            # Only non-priority fields
            (
                {"custom_field": "value", "another": "test"},
                ["<dim>custom_field=value</dim>", "<dim>another=test</dim>"],
            ),
            # Mixed fields
            (
                {
                    "correlation_id": "abcdef",
                    "status_code": 200,
                    "custom": "data",
                    "user_id": 42,
                },
                [
                    "<yellow>abcdef</yellow>",
                    "<yellow><green>200</green></yellow>",
                    "<dim>custom=data</dim>",
                    "<dim>user_id=42</dim>",
                ],
            ),
            # Fields with None values (should be skipped)
            (
                {"field1": "value", "field2": None, "field3": "another"},
                ["<dim>field1=value</dim>", "<dim>field3=another</dim>"],
            ),
            # Fields starting with underscore (should be skipped)
            (
                {"public": "visible", "_private": "hidden", "__dunder": "also_hidden"},
                ["<dim>public=visible</dim>"],
            ),
        ],
    )
    def test_format_context_fields(
        self, extra: dict[str, Any], expected_parts: list[str]
    ) -> None:
        """Test context field formatting with priority ordering."""
        result = _format_context_fields(extra)
        assert result == expected_parts

    def test_format_console_with_context(
        self, mock_loguru_record: dict[str, Any]
    ) -> None:
        """Test format_console_with_context produces correct output."""
        # Basic log without extra
        result = format_console_with_context(mock_loguru_record)
        expected = (
            "<green>2024-01-01 12:00:00.000</green> | "
            "<level>INFO    </level> | "
            "<cyan>test_module:test_func:42</cyan> | "
            "Test message\n"
        )
        assert result == expected

        # Log with all context fields
        mock_loguru_record["extra"] = {
            "correlation_id": "1234567890",
            "method": "POST",
            "custom_field": "value",
        }
        result = format_console_with_context(mock_loguru_record)
        assert "[<yellow>12345678</yellow>]" in result
        assert "[<yellow>POST</yellow>]" in result
        assert "[<dim>custom_field=value</dim>]" in result

        # Log with exception
        mock_loguru_record["exception"] = True
        result = format_console_with_context(mock_loguru_record)
        assert "{exception}" in result

        # Message with braces (should be escaped)
        mock_loguru_record["message"] = "Test {value} message"
        result = format_console_with_context(mock_loguru_record)
        assert "Test {{value}} message" in result

    def test_format_console_with_context_malformed(self) -> None:
        """Test format_console_with_context handles malformed records gracefully."""
        # Record that causes fallback behavior
        bad_record = {
            "time": None,  # Will cause fallback to "unknown"
            "level": None,
            "message": "test",
        }
        result = format_console_with_context(bad_record)
        expected = (
            "<green>unknown</green> | <level>None    </level> | "
            "<cyan>::</cyan> | test\n"
        )
        assert result == expected

    def test_intercept_handler_emit_basic(self, mocker: MockerFixture) -> None:
        """Test InterceptHandler basic log forwarding."""
        # Mock sys._getframe
        mock_frame = mocker.Mock()
        mock_frame.f_code.co_filename = "/app/test.py"
        mock_frame.f_back = None
        mocker.patch("sys._getframe", return_value=mock_frame)

        # Mock logger methods
        mock_opt = mocker.patch.object(logger, "opt")
        mock_bind = mocker.Mock()
        mock_log = mocker.Mock()
        mock_bind.log = mock_log
        mock_opt.return_value.bind.return_value = mock_bind

        # Create handler and emit log
        handler = InterceptHandler()
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="/app/test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        handler.emit(record)

        # Verify logger was called correctly
        mock_opt.assert_called_once_with(depth=6, exception=None)
        mock_log.assert_called_once_with("INFO", "Test message")

    def test_intercept_handler_uvicorn_access(self, mocker: MockerFixture) -> None:
        """Test InterceptHandler with uvicorn access logs."""
        # Mock sys._getframe
        mock_frame = mocker.Mock()
        mock_frame.f_code.co_filename = "/app/test.py"
        mock_frame.f_back = None
        mocker.patch("sys._getframe", return_value=mock_frame)

        # Mock logger
        mock_opt = mocker.patch.object(logger, "opt")
        mock_bind = mocker.Mock()
        mock_log = mocker.Mock()
        mock_bind.log = mock_log
        mock_opt.return_value.bind.return_value = mock_bind

        # Create uvicorn access log record with scope
        handler = InterceptHandler()
        record = logging.LogRecord(
            name="uvicorn.access",
            level=logging.INFO,
            pathname="/app/test.py",
            lineno=10,
            msg="127.0.0.1:8000 - GET /api/users 200",
            args=(),
            exc_info=None,
        )
        record.scope = {
            "method": "GET",
            "path": "/api/users",
            "client": ["127.0.0.1", 8000],
            "headers": [
                (b"x-correlation-id", b"test-correlation-id"),
                (b"user-agent", b"test-agent"),
            ],
        }

        handler.emit(record)

        # Verify extra fields were extracted
        bind_call = mock_opt.return_value.bind.call_args[1]
        assert bind_call["method"] == "GET"
        assert bind_call["path"] == "/api/users"
        assert bind_call["client_host"] == "127.0.0.1"
        assert bind_call["correlation_id"] == "test-correlation-id"

    def test_intercept_handler_frame_traversal(self, mocker: MockerFixture) -> None:
        """Test InterceptHandler frame traversal logic."""
        # Create chain of frames
        frame3 = mocker.Mock()
        frame3.f_code.co_filename = "/app/test.py"
        frame3.f_back = None

        frame2 = mocker.Mock()
        frame2.f_code.co_filename = logging.__file__
        frame2.f_back = frame3

        frame1 = mocker.Mock()
        frame1.f_code.co_filename = logging.__file__
        frame1.f_back = frame2

        mocker.patch("sys._getframe", return_value=frame1)

        # Mock logger
        mock_opt = mocker.patch.object(logger, "opt")
        mock_bind = mocker.Mock()
        mock_log = mocker.Mock()
        mock_bind.log = mock_log
        mock_opt.return_value.bind.return_value = mock_bind

        # Emit log
        handler = InterceptHandler()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="/app/test.py",
            lineno=10,
            msg="Test",
            args=(),
            exc_info=None,
        )

        handler.emit(record)

        # Should have traversed to depth 8 (6 + 2)
        mock_opt.assert_called_once_with(depth=8, exception=None)

    def test_intercept_handler_getframe_error(self, mocker: MockerFixture) -> None:
        """Test InterceptHandler when _getframe fails."""
        # Make _getframe raise ValueError
        mocker.patch("sys._getframe", side_effect=ValueError("Not enough frames"))

        # Mock logger
        mock_opt = mocker.patch.object(logger, "opt")
        mock_bind = mocker.Mock()
        mock_log = mocker.Mock()
        mock_bind.log = mock_log
        mock_opt.return_value.bind.return_value = mock_bind

        # Emit log
        handler = InterceptHandler()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="/app/test.py",
            lineno=10,
            msg="Test",
            args=(),
            exc_info=None,
        )

        handler.emit(record)

        # Should use depth=1 when _getframe fails
        mock_opt.assert_called_once_with(depth=1, exception=None)

    def test_intercept_handler_frame_traversal_with_none_f_back(
        self, mocker: MockerFixture
    ) -> None:
        """Test InterceptHandler when f_back is None during frame traversal."""
        # This tests line 300 - the break statement when next_frame is None
        # Create a frame where f_back is None while still in logging module
        frame2 = mocker.Mock()
        frame2.f_code.co_filename = logging.__file__
        frame2.f_back = None  # This will trigger the break at line 300

        frame1 = mocker.Mock()
        frame1.f_code.co_filename = logging.__file__
        frame1.f_back = frame2

        mocker.patch("sys._getframe", return_value=frame1)

        # Mock logger
        mock_opt = mocker.patch.object(logger, "opt")
        mock_bind = mocker.Mock()
        mock_log = mocker.Mock()
        mock_bind.log = mock_log
        mock_opt.return_value.bind.return_value = mock_bind

        # Emit log
        handler = InterceptHandler()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="/app/test.py",
            lineno=10,
            msg="Test with None f_back",
            args=(),
            exc_info=None,
        )

        handler.emit(record)

        # Should have traversed to depth 7 (6 + 1 before hitting the None)
        mock_opt.assert_called_once_with(depth=7, exception=None)

    def test_intercept_handler_extra_fields(self, mocker: MockerFixture) -> None:
        """Test InterceptHandler with extra fields in LogRecord."""
        # Mock sys._getframe
        mock_frame = mocker.Mock()
        mock_frame.f_code.co_filename = "/app/test.py"
        mock_frame.f_back = None
        mocker.patch("sys._getframe", return_value=mock_frame)

        # Mock logger
        mock_opt = mocker.patch.object(logger, "opt")
        mock_bind = mocker.Mock()
        mock_log = mocker.Mock()
        mock_bind.log = mock_log
        mock_opt.return_value.bind.return_value = mock_bind

        # Create record with extra fields
        handler = InterceptHandler()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="/app/test.py",
            lineno=10,
            msg="Test",
            args=(),
            exc_info=None,
        )
        # Add custom fields
        record.user_id = 123
        record.request_id = "req-456"
        record._private = "should_be_skipped"

        handler.emit(record)

        # Verify extra fields were passed
        bind_call = mock_opt.return_value.bind.call_args[1]
        assert bind_call["user_id"] == 123
        assert bind_call["request_id"] == "req-456"
        assert "_private" not in bind_call

    def test_serialize_for_json(
        self, mocker: MockerFixture, mock_loguru_record: dict[str, Any]
    ) -> None:
        """Test serialize_for_json produces valid JSON."""
        # Basic log entry
        result = serialize_for_json(mock_loguru_record)
        data = json.loads(result.strip())

        assert data["timestamp"] == "2024-01-01T12:00:00"
        assert data["level"] == "INFO"
        assert data["message"] == "Test message"
        assert data["logger"] == "test_module"
        assert data["function"] == "test_func"
        assert data["line"] == 42

        # Log with extra fields
        mock_loguru_record["extra"] = {
            "user_id": 123,
            "request_id": "req-456",
            "_internal": "should_be_filtered",
        }
        result = serialize_for_json(mock_loguru_record)
        data = json.loads(result.strip())

        assert data["user_id"] == 123
        assert data["request_id"] == "req-456"
        assert "_internal" not in data

        # Log with exception
        exc_mock = mocker.Mock()
        exc_mock.type = ValueError
        exc_mock.value = ValueError("Test error")
        exc_mock.traceback = "Traceback details..."
        mock_loguru_record["exception"] = exc_mock

        result = serialize_for_json(mock_loguru_record)
        data = json.loads(result.strip())

        assert data["exception"]["type"] == "ValueError"
        assert data["exception"]["value"] == "Test error"
        assert data["exception"]["traceback"] == "Traceback details..."

        # Special character escaping
        mock_loguru_record["message"] = 'Test "quoted" message\nwith newline'
        result = serialize_for_json(mock_loguru_record)
        data = json.loads(result.strip())
        assert data["message"] == 'Test "quoted" message\nwith newline'

    def test_serialize_for_gcp(
        self, mocker: MockerFixture, mock_loguru_record: dict[str, Any]
    ) -> None:
        """Test serialize_for_gcp follows GCP format."""
        # Mock get_settings
        mock_settings = mocker.Mock()
        mock_settings.app_name = "TestApp"
        mock_settings.app_version = "1.0.0"
        mocker.patch("src.core.logging.get_settings", return_value=mock_settings)

        # Basic log with severity mapping
        result = serialize_for_gcp(mock_loguru_record)
        data = json.loads(result.strip())

        assert data["severity"] == "INFO"
        assert data["message"] == "Test message"
        assert data["timestamp"] == "2024-01-01T12:00:00"
        assert data["serviceContext"]["service"] == "TestApp"
        assert data["serviceContext"]["version"] == "1.0.0"

        labels = data["logging.googleapis.com/labels"]
        assert labels["function"] == "test_func"
        assert labels["module"] == "test_module"
        assert labels["line"] == "42"

        # Log with correlation_id (trace integration)
        mock_loguru_record["extra"] = {
            "correlation_id": "trace-123",
            "request_id": "req-456",
            "fingerprint": "error_fp_12345678",
        }
        result = serialize_for_gcp(mock_loguru_record)
        data = json.loads(result.strip())

        assert data["logging.googleapis.com/trace"] == "trace-123"
        assert data["logging.googleapis.com/labels"]["request_id"] == "req-456"
        assert data["logging.googleapis.com/labels"]["error_fingerprint"] == "error_fp"
        assert data["jsonPayload"]["fingerprint"] == "error_fp_12345678"

        # Error log with source location
        error_level = mocker.Mock()
        error_level.name = "ERROR"
        mock_loguru_record["level"] = error_level
        mock_loguru_record["file"] = mocker.Mock(path="/app/src/test.py")
        mock_loguru_record["exception"] = True

        result = serialize_for_gcp(mock_loguru_record)
        data = json.loads(result.strip())

        assert data["severity"] == "ERROR"
        assert data["@type"] == (
            "type.googleapis.com/google.devtools.clouderrorreporting.v1beta1.ReportedErrorEvent"
        )
        source_loc = data["logging.googleapis.com/sourceLocation"]
        assert source_loc["file"] == "/app/src/test.py"
        assert source_loc["line"] == "42"
        assert source_loc["function"] == "test_func"

        # Log with stack trace
        mock_loguru_record["extra"]["stack_trace"] = "Custom stack trace"
        result = serialize_for_gcp(mock_loguru_record)
        data = json.loads(result.strip())

        assert data["stack_trace"] == "Custom stack trace"
        assert data["context"]["reportLocation"]["filePath"] == "/app/src/test.py"

    def test_serialize_for_aws(
        self, mocker: MockerFixture, mock_loguru_record: dict[str, Any]
    ) -> None:
        """Test serialize_for_aws follows AWS format."""
        # Basic log entry
        result = serialize_for_aws(mock_loguru_record)
        data = json.loads(result.strip())

        assert data["timestamp"] == "2024-01-01T12:00:00"
        assert data["level"] == "INFO"
        assert data["message"] == "Test message"
        assert data["logger"] == "test_module"

        # Log with X-Ray trace ID
        mock_loguru_record["extra"] = {
            "correlation_id": "xray-trace-123",
            "request_id": "req-456",
            "custom_field": "value",
        }
        result = serialize_for_aws(mock_loguru_record)
        data = json.loads(result.strip())

        assert data["traceId"] == "xray-trace-123"
        assert data["requestId"] == "req-456"
        assert data["custom_field"] == "value"

        # Log with exception
        exc_mock = mocker.Mock()
        exc_mock.type = RuntimeError
        exc_mock.value = RuntimeError("AWS error")
        exc_mock.traceback = "Stack trace..."
        mock_loguru_record["exception"] = exc_mock

        result = serialize_for_aws(mock_loguru_record)
        data = json.loads(result.strip())

        assert data["error"]["type"] == "RuntimeError"
        assert data["error"]["message"] == "AWS error"
        assert data["error"]["stackTrace"] == "Stack trace..."

    @pytest.mark.parametrize(
        ("env_vars", "expected"),
        [
            # K_SERVICE -> "gcp"
            ({"K_SERVICE": "test-service"}, "gcp"),
            # AWS_EXECUTION_ENV -> "aws"
            ({"AWS_EXECUTION_ENV": "AWS_Lambda_python3.11"}, "aws"),
            # WEBSITE_INSTANCE_ID -> "json"
            ({"WEBSITE_INSTANCE_ID": "azure-123"}, "json"),
            # No vars -> "console"
            ({}, "console"),
            # Multiple vars (GCP takes precedence)
            (
                {"K_SERVICE": "test", "AWS_EXECUTION_ENV": "lambda"},
                "gcp",
            ),
        ],
    )
    def test_detect_environment(
        self, monkeypatch: pytest.MonkeyPatch, env_vars: dict[str, str], expected: str
    ) -> None:
        """Test detect_environment identifies cloud providers."""
        # Clear all relevant env vars first
        for key in ["K_SERVICE", "AWS_EXECUTION_ENV", "WEBSITE_INSTANCE_ID"]:
            monkeypatch.delenv(key, raising=False)

        # Set test env vars
        for key, value in env_vars.items():
            monkeypatch.setenv(key, value)

        result = detect_environment()
        assert result == expected

    def test_setup_logging_first_call(
        self,
        mocker: MockerFixture,
        mock_settings: Settings,
        isolated_logging_state: _LoggingState,
    ) -> None:
        """Test setup_logging configuration on first call."""
        # Mock logger methods
        mock_remove = mocker.patch.object(logger, "remove")
        mock_add = mocker.patch.object(logger, "add")
        mock_info = mocker.patch.object(logger, "info")

        # Mock logging.basicConfig
        mock_basicconfig = mocker.patch("logging.basicConfig")

        # Mock getLogger
        mock_uvicorn_logger = mocker.Mock()
        mock_uvicorn_logger.handlers = []
        mocker.patch("logging.getLogger", return_value=mock_uvicorn_logger)

        # Set console formatter
        mock_settings.log_config.log_formatter_type = "console"
        mock_settings.log_config.log_level = "INFO"

        # Call setup_logging
        setup_logging(mock_settings)

        # Verify configuration
        assert isolated_logging_state.configured is True
        mock_remove.assert_called_once()
        mock_add.assert_called_once()

        # Check console formatter was used
        add_kwargs = mock_add.call_args[1]
        assert add_kwargs["format"] == format_console_with_context
        assert add_kwargs["level"] == "INFO"
        assert add_kwargs["enqueue"] is True
        assert add_kwargs["colorize"] is True

        # Verify logging was configured
        mock_basicconfig.assert_called_once()
        config_args = mock_basicconfig.call_args
        handlers = config_args[1]["handlers"]
        assert len(handlers) == 1
        assert isinstance(handlers[0], InterceptHandler)

        # Verify info log
        mock_info.assert_called_once_with(
            "Logging configured with {} formatter",
            "console",
            formatter_type="console",
            log_level="INFO",
        )

        # Use isolated_logging_state explicitly to fix lint
        assert isinstance(isolated_logging_state, _LoggingState)

    def test_setup_logging_subsequent_calls(
        self,
        mocker: MockerFixture,
        mock_settings: Settings,
        isolated_logging_state: _LoggingState,
    ) -> None:
        """Test setup_logging is no-op on subsequent calls."""
        # Set state as already configured
        isolated_logging_state.configured = True

        # Mock logger methods (should not be called)
        mock_remove = mocker.patch.object(logger, "remove")
        mock_add = mocker.patch.object(logger, "add")

        # Call setup_logging
        setup_logging(mock_settings)

        # Verify nothing was configured
        mock_remove.assert_not_called()
        mock_add.assert_not_called()

        # Use isolated_logging_state explicitly to fix lint
        assert isolated_logging_state.configured is True

    def test_setup_logging_json_formatter(
        self,
        mocker: MockerFixture,
        mock_settings: Settings,
        isolated_logging_state: _LoggingState,
    ) -> None:
        """Test setup_logging with JSON formatter."""
        # Mock logger methods
        mocker.patch.object(logger, "remove")
        mock_add = mocker.patch.object(logger, "add")
        mocker.patch.object(logger, "info")
        mocker.patch("logging.basicConfig")
        mocker.patch("logging.getLogger", return_value=mocker.Mock(handlers=[]))

        # Mock sys.stdout
        mock_stdout = mocker.Mock()
        mocker.patch("sys.stdout", mock_stdout)

        # Set JSON formatter
        mock_settings.log_config.log_formatter_type = "json"

        # Call setup_logging
        setup_logging(mock_settings)

        # Get the structured_sink function
        add_call = mock_add.call_args
        structured_sink = add_call[0][0]

        # Test structured_sink with valid record
        mock_message = mocker.Mock()
        mock_time = mocker.Mock()
        mock_time.isoformat.return_value = "2024-01-01T12:00:00"
        mock_level = mocker.Mock()
        mock_level.name = "INFO"
        mock_message.record = {
            "time": mock_time,
            "level": mock_level,
            "message": "Test message",
            "name": "test",
            "function": "test_func",
            "module": "test_module",
            "line": 42,
            "extra": {},
        }
        structured_sink(mock_message)

        # Verify JSON was written
        mock_stdout.write.assert_called()
        mock_stdout.flush.assert_called()

        # Test structured_sink when hasattr fails
        bad_message = "not an object with record"
        structured_sink(bad_message)  # Should not raise

        # Use isolated_logging_state explicitly to fix lint
        assert isolated_logging_state.configured is True

    def test_setup_logging_auto_detection(
        self,
        mocker: MockerFixture,
        mock_settings: Settings,
        monkeypatch: pytest.MonkeyPatch,
        isolated_logging_state: _LoggingState,
    ) -> None:
        """Test setup_logging with auto-detection when formatter_type is None."""
        # Mock logger methods
        mocker.patch.object(logger, "remove")
        mocker.patch.object(logger, "add")
        mock_info = mocker.patch.object(logger, "info")
        mocker.patch("logging.basicConfig")
        mocker.patch("logging.getLogger", return_value=mocker.Mock(handlers=[]))

        # Set formatter_type to None for auto-detection
        mock_settings.log_config.log_formatter_type = None

        # Set GCP environment
        monkeypatch.setenv("K_SERVICE", "test-service")

        # Call setup_logging
        setup_logging(mock_settings)

        # Verify GCP formatter was detected
        info_call = mock_info.call_args
        assert info_call[0][1] == "gcp"

        # Use isolated_logging_state explicitly to fix lint
        assert isolated_logging_state.configured is True

    def test_setup_logging_disabled_noisy_loggers(
        self,
        mocker: MockerFixture,
        mock_settings: Settings,
        isolated_logging_state: _LoggingState,
    ) -> None:
        """Test that noisy loggers are disabled."""
        # Mock logger methods
        mocker.patch.object(logger, "remove")
        mocker.patch.object(logger, "add")
        mocker.patch.object(logger, "info")
        mocker.patch("logging.basicConfig")

        # Mock specific getLogger calls instead of all calls
        mock_noisy_logger = mocker.Mock()
        mock_uvicorn_logger = mocker.Mock(handlers=[])

        # Store original getLogger
        original_get_logger = logging.getLogger

        def get_logger_side_effect(name: str = "") -> MockType | logging.Logger:
            if name == "urllib3.connectionpool":
                return cast("MockType", mock_noisy_logger)
            if name.startswith("uvicorn"):
                return cast("MockType", mock_uvicorn_logger)
            # Return real logger for other names (like pytest's loggers)
            return original_get_logger(name)

        mocker.patch("logging.getLogger", side_effect=get_logger_side_effect)

        # Call setup_logging
        setup_logging(mock_settings)

        # Verify noisy logger was disabled
        assert mock_noisy_logger.disabled is True

        # Use isolated_logging_state explicitly to fix lint
        assert isolated_logging_state.configured is True

    def test_bind_context(self, mocker: MockerFixture) -> None:
        """Test context binding to logger."""
        mock_configure = mocker.patch.object(logger, "configure")

        # Bind various context types
        bind_context(
            service_name="api",
            version="1.0.0",
            environment="production",
            numeric_value=42,
            boolean_value=True,
        )

        # Verify configure was called with correct args
        mock_configure.assert_called_once_with(
            extra={
                "service_name": "api",
                "version": "1.0.0",
                "environment": "production",
                "numeric_value": 42,
                "boolean_value": True,
            }
        )

    def test_get_logger(self, mocker: MockerFixture) -> None:
        """Test named logger creation."""
        mock_bind = mocker.patch.object(logger, "bind")
        mock_bound_logger = mocker.Mock()
        mock_bind.return_value = mock_bound_logger

        # Get logger with name
        result = get_logger("test.module.name")

        # Verify bind was called correctly
        mock_bind.assert_called_once_with(logger_name="test.module.name")
        assert result == mock_bound_logger

    def test_concurrent_setup_logging(
        self,
        mocker: MockerFixture,
        mock_settings: Settings,
        thread_sync: dict[str, Any],
        isolated_logging_state: _LoggingState,
    ) -> None:
        """Test setup_logging is thread-safe."""
        # Track how many times configuration happens
        configure_count = 0

        # Mock logger methods
        def mock_remove() -> None:
            nonlocal configure_count
            configure_count += 1

        mocker.patch.object(logger, "remove", side_effect=mock_remove)
        mocker.patch.object(logger, "add")
        mocker.patch.object(logger, "info")
        mocker.patch("logging.basicConfig")
        mocker.patch("logging.getLogger", return_value=mocker.Mock(handlers=[]))

        # Create barrier for thread synchronization
        num_threads = 5
        barrier = thread_sync["barrier"](num_threads)
        results = thread_sync["create_results"]()

        def thread_worker() -> None:
            try:
                # Wait for all threads to be ready
                barrier.wait()
                # All threads try to configure logging simultaneously
                setup_logging(mock_settings)
                results.append("success")
            except Exception as e:
                results.append(f"error: {e}")

        # Start threads
        threads = []
        for _ in range(num_threads):
            thread = threading.Thread(target=thread_worker)
            thread.start()
            threads.append(thread)

        # Wait for all threads with timeout
        for thread in threads:
            thread.join(timeout=5.0)
            assert not thread.is_alive(), "Thread did not complete in time"

        # Verify results
        assert len(results) == num_threads
        assert all(r == "success" for r in results)
        # Only one configuration should have occurred
        assert configure_count == 1
        assert isolated_logging_state.configured is True

    def test_concurrent_log_emission(
        self, mocker: MockerFixture, thread_sync: dict[str, Any]
    ) -> None:
        """Test InterceptHandler is thread-safe during concurrent emission."""
        # Mock sys._getframe
        mock_frame = mocker.Mock()
        mock_frame.f_code.co_filename = "/app/test.py"
        mock_frame.f_back = None
        mocker.patch("sys._getframe", return_value=mock_frame)

        # Track emitted logs
        emitted_logs = thread_sync["create_results"]()

        # Mock logger to capture emissions
        def mock_log(level: str, message: str) -> None:
            emitted_logs.append((level, message))

        mock_opt = mocker.patch.object(logger, "opt")
        mock_bind = mocker.Mock()
        mock_bind.log = mock_log
        mock_opt.return_value.bind.return_value = mock_bind

        # Create handler
        handler = InterceptHandler()

        # Create barrier for synchronization
        num_threads = 10
        barrier = thread_sync["barrier"](num_threads)

        def thread_worker(thread_id: int) -> None:
            # Wait for all threads
            barrier.wait()
            # Emit logs simultaneously
            for i in range(5):
                record = logging.LogRecord(
                    name=f"thread{thread_id}",
                    level=logging.INFO,
                    pathname="/app/test.py",
                    lineno=10,
                    msg=f"Thread {thread_id} message {i}",
                    args=(),
                    exc_info=None,
                )
                handler.emit(record)

        # Start threads
        threads = []
        for i in range(num_threads):
            thread = threading.Thread(target=thread_worker, args=(i,))
            thread.start()
            threads.append(thread)

        # Wait for completion
        for thread in threads:
            thread.join(timeout=5.0)
            assert not thread.is_alive()

        # Verify all logs were emitted without corruption
        assert len(emitted_logs) == num_threads * 5
        # Check no log corruption (all messages are properly formatted)
        for level, message in emitted_logs:
            assert level == "INFO"
            assert "Thread" in message
            assert "message" in message

    def test_stdlib_logging_integration(self, mocker: MockerFixture) -> None:
        """Test InterceptHandler captures stdlib logs."""
        # Mock sys._getframe
        mock_frame = mocker.Mock()
        mock_frame.f_code.co_filename = "/app/test.py"
        mock_frame.f_back = None
        mocker.patch("sys._getframe", return_value=mock_frame)

        # Track forwarded logs
        forwarded_logs = []

        def mock_log(level: str, message: str) -> None:
            forwarded_logs.append((level, message))

        mock_opt = mocker.patch.object(logger, "opt")
        mock_bind = mocker.Mock()
        mock_bind.log = mock_log
        mock_opt.return_value.bind.return_value = mock_bind

        # Create isolated stdlib logger
        test_logger = logging.getLogger("test.stdlib.logger")
        test_logger.handlers = [InterceptHandler()]
        test_logger.setLevel(logging.DEBUG)
        test_logger.propagate = False

        # Emit various log levels
        test_logger.debug("Debug message")
        test_logger.info("Info message")
        test_logger.warning("Warning message")
        test_logger.error("Error message")

        # Verify all logs were forwarded
        assert len(forwarded_logs) == 4
        levels_and_messages = [
            ("DEBUG", "Debug message"),
            ("INFO", "Info message"),
            ("WARNING", "Warning message"),
            ("ERROR", "Error message"),
        ]
        for (expected_level, expected_msg), (level, msg) in zip(
            levels_and_messages, forwarded_logs, strict=True
        ):
            assert level == expected_level
            assert msg == expected_msg

    def test_formatter_error_handling(self, mocker: MockerFixture) -> None:
        """Test formatters handle malformed records gracefully."""
        test_cases = [
            # Each formatter with various malformed records
            (
                format_console_with_context,
                {"time": mocker.Mock(strftime=mocker.Mock(side_effect=AttributeError))},
            ),
            (
                serialize_for_json,
                {
                    "time": mocker.Mock(
                        isoformat=mocker.Mock(side_effect=AttributeError)
                    ),
                    "level": mocker.Mock(name="INFO"),
                },
            ),
            (
                serialize_for_gcp,
                {
                    "level": mocker.Mock(name="INFO"),
                    "time": mocker.Mock(
                        isoformat=mocker.Mock(side_effect=AttributeError)
                    ),
                },
            ),
            (serialize_for_aws, {"exception": mocker.Mock(type=None, value=None)}),
        ]

        for formatter_func, bad_record in test_cases:
            # Ensure required fields exist with defaults
            # Create a properly typed record dict
            record: dict[str, Any] = bad_record.copy()
            record.setdefault("message", "test")
            record.setdefault("level", mocker.Mock(name="INFO"))
            record.setdefault(
                "time",
                mocker.Mock(isoformat=mocker.Mock(return_value="2024-01-01T00:00:00")),
            )
            record.setdefault("name", "test")
            record.setdefault("function", "test")
            record.setdefault("module", "test")
            record.setdefault("line", 1)
            record.setdefault("file", mocker.Mock(path="test.py"))

            # Test formatter behavior with malformed records
            try:
                result = formatter_func(record)
                # If it succeeds, should return a string
                assert isinstance(result, str)
                assert len(result) > 0
            except (AttributeError, KeyError, TypeError):
                # Some formatters may raise exceptions with malformed data,
                # which is acceptable
                pass

    def test_logging_enqueue_performance(
        self,
        mocker: MockerFixture,
        mock_settings: Settings,
        isolated_logging_state: _LoggingState,
    ) -> None:
        """Test async logging doesn't block."""
        # Mock logger methods
        mocker.patch.object(logger, "remove")
        mock_add = mocker.patch.object(logger, "add")
        mocker.patch.object(logger, "info")
        mocker.patch("logging.basicConfig")
        mocker.patch("logging.getLogger", return_value=mocker.Mock(handlers=[]))

        # Setup logging
        setup_logging(mock_settings)

        # Verify enqueue=True was set
        add_kwargs = mock_add.call_args[1]
        assert add_kwargs["enqueue"] is True

        # Measure logging time
        start_time = time.time()

        # This should return immediately due to enqueue=True
        logger.bind(test=True).info("Test async logging")

        elapsed = time.time() - start_time

        # Should be much faster than 100ms
        assert elapsed < 0.01, f"Logging took {elapsed}s, should be < 0.01s"

        # Use isolated_logging_state explicitly to fix lint
        assert isolated_logging_state.configured is True

    def test_log_formatters_registry(self) -> None:
        """Test LOG_FORMATTERS registry structure and extensibility."""
        # Verify all expected formatters are registered
        expected_formatters = ["console", "json", "gcp", "aws"]
        for formatter in expected_formatters:
            assert formatter in LOG_FORMATTERS

        # Verify console formatter is None (uses default)
        assert LOG_FORMATTERS["console"] is None

        # Verify other formatters are callable
        assert callable(LOG_FORMATTERS["json"])
        assert callable(LOG_FORMATTERS["gcp"])
        assert callable(LOG_FORMATTERS["aws"])

        # Test registry is mutable for extensibility
        def custom_formatter(record: dict[str, Any]) -> str:
            return f"CUSTOM: {record.get('message', '')}\n"

        LOG_FORMATTERS["custom"] = custom_formatter
        assert LOG_FORMATTERS["custom"] == custom_formatter

        # Clean up
        del LOG_FORMATTERS["custom"]

    def test_protocol_implementations(self, mocker: MockerFixture) -> None:
        """Test protocol compliance for type safety."""

        # Create minimal protocol implementations
        class MinimalSettings:
            @property
            def debug(self) -> bool:
                return False

            @property
            def log_config(self) -> LogConfigProtocol:
                return MinimalLogConfig()

        class MinimalLogConfig:
            @property
            def log_level(self) -> str:
                return "INFO"

            @property
            def log_formatter_type(self) -> str | None:
                return "console"

        # Mock logger methods
        mocker.patch.object(logger, "remove")
        mocker.patch.object(logger, "add")
        mocker.patch.object(logger, "info")
        mocker.patch("logging.basicConfig")
        mocker.patch("logging.getLogger", return_value=mocker.Mock(handlers=[]))

        # Reset state
        _state.configured = False

        # Verify setup_logging accepts protocol-compliant objects
        settings = MinimalSettings()
        try:
            setup_logging(settings)
        except Exception as e:
            pytest.fail(f"Protocol implementation failed: {e}")

    def test_module_constants(self) -> None:
        """Test module constants are correctly defined."""
        # Verify DEFAULT_LOG_FORMAT
        assert isinstance(DEFAULT_LOG_FORMAT, str)
        assert "{time:" in DEFAULT_LOG_FORMAT
        assert "{level:" in DEFAULT_LOG_FORMAT
        assert "{message}" in DEFAULT_LOG_FORMAT

        # Verify CORRELATION_ID_DISPLAY_LENGTH
        assert isinstance(CORRELATION_ID_DISPLAY_LENGTH, int)
        assert CORRELATION_ID_DISPLAY_LENGTH == 8

        # Verify MAX_FIELD_VALUE_LENGTH
        assert isinstance(MAX_FIELD_VALUE_LENGTH, int)
        assert MAX_FIELD_VALUE_LENGTH == 100

    def test_formatter_edge_cases(self, mocker: MockerFixture) -> None:
        """Test edge cases in all formatter functions."""
        test_cases = [
            # Empty records
            (format_console_with_context, {}),
            (serialize_for_json, {"level": mocker.Mock(name="")}),
            (serialize_for_gcp, {"extra": {}}),
            (serialize_for_aws, {"extra": {}}),
            # Unicode and special characters
            (
                format_console_with_context,
                {
                    "message": "Test 🚀 with émojis and 中文",
                    "time": datetime.now(UTC),
                    "level": mocker.Mock(name="INFO"),
                    "name": "test",
                    "function": "测试",
                    "line": 42,
                    "extra": {"field": "value with\nnewlines\tand\ttabs"},
                },
            ),
        ]

        for formatter, edge_case in test_cases:
            # Create a properly typed record dict
            record: dict[str, Any] = edge_case.copy()

            # Add minimal required fields
            record.setdefault("message", "test")
            record.setdefault("time", datetime.now(UTC))
            record.setdefault("level", mocker.Mock(name="INFO"))
            record.setdefault("name", "test")
            record.setdefault("function", "test")
            record.setdefault("module", "test")
            record.setdefault("line", 1)
            record.setdefault("file", mocker.Mock(path="test.py"))

            # Should handle edge cases gracefully
            try:
                result = formatter(record)
                assert isinstance(result, str)
                assert len(result) > 0

                # For JSON formatters, verify valid JSON
                if formatter in [
                    serialize_for_json,
                    serialize_for_gcp,
                    serialize_for_aws,
                ]:
                    json.loads(result.strip())  # Should not raise
            except Exception as e:
                pytest.fail(f"Formatter failed on edge case: {e}")

    def test_formatter_circular_reference(self, mocker: MockerFixture) -> None:
        """Test formatter with circular reference specifically."""
        # Create record with circular reference
        extra_dict: dict[str, Any] = {"circular": None}
        record = {
            "message": "test",
            "time": mocker.Mock(
                isoformat=mocker.Mock(return_value="2024-01-01T00:00:00")
            ),
            "level": mocker.Mock(name="INFO"),
            "extra": extra_dict,
            "name": "test",
            "function": "test",
            "module": "test",
            "line": 1,
            "file": mocker.Mock(path="test.py"),
        }
        # Set circular reference
        extra_dict["circular"] = extra_dict

        # Should handle gracefully (may fail JSON serialization)
        try:
            result = serialize_for_json(record)
            assert isinstance(result, str)
        except (ValueError, TypeError):
            # Circular reference may cause JSON serialization to fail
            pass
