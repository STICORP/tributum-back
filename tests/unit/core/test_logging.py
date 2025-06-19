"""Unit tests for the logging module."""

import asyncio
import datetime
import json
import logging
import uuid
from collections.abc import Generator
from typing import Any

import pytest
import structlog
from pytest_mock import MockerFixture
from structlog.testing import LogCapture

from src.core.config import LogConfig, Settings
from src.core.context import RequestContext
from src.core.exceptions import (
    BusinessRuleError,
    ErrorCode,
    NotFoundError,
    Severity,
    TributumError,
    UnauthorizedError,
    ValidationError,
)
from src.core.logging import (
    ORJSONRenderer,
    add_log_level_upper,
    bind_logger_context,
    clear_logger_context,
    configure_structlog,
    get_logger,
    inject_correlation_id,
    inject_logger_context,
    log_context,
    log_exception,
)


class TestAddLogLevelUpper:
    """Test the add_log_level_upper processor."""

    def test_adds_uppercase_level(self, mocker: MockerFixture) -> None:
        """Test that log level is added in uppercase."""
        logger = mocker.MagicMock()
        event_dict: dict[str, object] = {}

        result = add_log_level_upper(logger, "info", event_dict)

        assert result["level"] == "INFO"

    def test_converts_warn_to_warning(self, mocker: MockerFixture) -> None:
        """Test that 'warn' is converted to 'WARNING'."""
        logger = mocker.MagicMock()
        event_dict: dict[str, object] = {}

        result = add_log_level_upper(logger, "warn", event_dict)

        assert result["level"] == "WARNING"

    def test_handles_all_log_levels(self, mocker: MockerFixture) -> None:
        """Test all log levels are converted correctly."""
        logger = mocker.MagicMock()
        levels = {
            "debug": "DEBUG",
            "info": "INFO",
            "warning": "WARNING",
            "error": "ERROR",
            "critical": "CRITICAL",
        }

        for method_name, expected_level in levels.items():
            event_dict: dict[str, object] = {}
            result = add_log_level_upper(logger, method_name, event_dict)
            assert result["level"] == expected_level


class TestInjectCorrelationId:
    """Test the inject_correlation_id processor."""

    def test_injects_correlation_id_when_present(self, mocker: MockerFixture) -> None:
        """Test that correlation ID is injected when available."""
        # Set correlation ID in context
        test_correlation_id = "test-correlation-123"
        RequestContext.set_correlation_id(test_correlation_id)

        logger = mocker.MagicMock()
        event_dict: dict[str, object] = {}

        result = inject_correlation_id(logger, "info", event_dict)

        assert result["correlation_id"] == test_correlation_id

        # Clean up
        RequestContext.clear()

    def test_no_correlation_id_when_not_set(self, mocker: MockerFixture) -> None:
        """Test that no correlation ID is added when not in context."""
        # Ensure context is clear
        RequestContext.clear()

        logger = mocker.MagicMock()
        event_dict: dict[str, object] = {}

        result = inject_correlation_id(logger, "info", event_dict)

        assert "correlation_id" not in result

    def test_preserves_existing_fields(self, mocker: MockerFixture) -> None:
        """Test that existing fields are preserved."""
        RequestContext.set_correlation_id("test-id")

        logger = mocker.MagicMock()
        event_dict: dict[str, object] = {"existing": "value", "another": 123}

        result = inject_correlation_id(logger, "info", event_dict)

        assert result["existing"] == "value"
        assert result["another"] == 123
        assert result["correlation_id"] == "test-id"

        # Clean up
        RequestContext.clear()


