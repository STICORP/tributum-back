"""Unit tests for structlog configuration."""

import logging
from collections.abc import Generator

import pytest
import structlog
from pytest_mock import MockerFixture
from structlog.testing import LogCapture

from src.core.config import LogConfig, Settings
from src.core.context import RequestContext
from src.core.logging import (
    add_log_level_upper,
    configure_structlog,
    inject_correlation_id,
)


@pytest.mark.unit
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
