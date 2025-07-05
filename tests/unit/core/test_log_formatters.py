"""Tests for cloud-agnostic log formatters."""

import json
from collections.abc import AsyncGenerator, Generator
from datetime import UTC, datetime
from io import StringIO
from typing import Any, Protocol, cast

import pytest
from loguru import logger
from pytest_mock import MockerFixture

import src.core.logging
from src.core.config import LogConfig, Settings
from src.core.logging import (
    CORRELATION_ID_DISPLAY_LENGTH,
    LOG_FORMATTERS,
    _format_context_fields,
    _format_priority_field,
    detect_environment,
    format_console_with_context,
    serialize_for_aws,
    serialize_for_gcp,
    serialize_for_json,
    setup_logging,
)


class MessageWithRecord(Protocol):
    """Protocol for message objects with record attribute."""

    record: dict[str, Any]


@pytest.fixture
def mock_record(mocker: MockerFixture) -> dict[str, Any]:
    """Create a mock Loguru record."""
    mock_time = mocker.Mock()
    mock_time.isoformat.return_value = "2024-01-01T12:00:00+00:00"
    mock_time.strftime.return_value = "2024-01-01 12:00:00.000"

    mock_level = mocker.Mock()
    mock_level.name = "INFO"

    mock_file = mocker.Mock()
    mock_file.path = "test.py"

    return {
        "time": mock_time,
        "level": mock_level,
        "message": "Test message",
        "name": None,
        "function": "test_function",
        "module": "test_module",
        "line": 42,
        "file": mock_file,
        "extra": {
            "correlation_id": "test-correlation-123",
            "request_id": "test-request-456",
            "user_id": 789,
            "_internal": "should be filtered",
        },
    }


@pytest.fixture(autouse=True)
async def cleanup_logger() -> AsyncGenerator[None]:
    """Clean up logger handlers and database connections after each test."""
    yield
    logger.remove()


@pytest.fixture
def reset_logging_state() -> Generator[None]:
    """Reset logging state for tests that need to call setup_logging."""
    # Store original state
    original_state = src.core.logging._state.configured

    # Reset state to allow setup_logging to run
    src.core.logging._state.configured = False

    yield

    # Restore original state
    src.core.logging._state.configured = original_state


