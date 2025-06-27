"""Simple integration tests to achieve full coverage of main.py."""

import asyncio

import pytest
from pytest_mock import MockerFixture

from src.api.main import lifespan
from src.core.config import Settings


@pytest.mark.integration
class TestMainSimpleCoverage:
    """Test cases to cover remaining lines in main.py."""

    async def test_pool_exhaustion_and_error_handling(
        self, mocker: MockerFixture
    ) -> None:
        """Test pool exhaustion warning and error handling in background task."""
        # Create custom settings
        settings = Settings()
        settings.observability_config.enable_metrics = True
        settings.observability_config.enable_system_metrics = True
        settings.observability_config.system_metrics_interval_s = 10  # Minimum allowed

        # Mock settings
        mocker.patch("src.api.main.get_settings", return_value=settings)
        mocker.patch("src.api.main.setup_tracing")
        mocker.patch(
            "src.api.main.check_database_connection", return_value=(True, None)
        )

        # Create a mock logger to track calls
        mock_logger = mocker.Mock()
        mocker.patch("src.api.main.get_logger", return_value=mock_logger)

        # Create a controlled sequence of behaviors
        call_count = 0

        def get_pool_metrics_side_effect(pool: object) -> dict[str, int]:
            _ = pool  # Mark as used
            nonlocal call_count
            call_count += 1

            if call_count == 1:
                # First call: pool exhausted
                return {
                    "size": 10,
                    "checked_in": 0,
                    "checked_out": 10,  # All connections checked out
                    "overflow": 0,
                    "total": 10,
                }
            if call_count == 2:
                # Second call: raise exception
                raise RuntimeError("Database error")
            # Subsequent calls: normal
            return {
                "size": 10,
                "checked_in": 8,
                "checked_out": 2,
                "overflow": 0,
                "total": 10,
            }

        mocker.patch(
            "src.api.main.get_database_pool_metrics",
            side_effect=get_pool_metrics_side_effect,
        )

        # Mock get_engine
        mock_engine = mocker.Mock()
        mock_engine.pool = mocker.Mock()
        mocker.patch("src.api.main.get_engine", return_value=mock_engine)

        # Mock app
        mock_app = mocker.Mock()
        mock_app.title = "Test"
        mock_app.version = "1.0"

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

        # Run the lifespan briefly
        async def run_lifespan() -> None:
            async with lifespan(mock_app):
                # Wait for background task to run a few iterations
                # We need to wait long enough for at least 2 calls to get_pool_metrics
                for _ in range(5):
                    await original_sleep(0.01)

        await run_lifespan()

        # Verify the warning was logged for pool exhaustion
        warning_calls = [
            call
            for call in mock_logger.warning.call_args_list
            if "Database connection pool exhausted" in str(call)
        ]
        assert len(warning_calls) > 0

        # Verify the exception was logged
        exception_calls = [
            call
            for call in mock_logger.exception.call_args_list
            if "Error in system metrics collection" in str(call)
        ]
        assert len(exception_calls) > 0

        # Verify cancellation was logged
        info_calls = [
            call
            for call in mock_logger.info.call_args_list
            if "System metrics collection task cancelled" in str(call)
        ]
        assert len(info_calls) > 0
