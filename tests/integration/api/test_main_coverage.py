"""Integration tests to achieve full coverage of main.py."""

import asyncio
from contextlib import suppress

import pytest
from pytest_mock import MockerFixture

from src.api.main import lifespan
from src.core.config import Settings


@pytest.mark.integration
class TestMainCoverage:
    """Test cases to cover remaining lines in main.py."""

    async def test_database_pool_metrics_logging(self, mocker: MockerFixture) -> None:
        """Test that database pool metrics are logged in the background task."""
        # Mock settings with metrics enabled
        mock_settings = Settings()
        mock_settings.observability_config.enable_metrics = True
        mock_settings.observability_config.enable_system_metrics = True
        mock_settings.observability_config.system_metrics_interval_s = (
            10  # Minimum allowed
        )
        mocker.patch("src.api.main.get_settings", return_value=mock_settings)

        # Mock setup_tracing
        mocker.patch("src.api.main.setup_tracing")

        # Mock database check
        mocker.patch(
            "src.api.main.check_database_connection",
            return_value=(True, None),
        )

        # Mock logger
        mock_logger_instance = mocker.Mock()
        mocker.patch("src.api.main.get_logger", return_value=mock_logger_instance)

        # Mock get_engine and pool
        mock_engine = mocker.Mock()
        mock_pool = mocker.Mock()
        mock_engine.pool = mock_pool
        mocker.patch("src.api.main.get_engine", return_value=mock_engine)

        # Mock pool metrics - normal state
        mock_pool_metrics = {
            "size": 10,
            "checked_in": 8,
            "checked_out": 2,
            "overflow": 0,
            "total": 10,
        }
        mocker.patch(
            "src.api.main.get_database_pool_metrics",
            return_value=mock_pool_metrics,
        )

        # Mock FastAPI app
        mock_app = mocker.Mock()
        mock_app.title = "Test App"
        mock_app.version = "1.0.0"

        # Mock asyncio.sleep to speed up the test
        sleep_count = 0
        original_sleep = asyncio.sleep

        async def mock_sleep(seconds: float) -> None:
            _ = seconds  # Mark as used
            nonlocal sleep_count
            sleep_count += 1
            # Sleep for a very short time instead of the requested time
            await original_sleep(0.001)

        mocker.patch("asyncio.sleep", side_effect=mock_sleep)

        # Run lifespan with controlled duration
        task_executed = False

        async def run_with_timeout() -> None:
            nonlocal task_executed
            async with lifespan(mock_app):
                # Wait long enough for the task to execute at least once
                # Since we're patching sleep, we need to wait for multiple iterations
                for _ in range(5):
                    await original_sleep(0.01)
                task_executed = True

        # Run with a timeout to prevent hanging
        with suppress(TimeoutError):
            await asyncio.wait_for(run_with_timeout(), timeout=0.5)

        # Verify database pool metrics were logged
        assert task_executed
        # The debug log should have been called with pool metrics
        mock_logger_instance.debug.assert_called_with(
            "Database pool metrics",
            **mock_pool_metrics,
        )

    async def test_database_pool_no_engine(self, mocker: MockerFixture) -> None:
        """Test background task when engine is None."""
        # Mock settings with metrics enabled
        mock_settings = Settings()
        mock_settings.observability_config.enable_metrics = True
        mock_settings.observability_config.enable_system_metrics = True
        mock_settings.observability_config.system_metrics_interval_s = (
            10  # Minimum allowed
        )
        mocker.patch("src.api.main.get_settings", return_value=mock_settings)

        # Mock setup_tracing
        mocker.patch("src.api.main.setup_tracing")

        # Mock database check
        mocker.patch(
            "src.api.main.check_database_connection",
            return_value=(True, None),
        )

        # Mock logger
        mock_logger_instance = mocker.Mock()
        mocker.patch("src.api.main.get_logger", return_value=mock_logger_instance)

        # Mock get_engine to return None
        mocker.patch("src.api.main.get_engine", return_value=None)

        # Mock FastAPI app
        mock_app = mocker.Mock()
        mock_app.title = "Test App"
        mock_app.version = "1.0.0"

        # Mock asyncio.sleep to speed up the test
        sleep_count = 0
        original_sleep = asyncio.sleep

        async def mock_sleep(seconds: float) -> None:
            _ = seconds  # Mark as used
            nonlocal sleep_count
            sleep_count += 1
            # Sleep for a very short time instead of the requested time
            await original_sleep(0.001)

        mocker.patch("asyncio.sleep", side_effect=mock_sleep)

        # Run lifespan briefly
        task_executed = False

        async def run_with_timeout() -> None:
            nonlocal task_executed
            async with lifespan(mock_app):
                # Wait long enough for the task to execute at least once
                # Since we're patching sleep, we need to wait for multiple iterations
                for _ in range(5):
                    await original_sleep(0.01)
                task_executed = True

        # Run with a timeout
        with suppress(TimeoutError):
            await asyncio.wait_for(run_with_timeout(), timeout=0.5)

        assert task_executed
        # Verify no debug log was called (since engine is None)
        mock_logger_instance.debug.assert_not_called()