@pytest.mark.unit
class TestFormatters:
    """Test individual formatter functions."""

    def test_json_formatter(self, mock_record: dict[str, Any]) -> None:
        """Test generic JSON formatter."""
        output = serialize_for_json(mock_record)
        data = json.loads(output.strip())

        assert data["level"] == "INFO"
        assert data["message"] == "Test message"
        assert data["function"] == "test_function"
        assert data["correlation_id"] == "test-correlation-123"
        assert data["request_id"] == "test-request-456"
        assert data["user_id"] == 789
        assert "_internal" not in data

    def test_gcp_formatter(
        self, mock_record: dict[str, Any], mocker: MockerFixture
    ) -> None:
        """Test GCP Cloud Logging formatter."""
        # Mock get_settings for GCP formatter
        mock_settings = mocker.patch("src.core.logging.get_settings")
        mock_settings.return_value.app_name = "test-app"
        mock_settings.return_value.app_version = "1.0.0"

        output = serialize_for_gcp(mock_record)
        data = json.loads(output.strip())

        assert data["severity"] == "INFO"
        assert data["message"] == "Test message"
        assert data["logging.googleapis.com/trace"] == "test-correlation-123"
        assert data["logging.googleapis.com/labels"]["request_id"] == "test-request-456"
        assert data["jsonPayload"]["user_id"] == 789
        assert "timestamp" in data

    def test_aws_formatter(self, mock_record: dict[str, Any]) -> None:
        """Test AWS CloudWatch formatter."""
        output = serialize_for_aws(mock_record)
        data = json.loads(output.strip())

        assert data["level"] == "INFO"
        assert data["message"] == "Test message"
        assert data["traceId"] == "test-correlation-123"
        assert data["requestId"] == "test-request-456"
        assert data["user_id"] == 789
        assert "timestamp" in data

    def test_exception_formatting_json(
        self, mock_record: dict[str, Any], mocker: MockerFixture
    ) -> None:
        """Test exception formatting in JSON."""
        mock_exception = mocker.Mock()
        mock_exception.type = ValueError
        mock_exception.value = "Test error"
        mock_exception.traceback = "Traceback details..."

        mock_record["exception"] = mock_exception

        output = serialize_for_json(mock_record)
        data = json.loads(output.strip())

        assert data["exception"]["type"] == "ValueError"
        assert data["exception"]["value"] == "Test error"
        assert "traceback" in data["exception"]

    def test_exception_formatting_gcp(
        self,
        mock_record: dict[str, Any],
        mocker: MockerFixture,
    ) -> None:
        """Test exception formatting for GCP."""
        # Mock get_settings for GCP formatter
        mock_settings = mocker.patch("src.core.logging.get_settings")
        mock_settings.return_value.app_name = "test-app"
        mock_settings.return_value.app_version = "1.0.0"

        mock_exception = mocker.Mock()
        mock_exception.type = ValueError
        mock_exception.value = "Test error"
        mock_exception.traceback = "Traceback details..."

        mock_record["exception"] = mock_exception

        output = serialize_for_gcp(mock_record)
        data = json.loads(output.strip())

        assert "logging.googleapis.com/sourceLocation" in data
        assert data["logging.googleapis.com/sourceLocation"]["file"] == "test.py"
        assert data["logging.googleapis.com/sourceLocation"]["line"] == "42"

    def test_exception_formatting_aws(
        self, mock_record: dict[str, Any], mocker: MockerFixture
    ) -> None:
        """Test exception formatting for AWS."""
        mock_exception = mocker.Mock()
        mock_exception.type = ValueError
        mock_exception.value = "Test error"
        mock_exception.traceback = "Traceback details..."

        mock_record["exception"] = mock_exception

        output = serialize_for_aws(mock_record)
        data = json.loads(output.strip())

        assert data["error"]["type"] == "ValueError"
        assert data["error"]["message"] == "Test error"
        assert data["error"]["stackTrace"] == "Traceback details..."

    def test_empty_extra_fields(
        self, mock_record: dict[str, Any], mocker: MockerFixture
    ) -> None:
        """Test formatters with no extra fields."""
        # Mock get_settings for GCP formatter test
        mock_settings = mocker.patch("src.core.logging.get_settings")
        mock_settings.return_value.app_name = "test-app"
        mock_settings.return_value.app_version = "1.0.0"

        mock_record["extra"] = {}

        # JSON formatter
        output = serialize_for_json(mock_record)
        data = json.loads(output.strip())
        assert "correlation_id" not in data
        assert "user_id" not in data

        # GCP formatter
        output = serialize_for_gcp(mock_record)
        data = json.loads(output.strip())
        assert "logging.googleapis.com/trace" not in data
        assert "jsonPayload" not in data

        # AWS formatter
        output = serialize_for_aws(mock_record)
        data = json.loads(output.strip())
        assert "traceId" not in data
        assert "requestId" not in data

    def test_level_mapping_gcp(
        self, mock_record: dict[str, Any], mocker: MockerFixture
    ) -> None:
        """Test Loguru to GCP severity level mapping."""
        # Mock get_settings for GCP formatter
        mock_settings = mocker.patch("src.core.logging.get_settings")
        mock_settings.return_value.app_name = "test-app"
        mock_settings.return_value.app_version = "1.0.0"

        levels = {
            "TRACE": "DEBUG",
            "DEBUG": "DEBUG",
            "INFO": "INFO",
            "SUCCESS": "INFO",
            "WARNING": "WARNING",
            "ERROR": "ERROR",
            "CRITICAL": "CRITICAL",
        }

        for loguru_level, gcp_severity in levels.items():
            mock_record["level"].name = loguru_level
            output = serialize_for_gcp(mock_record)
            data = json.loads(output.strip())
            assert data["severity"] == gcp_severity