class TestInjectLoggerContext:
    """Test the inject_logger_context processor."""

    def test_injects_context_when_present(self, mocker: MockerFixture) -> None:
        """Test that logger context is injected when available."""
        # Set context in contextvar
        bind_logger_context(user_id=123, request_id="test-request")

        logger = mocker.MagicMock()
        event_dict: dict[str, object] = {"event": "test"}

        result = inject_logger_context(logger, "info", event_dict)

        assert result["user_id"] == 123
        assert result["request_id"] == "test-request"
        assert result["event"] == "test"

        # Clean up
        clear_logger_context()

    def test_no_context_when_not_set(self, mocker: MockerFixture) -> None:
        """Test that no context is added when not set."""
        # Ensure context is clear
        clear_logger_context()

        logger = mocker.MagicMock()
        event_dict: dict[str, object] = {"event": "test"}

        result = inject_logger_context(logger, "info", event_dict)

        assert result == {"event": "test"}
        assert "user_id" not in result
        assert "request_id" not in result

    def test_event_dict_takes_precedence(self, mocker: MockerFixture) -> None:
        """Test that event_dict values take precedence over context."""
        bind_logger_context(user_id=123, action="context_action")

        logger = mocker.MagicMock()
        event_dict: dict[str, object] = {"event": "test", "user_id": 456}

        result = inject_logger_context(logger, "info", event_dict)

        assert result["user_id"] == 456  # Event dict value wins
        assert result["action"] == "context_action"  # Context value added
        assert result["event"] == "test"

        # Clean up
        clear_logger_context()


