"""Unit tests for logger factory functions."""

from collections.abc import Generator

import pytest
import structlog
from structlog.testing import LogCapture

from src.core.logging import configure_structlog, get_logger


@pytest.mark.unit
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
