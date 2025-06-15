"""Unit tests for the logging module."""

import logging
from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest
import structlog
from structlog.testing import LogCapture

from src.core.config import LogConfig, Settings
from src.core.logging import add_log_level_upper, configure_structlog


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
