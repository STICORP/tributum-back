"""Integration tests for system metrics collection background task."""

import pytest
from pytest_mock import MockerFixture

from src.api.main import lifespan
from src.core.config import Settings


@pytest.mark.integration
class TestSystemMetricsTask:
    """Test cases for system metrics collection background task."""

    async def test_database_startup_failure(self, mocker: MockerFixture) -> None:
        """Test application startup fails when database is unavailable."""
        # Mock settings
        mock_settings = Settings()
        mocker.patch("src.api.main.get_settings", return_value=mock_settings)

        # Phase 0: Removed mock for setup_tracing which no longer exists

        # Mock failed database check - patch at the usage location in main.py
        mocker.patch(
            "src.api.main.check_database_connection",
            return_value=(False, "Connection refused"),
        )

        # Mock close_database to prevent issues during shutdown
        mocker.patch("src.api.main.close_database")

        # Mock logger
        mock_logger = mocker.Mock()
        mocker.patch("src.api.main.logger", mock_logger)

        # Phase 0: Removed mock for tracer and span which no longer exist

        # Mock FastAPI app
        mock_app = mocker.Mock()
        mock_app.title = "Test App"
        mock_app.version = "1.0.0"

        # Test that RuntimeError is raised
        with pytest.raises(RuntimeError, match="Database connection failed"):
            async with lifespan(mock_app):
                pass

        # Verify error logging - updated to match new logging format
        mock_logger.error.assert_called_once_with(
            "Database connection failed during startup: %s",
            "Connection refused",
        )

        # Phase 0: Removed span attribute verification as tracing no longer exists
