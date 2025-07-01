"""Tests for cloud-agnostic log formatters."""

import json
from collections.abc import Generator
from datetime import UTC, datetime
from io import StringIO
from typing import Any, Protocol, cast

import pytest
from loguru import logger
from pytest_mock import MockerFixture

from src.core.config import LogConfig, Settings
from src.core.logging import (
    LOG_FORMATTERS,
    _state,
    detect_environment,
    serialize_for_aws,
    serialize_for_gcp,
    serialize_for_json,
    setup_logging,
)


class MessageWithRecord(Protocol):
    """Protocol for message objects with record attribute."""

    record: dict[str, Any]


@pytest.mark.unit
class TestFormatters:
    """Test individual formatter functions."""

    @pytest.fixture
    def mock_record(self) -> dict[str, Any]:
        """Create a mock Loguru record."""

        # Create mock types for nested attributes
        class MockLevel:
            name = "INFO"

        class MockFile:
            path = "test.py"

        class MockTime:
            def isoformat(self) -> str:
                return "2024-01-01T12:00:00+00:00"

        return {
            "time": MockTime(),
            "level": MockLevel(),
            "message": "Test message",
            "name": None,
            "function": "test_function",
            "module": "test_module",
            "line": 42,
            "file": MockFile(),
            "extra": {
                "correlation_id": "test-correlation-123",
                "request_id": "test-request-456",
                "user_id": 789,
                "_internal": "should be filtered",
            },
        }

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

    def test_gcp_formatter(self, mock_record: dict[str, Any]) -> None:
        """Test GCP Cloud Logging formatter."""
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

    def test_exception_formatting_json(self, mock_record: dict[str, Any]) -> None:
        """Test exception formatting in JSON."""

        class MockException:
            type = ValueError
            value = "Test error"
            traceback = "Traceback details..."

        mock_record["exception"] = MockException()

        output = serialize_for_json(mock_record)
        data = json.loads(output.strip())

        assert data["exception"]["type"] == "ValueError"
        assert data["exception"]["value"] == "Test error"
        assert "traceback" in data["exception"]

    def test_exception_formatting_gcp(self, mock_record: dict[str, Any]) -> None:
        """Test exception formatting for GCP."""

        class MockException:
            type = ValueError
            value = "Test error"
            traceback = "Traceback details..."

        mock_record["exception"] = MockException()

        output = serialize_for_gcp(mock_record)
        data = json.loads(output.strip())

        assert "logging.googleapis.com/sourceLocation" in data
        assert data["logging.googleapis.com/sourceLocation"]["file"] == "test.py"
        assert data["logging.googleapis.com/sourceLocation"]["line"] == "42"

    def test_exception_formatting_aws(self, mock_record: dict[str, Any]) -> None:
        """Test exception formatting for AWS."""

        class MockException:
            type = ValueError
            value = "Test error"
            traceback = "Traceback details..."

        mock_record["exception"] = MockException()

        output = serialize_for_aws(mock_record)
        data = json.loads(output.strip())

        assert data["error"]["type"] == "ValueError"
        assert data["error"]["message"] == "Test error"
        assert data["error"]["stackTrace"] == "Traceback details..."

    def test_empty_extra_fields(self, mock_record: dict[str, Any]) -> None:
        """Test formatters with no extra fields."""
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

    def test_level_mapping_gcp(self, mock_record: dict[str, Any]) -> None:
        """Test Loguru to GCP severity level mapping."""
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

    @pytest.fixture(autouse=True)
    def cleanup_logger(self) -> Generator[None]:
        """Clean up logger handlers and reset state."""
        # Reset state before test
        _state.configured = False
        yield
        # Remove all handlers after test
        logger.remove()
        # Reset state after test
        _state.configured = False

    def test_console_formatter(self) -> None:
        """Test console formatter setup."""
        settings = Settings(log_config=LogConfig(log_formatter_type="console"))

        logger.remove()
        setup_logging(settings)

        # Console formatter should work without errors
        # Just verify it doesn't crash
        logger.info("Test console message")

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
        self, monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture
    ) -> None:
        """Test formatter auto-detection."""
        # Simulate GCP environment
        monkeypatch.setenv("K_SERVICE", "test-service")

        settings = Settings(
            log_config=LogConfig()  # No formatter specified
        )

        logger.remove()
        _state.configured = False

        # Mock the logger.info call to prevent output during test
        mock_logger_info = mocker.patch("src.core.logging.logger.info")

        setup_logging(settings)

        # Should auto-detect GCP
        assert _state.configured

        # Verify the logger.info was called with the expected message
        mock_logger_info.assert_called_once()
        call_args = mock_logger_info.call_args
        assert "Logging configured with {} formatter" in call_args[0][0]
        assert call_args[0][1] == "gcp"

    def test_gcp_formatter_integration(self) -> None:
        """Test GCP formatter integration."""
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

    @pytest.fixture(autouse=True)
    def cleanup_logger(self) -> Generator[None]:
        """Clean up logger handlers."""
        yield
        logger.remove()
        _state.configured = False

    def test_local_development_no_cloud(self) -> None:
        """Test that local development works without cloud services."""
        settings = Settings(
            environment="development",
            log_config=LogConfig(log_formatter_type="console"),
        )

        # Should not require any cloud authentication
        logger.remove()
        _state.configured = False
        setup_logging(settings)

        # Should work without errors
        logger.info("Local development message")

    def test_easy_cloud_switching(self) -> None:
        """Test switching between cloud providers is configuration-only."""
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

    def test_formatter_with_real_datetime(self) -> None:
        """Test formatters with real datetime objects."""
        # Create a more realistic mock record with actual datetime
        now = datetime.now(tz=UTC)

        class MockLevel:
            name = "INFO"

        class MockFile:
            path = "test.py"

        mock_record = {
            "time": now,
            "level": MockLevel(),
            "message": "Test with real datetime",
            "name": None,
            "function": "test_function",
            "module": "test_module",
            "line": 42,
            "file": MockFile(),
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

        # Call with proper message
        class MessageWithRecord:
            def __init__(self) -> None:
                class MockLevel:
                    name = "INFO"

                class MockFile:
                    path = "test.py"

                class MockTime:
                    def isoformat(self) -> str:
                        return "2024-01-01T12:00:00+00:00"

                self.record = {
                    "time": MockTime(),
                    "level": MockLevel(),
                    "message": "Test message",
                    "name": None,
                    "function": "test_function",
                    "module": "test_module",
                    "line": 42,
                    "file": MockFile(),
                    "extra": {},
                }

        msg = MessageWithRecord()
        structured_sink(msg)

        # Verify output
        output_value = output.getvalue()
        assert output_value
        parsed = json.loads(output_value.strip())
        assert parsed["message"] == "Test message"