class TestConfigureStructlog:
    """Test structlog configuration."""

    @pytest.fixture(autouse=True)
    def reset_structlog(self) -> Generator[None]:
        """Reset structlog configuration after each test."""
        # Store original configuration
        original_config = structlog.get_config()
        yield
        # Restore original configuration
        structlog.configure(**original_config)

    def test_json_output_structure(self, mocker: MockerFixture) -> None:
        """Test JSON output structure in production mode."""
        # Configure for JSON output
        settings = Settings()
        settings.log_config = LogConfig(
            log_level="INFO",
            log_format="json",
            render_json_logs=True,
            add_timestamp=True,
            timestamper_format="iso",
        )
        mocker.patch("src.core.logging.get_settings", return_value=settings)

        # Configure structlog
        configure_structlog()

        # Use LogCapture to test JSON processor pipeline
        cap = LogCapture()
        # Get current config and verify it has JSON renderer
        config = structlog.get_config()
        processors = config["processors"]

        # Verify ORJSONRenderer is in the pipeline
        has_orjson_renderer = any(
            type(p).__name__ == "ORJSONRenderer" for p in processors
        )
        assert has_orjson_renderer, "ORJSONRenderer should be configured"

        # Now test with LogCapture to verify structure
        structlog.configure(
            processors=[
                structlog.stdlib.add_logger_name,
                add_log_level_upper,
                structlog.processors.CallsiteParameterAdder(
                    parameters=[
                        structlog.processors.CallsiteParameter.FILENAME,
                        structlog.processors.CallsiteParameter.LINENO,
                        structlog.processors.CallsiteParameter.FUNC_NAME,
                    ]
                ),
                structlog.processors.TimeStamper(fmt="iso"),
                cap,
            ]
        )

        # Create logger and log a message
        logger = structlog.get_logger("test_logger")
        logger.info("test message", extra_field="extra_value")

        # Verify structure
        assert len(cap.entries) == 1
        entry = cap.entries[0]
        assert entry["event"] == "test message"
        assert entry["level"] == "INFO"
        assert entry["logger"] == "test_logger"
        assert entry["extra_field"] == "extra_value"
        assert "timestamp" in entry
        assert "filename" in entry
        assert "lineno" in entry
        assert "func_name" in entry

    def test_console_output_format(self, mocker: MockerFixture) -> None:
        """Test console output format in development mode."""
        # Configure for console output
        settings = Settings()
        settings.log_config = LogConfig(
            log_level="DEBUG",
            log_format="console",
            render_json_logs=False,
            add_timestamp=True,
            timestamper_format="iso",
        )
        mocker.patch("src.core.logging.get_settings", return_value=settings)

        # Configure structlog
        configure_structlog()

        # Create logger with LogCapture for testing
        cap = LogCapture()
        structlog.configure(
            processors=[
                structlog.stdlib.add_logger_name,
                add_log_level_upper,
                structlog.processors.CallsiteParameterAdder(
                    parameters=[
                        structlog.processors.CallsiteParameter.FILENAME,
                        structlog.processors.CallsiteParameter.LINENO,
                        structlog.processors.CallsiteParameter.FUNC_NAME,
                    ]
                ),
                structlog.processors.TimeStamper(fmt="iso"),
                cap,
            ]
        )

        # Log a message
        logger = structlog.get_logger("test_logger")
        logger.debug("debug message", debug_field="debug_value")

        # Verify captured log
        assert len(cap.entries) == 1
        entry = cap.entries[0]
        assert entry["event"] == "debug message"
        assert entry["level"] == "DEBUG"
        assert entry["logger"] == "test_logger"
        assert entry["debug_field"] == "debug_value"
        assert "timestamp" in entry

    def test_processor_pipeline(self, mocker: MockerFixture) -> None:
        """Test that all processors are included in the pipeline."""
        # Configure settings
        settings = Settings()
        settings.log_config = LogConfig(
            log_level="INFO",
            log_format="json",
            render_json_logs=True,
            add_timestamp=True,
            timestamper_format="iso",
        )
        mocker.patch("src.core.logging.get_settings", return_value=settings)

        # Configure structlog
        configure_structlog()

        # Get current configuration
        config = structlog.get_config()
        processors = config["processors"]

        # Verify processors are present
        processor_types = []
        for p in processors:
            if hasattr(p, "__name__"):
                processor_types.append(p.__name__)
            else:
                processor_types.append(type(p).__name__)

        # Check for expected processors (some are functions, some are classes)
        assert any("add_logger_name" in str(p) for p in processors)
        assert "CallsiteParameterAdder" in processor_types
        assert "TimeStamper" in processor_types
        # Should have ORJSONRenderer
        assert "ORJSONRenderer" in processor_types

    def test_timestamp_configuration(self, mocker: MockerFixture) -> None:
        """Test timestamp configuration options."""
        # Test with timestamp disabled
        settings = Settings()
        settings.log_config = LogConfig(
            log_level="INFO",
            log_format="console",
            render_json_logs=False,
            add_timestamp=False,
        )
        mocker.patch("src.core.logging.get_settings", return_value=settings)

        configure_structlog()

        # Create logger with LogCapture
        cap = LogCapture()
        structlog.configure(
            processors=[
                structlog.stdlib.add_logger_name,
                add_log_level_upper,
                cap,
            ]
        )

        logger = structlog.get_logger()
        logger.info("no timestamp")

        assert "timestamp" not in cap.entries[0]

    def test_unix_timestamp_format(self, mocker: MockerFixture) -> None:
        """Test unix timestamp format."""
        settings = Settings()
        settings.log_config = LogConfig(
            log_level="INFO",
            log_format="json",
            render_json_logs=True,
            add_timestamp=True,
            timestamper_format="unix",
        )
        mocker.patch("src.core.logging.get_settings", return_value=settings)

        configure_structlog()

        # Create logger with LogCapture
        cap = LogCapture()
        structlog.configure(
            processors=[
                structlog.stdlib.add_logger_name,
                structlog.processors.TimeStamper(fmt=None),
                cap,
            ]
        )

        logger = structlog.get_logger()
        logger.info("unix timestamp")

        # Unix timestamp should be a float
        assert isinstance(cap.entries[0]["timestamp"], float)

    def test_log_level_configuration(self, mocker: MockerFixture) -> None:
        """Test that log level is properly configured."""
        settings = Settings()
        settings.log_config = LogConfig(
            log_level="WARNING", log_format="console", render_json_logs=False
        )
        mocker.patch("src.core.logging.get_settings", return_value=settings)

        configure_structlog()

        # Verify root logger level
        assert logging.root.level == logging.WARNING

    def test_development_vs_production_processors(self, mocker: MockerFixture) -> None:
        """Test different processor pipelines for dev vs prod."""
        # Test development configuration
        settings = Settings()
        settings.log_config = LogConfig(
            log_level="DEBUG", log_format="console", render_json_logs=False
        )
        mocker.patch("src.core.logging.get_settings", return_value=settings)

        configure_structlog()
        config_dev = structlog.get_config()

        # Test production configuration
        settings.log_config = LogConfig(
            log_level="INFO", log_format="json", render_json_logs=True
        )

        configure_structlog()
        config_prod = structlog.get_config()

        # Verify different renderers
        dev_renderers = [
            type(p).__name__
            for p in config_dev["processors"]
            if "Renderer" in type(p).__name__
        ]
        prod_renderers = [
            type(p).__name__
            for p in config_prod["processors"]
            if "Renderer" in type(p).__name__
        ]

        assert "ConsoleRenderer" in dev_renderers
        # Should have ORJSONRenderer in production
        assert "ORJSONRenderer" in prod_renderers

    def test_callsite_information(self, mocker: MockerFixture) -> None:
        """Test that callsite information is included."""
        settings = Settings()
        settings.log_config = LogConfig(
            log_level="INFO", log_format="json", render_json_logs=True
        )
        mocker.patch("src.core.logging.get_settings", return_value=settings)

        configure_structlog()

        # Create logger with LogCapture
        cap = LogCapture()
        structlog.configure(
            processors=[
                structlog.stdlib.add_logger_name,
                structlog.processors.CallsiteParameterAdder(
                    parameters=[
                        structlog.processors.CallsiteParameter.FILENAME,
                        structlog.processors.CallsiteParameter.LINENO,
                        structlog.processors.CallsiteParameter.FUNC_NAME,
                    ]
                ),
                cap,
            ]
        )

        logger = structlog.get_logger()
        logger.info("callsite test")

        entry = cap.entries[0]
        assert "filename" in entry
        assert "lineno" in entry
        assert "func_name" in entry
        assert entry["func_name"] == "test_callsite_information"

    def test_correlation_id_included_in_logs(self, mocker: MockerFixture) -> None:
        """Test that correlation ID is automatically included in logs when set."""
        # Set up configuration
        settings = Settings()
        settings.log_config = LogConfig(
            log_level="INFO", log_format="json", render_json_logs=True
        )
        mocker.patch("src.core.logging.get_settings", return_value=settings)

        # Configure structlog with correlation ID processor
        configure_structlog()

        # Set correlation ID in context
        test_correlation_id = "test-corr-456"
        RequestContext.set_correlation_id(test_correlation_id)

        # Create logger with LogCapture
        cap = LogCapture()
        structlog.configure(
            processors=[
                structlog.stdlib.add_logger_name,
                add_log_level_upper,
                inject_correlation_id,
                cap,
            ]
        )

        # Log a message
        logger = structlog.get_logger("test")
        logger.info("test with correlation", user_id=123)

        # Verify correlation ID is included
        assert len(cap.entries) == 1
        entry = cap.entries[0]
        assert entry["correlation_id"] == test_correlation_id
        assert entry["user_id"] == 123
        assert entry["event"] == "test with correlation"

        # Clean up
        RequestContext.clear()

    def test_logs_without_correlation_id(self, mocker: MockerFixture) -> None:
        """Test that logs work fine without correlation ID."""
        # Ensure context is clear
        RequestContext.clear()

        settings = Settings()
        settings.log_config = LogConfig(
            log_level="INFO", log_format="json", render_json_logs=True
        )
        mocker.patch("src.core.logging.get_settings", return_value=settings)

        configure_structlog()

        # Create logger with LogCapture
        cap = LogCapture()
        structlog.configure(
            processors=[
                structlog.stdlib.add_logger_name,
                add_log_level_upper,
                inject_correlation_id,
                cap,
            ]
        )

        # Log a message without correlation ID
        logger = structlog.get_logger()
        logger.info("no correlation id")

        # Verify no correlation ID field
        assert len(cap.entries) == 1
        entry = cap.entries[0]
        assert "correlation_id" not in entry
        assert entry["event"] == "no correlation id"

    def test_correlation_id_isolation(self, mocker: MockerFixture) -> None:
        """Test that correlation IDs are isolated between contexts."""
        settings = Settings()
        settings.log_config = LogConfig(
            log_level="INFO", log_format="json", render_json_logs=True
        )
        mocker.patch("src.core.logging.get_settings", return_value=settings)

        configure_structlog()

        # Create logger with LogCapture
        cap = LogCapture()
        structlog.configure(
            processors=[
                structlog.stdlib.add_logger_name,
                inject_correlation_id,
                cap,
            ]
        )

        logger = structlog.get_logger()

        # First context with correlation ID
        RequestContext.set_correlation_id("context-1")
        logger.info("message 1")

        # Second context with different correlation ID
        RequestContext.set_correlation_id("context-2")
        logger.info("message 2")

        # Clear context
        RequestContext.clear()
        logger.info("message 3")

        # Verify entries
        assert len(cap.entries) == 3
        assert cap.entries[0]["correlation_id"] == "context-1"
        assert cap.entries[1]["correlation_id"] == "context-2"
        assert "correlation_id" not in cap.entries[2]

    def test_orjson_used_in_production(self, mocker: MockerFixture) -> None:
        """Test that ORJSONRenderer is used in production."""
        # Configure for JSON output
        settings = Settings()
        settings.log_config = LogConfig(
            log_level="INFO", log_format="json", render_json_logs=True
        )
        mocker.patch("src.core.logging.get_settings", return_value=settings)

        # Configure structlog
        configure_structlog()

        # Get configuration and check the renderer type
        config = structlog.get_config()
        processors = config["processors"]

        # Find the JSON renderer in processors
        renderer = None
        for p in processors:
            if type(p).__name__ == "ORJSONRenderer":
                renderer = p
                break

        assert renderer is not None
        assert type(renderer).__name__ == "ORJSONRenderer"