@pytest.mark.unit
class TestEnvironmentDetection:
    """Test automatic environment detection."""

    def test_detect_gcp(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test GCP environment detection."""
        monkeypatch.setenv("K_SERVICE", "test-service")
        assert detect_environment() == "gcp"

    def test_detect_aws(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test AWS environment detection."""
        monkeypatch.setenv("AWS_EXECUTION_ENV", "AWS_ECS_FARGATE")
        assert detect_environment() == "aws"

    def test_detect_azure(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test Azure environment detection."""
        monkeypatch.setenv("WEBSITE_INSTANCE_ID", "test-instance")
        assert detect_environment() == "json"  # Azure uses generic JSON

    def test_detect_local(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test local environment detection."""
        # Ensure no cloud env vars
        monkeypatch.delenv("K_SERVICE", raising=False)
        monkeypatch.delenv("AWS_EXECUTION_ENV", raising=False)
        monkeypatch.delenv("WEBSITE_INSTANCE_ID", raising=False)
        assert detect_environment() == "console"


@pytest.mark.unit
class TestFormatterIntegration:
    """Test formatter integration with Loguru."""

    def test_console_formatter(
        self, mocker: MockerFixture, reset_logging_state: None
    ) -> None:
        """Test console formatter setup."""
        # Use the fixture to ensure logging state is reset
        _ = reset_logging_state

        settings = Settings(log_config=LogConfig(log_formatter_type="console"))

        # Mock logger.add to verify it's called with correct parameters
        mock_add = mocker.patch("src.core.logging.logger.add")

        logger.remove()
        setup_logging(settings)

        # Verify logger.add was called with console formatter
        mock_add.assert_called_once()
        call_args = mock_add.call_args
        assert call_args.kwargs["format"] == format_console_with_context

    def test_json_formatter_integration(self) -> None:
        """Test JSON formatter integration."""
        # Remove all handlers and add one for capturing output
        logger.remove()
        output = StringIO()

        # Create a custom sink that uses the formatter
        def json_sink(message: object) -> None:
            msg = cast("MessageWithRecord", message)
            formatted = serialize_for_json(msg.record)
            output.write(formatted)

        logger.add(json_sink, level="INFO")

        # Log with context
        with logger.contextualize(correlation_id="test-123"):
            logger.info("Test message", user_id=456)

        # Parse output
        log_lines = output.getvalue().strip().split("\n")
        assert len(log_lines) >= 1

        # Parse the JSON log
        data = json.loads(log_lines[0])
        assert data["message"] == "Test message"
        assert data["correlation_id"] == "test-123"
        assert data["user_id"] == 456

    def test_formatter_auto_detection(
        self,
        monkeypatch: pytest.MonkeyPatch,
        mocker: MockerFixture,
        reset_logging_state: None,
    ) -> None:
        """Test formatter auto-detection."""
        # Use the fixture to ensure logging state is reset
        _ = reset_logging_state

        # Simulate GCP environment
        monkeypatch.setenv("K_SERVICE", "test-service")

        settings = Settings(
            log_config=LogConfig()  # No formatter specified
        )

        logger.remove()

        # Mock the logger.info call to prevent output during test
        mock_logger_info = mocker.patch("src.core.logging.logger.info")

        setup_logging(settings)

        # Verify the logger.info was called with the expected message
        mock_logger_info.assert_called_once()
        call_args = mock_logger_info.call_args
        assert "Logging configured with {} formatter" in call_args[0][0]
        assert call_args[0][1] == "gcp"

    def test_gcp_formatter_integration(self, mocker: MockerFixture) -> None:
        """Test GCP formatter integration."""
        # Mock get_settings for GCP formatter
        mock_settings = mocker.patch("src.core.logging.get_settings")
        mock_settings.return_value.app_name = "test-app"
        mock_settings.return_value.app_version = "1.0.0"

        # Remove all handlers and add one for capturing output
        logger.remove()
        output = StringIO()

        # Create a custom sink that uses the formatter
        def gcp_sink(message: object) -> None:
            msg = cast("MessageWithRecord", message)
            formatted = serialize_for_gcp(msg.record)
            output.write(formatted)

        logger.add(gcp_sink, level="INFO")

        # Log a message
        logger.info("GCP test message")

        # Parse output
        log_lines = output.getvalue().strip().split("\n")
        assert len(log_lines) >= 1

        # Parse the JSON log
        data = json.loads(log_lines[0])
        assert data["severity"] == "INFO"
        assert data["message"] == "GCP test message"

    def test_aws_formatter_integration(self) -> None:
        """Test AWS formatter integration."""
        # Remove all handlers and add one for capturing output
        logger.remove()
        output = StringIO()

        # Create a custom sink that uses the formatter
        def aws_sink(message: object) -> None:
            msg = cast("MessageWithRecord", message)
            formatted = serialize_for_aws(msg.record)
            output.write(formatted)

        logger.add(aws_sink, level="INFO")

        # Log a message
        logger.info("AWS test message")

        # Parse output
        log_lines = output.getvalue().strip().split("\n")
        assert len(log_lines) >= 1

        # Parse the JSON log
        data = json.loads(log_lines[0])
        assert data["level"] == "INFO"
        assert data["message"] == "AWS test message"


@pytest.mark.unit
class TestCloudAgnostic:
    """Test cloud-agnostic functionality."""

    def test_local_development_no_cloud(
        self, mocker: MockerFixture, reset_logging_state: None
    ) -> None:
        """Test that local development works without cloud services."""
        # Use the fixture to ensure logging state is reset
        _ = reset_logging_state

        settings = Settings(
            environment="development",
            log_config=LogConfig(log_formatter_type="console"),
        )

        # Mock logger.add to verify it works without cloud auth
        mock_add = mocker.patch("src.core.logging.logger.add")

        logger.remove()
        setup_logging(settings)

        # Should work without errors
        assert mock_add.called

    def test_easy_cloud_switching(self, mocker: MockerFixture) -> None:
        """Test switching between cloud providers is configuration-only."""
        # Mock get_settings for GCP formatter
        mock_settings = mocker.patch("src.core.logging.get_settings")
        mock_settings.return_value.app_name = "test-app"
        mock_settings.return_value.app_version = "1.0.0"

        # Start with GCP
        output_gcp = StringIO()
        logger.remove()

        def gcp_sink(message: object) -> None:
            msg = cast("MessageWithRecord", message)
            formatted = serialize_for_gcp(msg.record)
            output_gcp.write(formatted)

        logger.add(gcp_sink, level="INFO")
        logger.info("GCP message")

        gcp_data = json.loads(output_gcp.getvalue().strip())
        assert "severity" in gcp_data  # GCP-specific field

        # Switch to AWS
        output_aws = StringIO()
        logger.remove()

        def aws_sink(message: object) -> None:
            msg = cast("MessageWithRecord", message)
            formatted = serialize_for_aws(msg.record)
            output_aws.write(formatted)

        logger.add(aws_sink, level="INFO")
        logger.info("AWS message")

        aws_data = json.loads(output_aws.getvalue().strip())
        assert "level" in aws_data  # AWS uses different field name

        # No code changes required, only configuration!

    def test_formatter_registry(self) -> None:
        """Test that formatter registry is properly configured."""
        assert "console" in LOG_FORMATTERS
        assert "json" in LOG_FORMATTERS
        assert "gcp" in LOG_FORMATTERS
        assert "aws" in LOG_FORMATTERS

        assert LOG_FORMATTERS["console"] is None  # Console uses default
        assert callable(LOG_FORMATTERS["json"])
        assert callable(LOG_FORMATTERS["gcp"])
        assert callable(LOG_FORMATTERS["aws"])

    def test_invalid_formatter_detection(self) -> None:
        """Test that invalid formatter type is caught by Pydantic validation."""
        with pytest.raises(ValueError, match="Input should be"):
            # Test passing an invalid value via dict to bypass type checking
            LogConfig.model_validate({"log_formatter_type": "invalid"})

    def test_formatter_with_real_datetime(self, mocker: MockerFixture) -> None:
        """Test formatters with real datetime objects."""
        # Mock get_settings for GCP formatter
        mock_settings = mocker.patch("src.core.logging.get_settings")
        mock_settings.return_value.app_name = "test-app"
        mock_settings.return_value.app_version = "1.0.0"

        # Create a more realistic mock record with actual datetime
        # Use a fixed datetime for determinism
        fixed_datetime = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)

        mock_level = mocker.Mock()
        mock_level.name = "INFO"

        mock_file = mocker.Mock()
        mock_file.path = "test.py"

        mock_record = {
            "time": fixed_datetime,
            "level": mock_level,
            "message": "Test with real datetime",
            "name": None,
            "function": "test_function",
            "module": "test_module",
            "line": 42,
            "file": mock_file,
            "extra": {},
        }

        # Test all formatters handle real datetime
        output_json = serialize_for_json(mock_record)
        data_json = json.loads(output_json.strip())
        assert "timestamp" in data_json

        output_gcp = serialize_for_gcp(mock_record)
        data_gcp = json.loads(output_gcp.strip())
        assert "timestamp" in data_gcp

        output_aws = serialize_for_aws(mock_record)
        data_aws = json.loads(output_aws.strip())
        assert "timestamp" in data_aws

    def test_structured_sink_edge_case(self) -> None:
        """Test structured_sink edge case where message has no record attribute."""

        # Create a message object without record attribute
        class MessageNoRecord:
            pass

        # Get the JSON formatter
        formatter = LOG_FORMATTERS["json"]
        assert formatter is not None

        # Create the structured sink function directly
        output = StringIO()

        def structured_sink(message: object) -> None:
            """Custom sink that formats and writes structured logs."""
            if formatter and hasattr(message, "record"):
                formatted = formatter(message.record)
                output.write(formatted)
                output.flush()

        # Call with message that has no record - should not write anything
        structured_sink(MessageNoRecord())
        assert output.getvalue() == ""

        # Test with a proper message that has a record attribute
        class TestMessage:
            def __init__(self) -> None:
                self.record = {
                    "time": type(
                        "MockTime",
                        (),
                        {"isoformat": lambda: "2024-01-01T12:00:00+00:00"},
                    ),
                    "level": type("MockLevel", (), {"name": "INFO"}),
                    "message": "Test message",
                    "name": None,
                    "function": "test_function",
                    "module": "test_module",
                    "line": 42,
                    "file": type("MockFile", (), {"path": "test.py"}),
                    "extra": {},
                }

        msg = TestMessage()
        structured_sink(msg)

        # Verify output
        output_value = output.getvalue()
        assert output_value
        parsed = json.loads(output_value.strip())
        assert parsed["message"] == "Test message"


@pytest.mark.unit
class TestConsoleFormatterEdgeCases:
    """Test console formatter edge cases to achieve 100% coverage."""

    def test_console_formatter_long_correlation_id(self) -> None:
        """Test console formatter truncates long correlation IDs."""
        # Create a correlation ID longer than display length (8 chars)
        long_correlation_id = "this-is-a-very-long-correlation-id-12345"

        # Format the field
        result = _format_priority_field("correlation_id", long_correlation_id)

        # Should be truncated to CORRELATION_ID_DISPLAY_LENGTH
        assert result == long_correlation_id[:CORRELATION_ID_DISPLAY_LENGTH]
        assert result is not None
        assert len(result) == CORRELATION_ID_DISPLAY_LENGTH

    def test_console_formatter_duration_ms(self) -> None:
        """Test console formatter adds 'ms' suffix to duration_ms field."""
        # Test with numeric duration
        result = _format_priority_field("duration_ms", 123.45)
        assert result == "123.45ms"

        # Test with string duration
        result = _format_priority_field("duration_ms", "456")
        assert result == "456ms"

    def test_console_formatter_status_code_4xx(self) -> None:
        """Test console formatter colors 4xx status codes red."""
        # Test various 4xx codes
        for code in [400, 401, 403, 404, 422, 429]:
            result = _format_priority_field("status_code", code)
            assert result == f"<red>{code}</red>"

        # Also test string versions
        result = _format_priority_field("status_code", "404")
        assert result == "<red>404</red>"

    def test_console_formatter_with_all_priority_fields(self) -> None:
        """Test console formatter with all priority fields."""
        # Create extra data with all priority fields
        extra = {
            "correlation_id": "test-correlation-id-longer-than-8-chars",
            "request_id": "req-123",
            "user_id": 456,
            "method": "GET",
            "path": "/api/test",
            "status_code": 404,
            "duration_ms": 150.5,
            "custom_field": "custom_value",
        }

        # Format context fields
        context_parts = _format_context_fields(extra)

        # Should have formatted all fields
        assert len(context_parts) > 0

        # Check specific formatting
        assert any("test-cor" in part for part in context_parts)  # Truncated to 8 chars
        assert any("<yellow>req-123</yellow>" in part for part in context_parts)
        assert any("456" in part for part in context_parts)  # user_id as dim
        assert any("<yellow>GET</yellow>" in part for part in context_parts)
        assert any("<yellow>/api/test</yellow>" in part for part in context_parts)
        assert any("<yellow><red>404</red></yellow>" in part for part in context_parts)
        assert any("<yellow>150.5ms</yellow>" in part for part in context_parts)
        assert any("custom_field=custom_value" in part for part in context_parts)

    def test_console_formatter_with_exception(self, mocker: MockerFixture) -> None:
        """Test console formatter includes exception formatting."""
        # Create a mock record with exception
        mock_level = mocker.Mock()
        mock_level.name = "ERROR"

        mock_file = mocker.Mock()
        mock_file.path = "test.py"

        mock_time = mocker.Mock()
        mock_time.strftime.return_value = "2024-01-01 12:00:00.000"

        mock_exception = mocker.Mock()
        mock_exception.type = ValueError
        mock_exception.value = ValueError("Test error")
        mock_exception.traceback = "Traceback details here"

        mock_record = {
            "time": mock_time,
            "level": mock_level,
            "message": "Error occurred",
            "name": "test",
            "function": "test_func",
            "module": "test_module",
            "line": 42,
            "file": mock_file,
            "extra": {},
            "exception": mock_exception,
        }

        # Format the record
        result = format_console_with_context(mock_record)

        # Should include exception placeholder
        assert "{exception}" in result
        assert "Error occurred" in result
