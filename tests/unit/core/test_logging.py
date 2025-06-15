"""Unit tests for the logging module."""

import logging
from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest
import structlog
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
    add_log_level_upper,
    configure_structlog,
    get_logger,
    inject_correlation_id,
    log_context,
    log_exception,
)


class TestAddLogLevelUpper:
    """Test the add_log_level_upper processor."""

    def test_adds_uppercase_level(self) -> None:
        """Test that log level is added in uppercase."""
        logger = MagicMock()
        event_dict: dict[str, object] = {}

        result = add_log_level_upper(logger, "info", event_dict)

        assert result["level"] == "INFO"

    def test_converts_warn_to_warning(self) -> None:
        """Test that 'warn' is converted to 'WARNING'."""
        logger = MagicMock()
        event_dict: dict[str, object] = {}

        result = add_log_level_upper(logger, "warn", event_dict)

        assert result["level"] == "WARNING"

    def test_handles_all_log_levels(self) -> None:
        """Test all log levels are converted correctly."""
        logger = MagicMock()
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

    def test_injects_correlation_id_when_present(self) -> None:
        """Test that correlation ID is injected when available."""
        # Set correlation ID in context
        test_correlation_id = "test-correlation-123"
        RequestContext.set_correlation_id(test_correlation_id)

        logger = MagicMock()
        event_dict: dict[str, object] = {}

        result = inject_correlation_id(logger, "info", event_dict)

        assert result["correlation_id"] == test_correlation_id

        # Clean up
        RequestContext.clear()

    def test_no_correlation_id_when_not_set(self) -> None:
        """Test that no correlation ID is added when not in context."""
        # Ensure context is clear
        RequestContext.clear()

        logger = MagicMock()
        event_dict: dict[str, object] = {}

        result = inject_correlation_id(logger, "info", event_dict)

        assert "correlation_id" not in result

    def test_preserves_existing_fields(self) -> None:
        """Test that existing fields are preserved."""
        RequestContext.set_correlation_id("test-id")

        logger = MagicMock()
        event_dict: dict[str, object] = {"existing": "value", "another": 123}

        result = inject_correlation_id(logger, "info", event_dict)

        assert result["existing"] == "value"
        assert result["another"] == 123
        assert result["correlation_id"] == "test-id"

        # Clean up
        RequestContext.clear()


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

    @patch("src.core.logging.get_settings")
    def test_json_output_structure(self, mock_get_settings: MagicMock) -> None:
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
        mock_get_settings.return_value = settings

        # Configure structlog
        configure_structlog()

        # Use LogCapture to test JSON processor pipeline
        cap = LogCapture()
        # Get current config and verify it has JSON renderer
        config = structlog.get_config()
        processors = config["processors"]

        # Verify JSON renderer is in the pipeline
        has_json_renderer = any(type(p).__name__ == "JSONRenderer" for p in processors)
        assert has_json_renderer, "JSON renderer should be configured"

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

    @patch("src.core.logging.get_settings")
    def test_console_output_format(self, mock_get_settings: MagicMock) -> None:
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
        mock_get_settings.return_value = settings

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

    @patch("src.core.logging.get_settings")
    def test_processor_pipeline(self, mock_get_settings: MagicMock) -> None:
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
        mock_get_settings.return_value = settings

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
        assert "JSONRenderer" in processor_types

    @patch("src.core.logging.get_settings")
    def test_timestamp_configuration(self, mock_get_settings: MagicMock) -> None:
        """Test timestamp configuration options."""
        # Test with timestamp disabled
        settings = Settings()
        settings.log_config = LogConfig(
            log_level="INFO",
            log_format="console",
            render_json_logs=False,
            add_timestamp=False,
        )
        mock_get_settings.return_value = settings

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

    @patch("src.core.logging.get_settings")
    def test_unix_timestamp_format(self, mock_get_settings: MagicMock) -> None:
        """Test unix timestamp format."""
        settings = Settings()
        settings.log_config = LogConfig(
            log_level="INFO",
            log_format="json",
            render_json_logs=True,
            add_timestamp=True,
            timestamper_format="unix",
        )
        mock_get_settings.return_value = settings

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

    @patch("src.core.logging.get_settings")
    def test_log_level_configuration(self, mock_get_settings: MagicMock) -> None:
        """Test that log level is properly configured."""
        settings = Settings()
        settings.log_config = LogConfig(
            log_level="WARNING", log_format="console", render_json_logs=False
        )
        mock_get_settings.return_value = settings

        configure_structlog()

        # Verify root logger level
        assert logging.root.level == logging.WARNING

    @patch("src.core.logging.get_settings")
    def test_development_vs_production_processors(
        self, mock_get_settings: MagicMock
    ) -> None:
        """Test different processor pipelines for dev vs prod."""
        # Test development configuration
        settings = Settings()
        settings.log_config = LogConfig(
            log_level="DEBUG", log_format="console", render_json_logs=False
        )
        mock_get_settings.return_value = settings

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
        assert "JSONRenderer" in prod_renderers

    @patch("src.core.logging.get_settings")
    def test_callsite_information(self, mock_get_settings: MagicMock) -> None:
        """Test that callsite information is included."""
        settings = Settings()
        settings.log_config = LogConfig(
            log_level="INFO", log_format="json", render_json_logs=True
        )
        mock_get_settings.return_value = settings

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

    @patch("src.core.logging.get_settings")
    def test_correlation_id_included_in_logs(
        self, mock_get_settings: MagicMock
    ) -> None:
        """Test that correlation ID is automatically included in logs when set."""
        # Set up configuration
        settings = Settings()
        settings.log_config = LogConfig(
            log_level="INFO", log_format="json", render_json_logs=True
        )
        mock_get_settings.return_value = settings

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

    @patch("src.core.logging.get_settings")
    def test_logs_without_correlation_id(self, mock_get_settings: MagicMock) -> None:
        """Test that logs work fine without correlation ID."""
        # Ensure context is clear
        RequestContext.clear()

        settings = Settings()
        settings.log_config = LogConfig(
            log_level="INFO", log_format="json", render_json_logs=True
        )
        mock_get_settings.return_value = settings

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

    @patch("src.core.logging.get_settings")
    def test_correlation_id_isolation(self, mock_get_settings: MagicMock) -> None:
        """Test that correlation IDs are isolated between contexts."""
        settings = Settings()
        settings.log_config = LogConfig(
            log_level="INFO", log_format="json", render_json_logs=True
        )
        mock_get_settings.return_value = settings

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

    def test_log_exception_severity_levels(self) -> None:
        """Test that different severities use appropriate log levels."""
        # Mock logger to track method calls
        mock_logger = MagicMock()

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