class TestGetLogger:
    """Test the get_logger function."""

    @pytest.fixture(autouse=True)
    def setup_structlog(self) -> Generator[None]:
        """Set up structlog for tests."""
        configure_structlog()
        yield
        # Reset structlog
        structlog.reset_defaults()

    def test_get_logger_with_name(self) -> None:
        """Test getting a logger with a specific name."""
        logger = get_logger("test_logger")

        assert logger is not None
        # Verify it's a structlog bound logger
        assert hasattr(logger, "bind")
        assert hasattr(logger, "info")
        assert hasattr(logger, "error")

    def test_get_logger_without_name(self) -> None:
        """Test getting a logger without specifying a name."""
        logger = get_logger()

        assert logger is not None
        # Verify it's a structlog bound logger
        assert hasattr(logger, "bind")

    def test_logger_creates_log_entries(self) -> None:
        """Test that the logger actually creates log entries."""
        cap = LogCapture()
        structlog.configure(processors=[cap])

        logger = get_logger("test")
        logger.info("test message", key="value")

        assert len(cap.entries) == 1
        assert cap.entries[0]["event"] == "test message"
        assert cap.entries[0]["key"] == "value"


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


class TestLogException:
    """Test the log_exception function."""

    @pytest.fixture(autouse=True)
    def setup_structlog(self) -> Generator[None]:
        """Set up structlog for tests."""
        configure_structlog()
        yield
        # Reset structlog
        structlog.reset_defaults()

    def test_log_exception_with_tributum_error(self) -> None:
        """Test logging a TributumError with full context."""
        cap = LogCapture()
        structlog.configure(processors=[cap])

        logger = get_logger("test")
        error = ValidationError(
            "Invalid email format",
            context={"field": "email", "value": "not-an-email"},
        )

        log_exception(logger, error)

        assert len(cap.entries) == 1
        entry = cap.entries[0]
        assert entry["event"] == "[VALIDATION_ERROR] Invalid email format"
        assert entry["error_code"] == "VALIDATION_ERROR"
        assert entry["severity"] == "LOW"
        assert entry["fingerprint"] == error.fingerprint
        assert entry["error_context"] == {"field": "email", "value": "not-an-email"}
        assert entry["exc_info"] is not None

    def test_log_exception_with_custom_message(self) -> None:
        """Test logging with a custom message."""
        cap = LogCapture()
        structlog.configure(processors=[cap])

        logger = get_logger("test")
        error = NotFoundError("User not found")

        log_exception(logger, error, "Failed to fetch user")

        assert len(cap.entries) == 1
        assert cap.entries[0]["event"] == "Failed to fetch user"
        assert cap.entries[0]["error_code"] == "NOT_FOUND"

    def test_log_exception_with_extra_context(self) -> None:
        """Test logging with additional context."""
        cap = LogCapture()
        structlog.configure(processors=[cap])

        logger = get_logger("test")
        error = UnauthorizedError("Invalid token")

        log_exception(logger, error, user_id=123, endpoint="/api/users")

        assert len(cap.entries) == 1
        entry = cap.entries[0]
        assert entry["user_id"] == 123
        assert entry["endpoint"] == "/api/users"
        assert entry["severity"] == "HIGH"

    def test_log_exception_severity_levels(self, mocker: MockerFixture) -> None:
        """Test that different severities use appropriate log levels."""
        # Mock logger to track method calls
        mock_logger = mocker.MagicMock()

        # Test LOW severity - should use warning
        low_error = ValidationError("Low severity")
        log_exception(mock_logger, low_error)
        mock_logger.warning.assert_called_once()
        mock_logger.error.assert_not_called()

        # Reset mock
        mock_logger.reset_mock()

        # Test MEDIUM severity - should use error
        medium_error = BusinessRuleError("Medium severity")
        log_exception(mock_logger, medium_error)
        mock_logger.error.assert_called_once()

        # Reset mock
        mock_logger.reset_mock()

        # Test HIGH severity - should use error
        high_error = UnauthorizedError("High severity")
        log_exception(mock_logger, high_error)
        mock_logger.error.assert_called_once()

        # Reset mock
        mock_logger.reset_mock()

        # Test CRITICAL severity - should use critical
        critical_error = TributumError(
            ErrorCode.INTERNAL_ERROR, "Critical error", severity=Severity.CRITICAL
        )
        log_exception(mock_logger, critical_error)
        mock_logger.critical.assert_called_once()

    def test_log_exception_with_standard_exception(self) -> None:
        """Test logging a standard Python exception."""
        cap = LogCapture()
        structlog.configure(processors=[cap])

        logger = get_logger("test")
        error = ValueError("Invalid value")

        log_exception(logger, error)

        assert len(cap.entries) == 1
        entry = cap.entries[0]
        assert entry["event"] == "Invalid value"
        assert entry["error_type"] == "ValueError"
        assert "error_code" not in entry
        assert "severity" not in entry
        assert entry["exc_info"] is not None

    def test_log_exception_with_cause(self) -> None:
        """Test logging an exception with a cause."""
        cap = LogCapture()
        structlog.configure(processors=[cap])

        logger = get_logger("test")

        try:
            int("not a number")
        except ValueError as e:
            error = ValidationError("Invalid format", cause=e)
            log_exception(logger, error)

        assert len(cap.entries) == 1
        entry = cap.entries[0]
        assert entry["error_code"] == "VALIDATION_ERROR"
        # The cause should be part of the exc_info
        assert entry["exc_info"] is not None

    def test_log_exception_empty_context(self) -> None:
        """Test logging TributumError with empty context."""
        cap = LogCapture()
        structlog.configure(processors=[cap])

        logger = get_logger("test")
        error = TributumError(ErrorCode.INTERNAL_ERROR, "System error")

        log_exception(logger, error)

        assert len(cap.entries) == 1
        entry = cap.entries[0]
        assert "error_context" not in entry
        assert entry["error_code"] == "INTERNAL_ERROR"

    def test_log_exception_chain_handling(self) -> None:
        """Test that exception chains are preserved in logging."""
        cap = LogCapture()
        structlog.configure(processors=[cap])

        logger = get_logger("test")

        try:
            try:
                raise ValueError("Original error")
            except ValueError as e:
                raise BusinessRuleError("Business rule failed", cause=e) from e
        except BusinessRuleError as business_error:
            log_exception(logger, business_error)

        assert len(cap.entries) == 1
        entry = cap.entries[0]
        assert entry["error_code"] == "INTERNAL_ERROR"
        # The exc_info should contain the full exception chain
        assert entry["exc_info"] is not None


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

    def test_get_logger_with_initial_context(self) -> None:
        """Test get_logger with initial context parameters."""
        cap = LogCapture()
        structlog.configure(
            processors=[
                cap,
            ]
        )

        # Create logger with initial context
        logger = get_logger("test", service="api", version="1.0")
        logger.info("test message")

        assert len(cap.entries) == 1
        entry = cap.entries[0]
        assert entry["service"] == "api"
        assert entry["version"] == "1.0"

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


