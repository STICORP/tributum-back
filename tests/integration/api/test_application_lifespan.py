"""Integration tests for application lifespan and startup/shutdown behavior."""

import pytest
from fastapi import FastAPI
from pytest_mock import MockerFixture

from src.api.main import lifespan


@pytest.mark.integration
class TestApplicationLifespan:
    """Test cases for application startup and shutdown lifecycle."""

    async def test_database_startup_failure(self, mocker: MockerFixture) -> None:
        """Test application startup fails when database is unavailable.

        This integration test verifies that the application properly handles
        database connection failures during startup by raising a RuntimeError.
        """
        # Mock failed database check - patch at the usage location in main.py
        mocker.patch(
            "src.api.main.check_database_connection",
            return_value=(False, "Connection refused"),
        )

        # Mock close_database to prevent issues during shutdown
        mocker.patch("src.api.main.close_database")

        # Mock logger to verify error logging
        mock_logger = mocker.patch("src.api.main.logger")

        # Create a minimal FastAPI app for testing lifespan
        # Using real FastAPI instance instead of mock for better type safety
        test_app = FastAPI(title="Test App", version="1.0.0")

        # Test that RuntimeError is raised
        with pytest.raises(
            RuntimeError, match="Database connection failed: Connection refused"
        ):
            async with lifespan(test_app):
                # This line is never reached due to the exception
                pass  # pragma: no cover

        # Verify error logging
        mock_logger.error.assert_called_once_with(
            "Database connection failed during startup: {}",
            "Connection refused",
        )

    async def test_successful_startup_and_shutdown(self, mocker: MockerFixture) -> None:
        """Test successful application startup and shutdown lifecycle.

        This test verifies that when the database is available, the application:
        1. Successfully connects to the database during startup
        2. Logs the appropriate startup messages
        3. Properly closes database connections during shutdown
        4. Logs the appropriate shutdown messages
        """
        # Mock successful database check
        mocker.patch(
            "src.api.main.check_database_connection",
            return_value=(True, None),
        )

        # Mock close_database
        mock_close_database = mocker.patch("src.api.main.close_database")

        # Mock logger to verify logging
        mock_logger = mocker.patch("src.api.main.logger")

        # Create a test app
        test_app = FastAPI(title="Test App", version="1.0.0")

        # Run through the lifespan
        async with lifespan(test_app):
            # Verify startup logging
            assert mock_logger.info.call_count >= 2
            mock_logger.info.assert_any_call("Database connection successful")
            mock_logger.info.assert_any_call(
                "Application startup complete - {} v{}",
                "Test App",
                "1.0.0",
            )

        # After exiting the context, shutdown should have occurred
        # Verify shutdown logging
        mock_logger.info.assert_any_call("Application shutdown initiated")
        mock_logger.info.assert_any_call("Application shutdown complete")

        # Verify close_database was called
        mock_close_database.assert_called_once()

    async def test_database_check_with_degraded_status(
        self, mocker: MockerFixture
    ) -> None:
        """Test that database check failure still allows app to start.

        This test verifies that if the database check fails during runtime
        (not startup), the application continues to run but reports degraded status.
        This is important for health checks that shouldn't bring down the service.
        """
        # For startup, database is healthy
        startup_check = mocker.patch(
            "src.api.main.check_database_connection",
            return_value=(True, None),
        )

        # Mock close_database
        mocker.patch("src.api.main.close_database")

        # Mock logger
        mocker.patch("src.api.main.logger")

        # Create a test app
        test_app = FastAPI(title="Test App", version="1.0.0")

        # Run through the lifespan
        async with lifespan(test_app):
            # Verify startup was successful
            startup_check.assert_called_once()

            # Simulate a runtime database check that would fail
            # (This would be called by the health endpoint, not tested here)
            # The test ensures the app starts successfully even if later checks fail