class TestORJSONRenderer:
    """Test the ORJSONRenderer custom processor."""

    def test_basic_json_rendering(self, mocker: MockerFixture) -> None:
        """Test basic JSON rendering with simple types."""
        renderer = ORJSONRenderer()
        logger = mocker.MagicMock()
        event_dict = {
            "event": "test message",
            "level": "INFO",
            "number": 123,
            "float": 45.67,
            "bool": True,
            "none": None,
        }

        result = renderer(logger, "test", event_dict)

        # Parse the result to verify it's valid JSON

        parsed = json.loads(result)
        assert parsed["event"] == "test message"
        assert parsed["level"] == "INFO"
        assert parsed["number"] == 123
        assert parsed["float"] == 45.67
        assert parsed["bool"] is True
        assert parsed["none"] is None

    def test_datetime_handling(self, mocker: MockerFixture) -> None:
        """Test that datetime objects are serialized correctly."""
        renderer = ORJSONRenderer()
        logger = mocker.MagicMock()
        now = datetime.datetime.now(datetime.UTC)
        event_dict = {"event": "test", "timestamp": now}

        result = renderer(logger, "test", event_dict)

        parsed = json.loads(result)
        assert parsed["event"] == "test"
        # orjson serializes datetime to ISO format string
        assert isinstance(parsed["timestamp"], str)
        assert now.isoformat() in parsed["timestamp"]

    def test_uuid_handling(self, mocker: MockerFixture) -> None:
        """Test that UUID objects are serialized correctly."""
        renderer = ORJSONRenderer()
        logger = mocker.MagicMock()
        test_uuid = uuid.uuid4()
        event_dict = {"event": "test", "id": test_uuid}

        result = renderer(logger, "test", event_dict)

        parsed = json.loads(result)
        assert parsed["event"] == "test"
        assert parsed["id"] == str(test_uuid)

    def test_exception_handling(self, mocker: MockerFixture) -> None:
        """Test that exceptions are converted to strings."""
        renderer = ORJSONRenderer()
        logger = mocker.MagicMock()
        error = ValueError("Test error")
        event_dict = {"event": "error occurred", "exception": error}

        result = renderer(logger, "test", event_dict)

        parsed = json.loads(result)
        assert parsed["event"] == "error occurred"
        assert parsed["exception"] == "Test error"

    def test_type_handling(self, mocker: MockerFixture) -> None:
        """Test that type objects are converted to their names."""
        renderer = ORJSONRenderer()
        logger = mocker.MagicMock()
        event_dict = {"event": "test", "error_type": ValueError}

        result = renderer(logger, "test", event_dict)

        parsed = json.loads(result)
        assert parsed["event"] == "test"
        assert parsed["error_type"] == "ValueError"

    def test_nested_dict_processing(self, mocker: MockerFixture) -> None:
        """Test that nested dictionaries are processed correctly."""
        renderer = ORJSONRenderer()
        logger = mocker.MagicMock()
        error = Exception("nested error")
        event_dict = {
            "event": "test",
            "context": {
                "user": {"id": 123, "name": "test"},
                "error": error,
                "metadata": {"type": ValueError},
            },
        }

        result = renderer(logger, "test", event_dict)

        parsed = json.loads(result)
        assert parsed["event"] == "test"
        assert parsed["context"]["user"]["id"] == 123
        assert parsed["context"]["error"] == "nested error"
        assert parsed["context"]["metadata"]["type"] == "ValueError"

    def test_list_processing(self, mocker: MockerFixture) -> None:
        """Test that lists containing special types are processed."""
        renderer = ORJSONRenderer()
        logger = mocker.MagicMock()
        errors = [ValueError("error1"), TypeError("error2")]
        event_dict = {"event": "test", "errors": errors, "numbers": [1, 2, 3]}

        result = renderer(logger, "test", event_dict)

        parsed = json.loads(result)
        assert parsed["event"] == "test"
        assert parsed["errors"] == ["error1", "error2"]
        assert parsed["numbers"] == [1, 2, 3]

    def test_tuple_processing(self, mocker: MockerFixture) -> None:
        """Test that tuples containing special types are processed."""
        renderer = ORJSONRenderer()
        logger = mocker.MagicMock()
        # Test with tuple containing various types
        event_dict = {
            "event": "test",
            "tuple_data": (ValueError("error1"), dict, {"nested": True}, 123),
            "mixed_tuple": (1, "string", None, True),
        }

        result = renderer(logger, "test", event_dict)

        parsed = json.loads(result)
        assert parsed["event"] == "test"
        # Tuples are converted to lists in JSON
        assert parsed["tuple_data"] == ["error1", "dict", {"nested": True}, 123]
        assert parsed["mixed_tuple"] == [1, "string", None, True]

    def test_sort_keys_option(self, mocker: MockerFixture) -> None:
        """Test that keys are sorted for consistency."""
        renderer = ORJSONRenderer()
        logger = mocker.MagicMock()
        event_dict = {
            "zebra": 1,
            "alpha": 2,
            "beta": 3,
            "event": "test",
        }

        result = renderer(logger, "test", event_dict)

        # Keys should be in sorted order
        assert result.index("alpha") < result.index("beta")
        assert result.index("beta") < result.index("event")
        assert result.index("event") < result.index("zebra")

    def test_custom_options_initialization(self, mocker: MockerFixture) -> None:
        """Test ORJSONRenderer with custom options."""
        # Test with valid orjson option
        renderer = ORJSONRenderer(OPT_INDENT_2=True)
        logger = mocker.MagicMock()
        event_dict = {"event": "test", "nested": {"key": "value"}}

        result = renderer(logger, "test", event_dict)

        # Should include indentation
        assert "  " in result  # Check for indentation

        # Test with invalid option (should be ignored)
        renderer2 = ORJSONRenderer(INVALID_OPTION=True)
        result2 = renderer2(logger, "test", event_dict)

        # Should still produce valid JSON

        parsed = json.loads(result2)
        assert parsed["event"] == "test"

    def test_performance_comparison(self, mocker: MockerFixture) -> None:
        """Test that ORJSONRenderer performs well compared to JSONRenderer."""
        # Create test data with various types
        event_dict = {
            "event": "performance test",
            "timestamp": datetime.datetime.now(datetime.UTC),
            "user_id": 12345,
            "metadata": {
                "nested": True,
                "values": list(range(100)),
                "mapping": {str(i): i for i in range(50)},
            },
        }

        # Test ORJSONRenderer
        orjson_renderer = ORJSONRenderer()
        logger = mocker.MagicMock()

        # Warm up
        for _ in range(10):
            orjson_renderer(logger, "test", event_dict)

        # Just verify it works correctly and produces valid output
        result = orjson_renderer(logger, "test", event_dict)

        parsed = json.loads(result)

        # Verify the output is correct
        assert parsed["event"] == "performance test"
        assert parsed["user_id"] == 12345
        assert len(parsed["metadata"]["values"]) == 100
        assert len(parsed["metadata"]["mapping"]) == 50

    def test_complex_real_world_log(self, mocker: MockerFixture) -> None:
        """Test with a complex log entry similar to real usage."""
        renderer = ORJSONRenderer()
        logger = mocker.MagicMock()

        # Simulate a real log entry
        event_dict = {
            "event": "api_request_completed",
            "level": "INFO",
            "timestamp": datetime.datetime.now(datetime.UTC),
            "correlation_id": str(uuid.uuid4()),
            "logger": "api.handlers",
            "filename": "handlers.py",
            "lineno": 123,
            "func_name": "handle_request",
            "request": {
                "method": "POST",
                "path": "/api/users",
                "headers": {"content-type": "application/json"},
            },
            "response": {"status_code": 200, "duration_ms": 45.23},
            "user_id": 789,
            "error_context": None,
            "tags": ["api", "success"],
        }

        result = renderer(logger, "test", event_dict)

        # Should produce valid JSON

        parsed = json.loads(result)
        assert parsed["event"] == "api_request_completed"
        assert parsed["request"]["method"] == "POST"
        assert parsed["response"]["duration_ms"] == 45.23
        assert parsed["tags"] == ["api", "success"]
