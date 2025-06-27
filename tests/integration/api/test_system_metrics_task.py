"""Integration tests for system metrics collection background task."""

import asyncio
from collections.abc import Coroutine
from typing import Any

import pytest
from pytest_mock import MockerFixture

from src.api.main import lifespan
from src.core.config import Settings


@pytest.mark.integration
class TestSystemMetricsTask:
    """Test cases for system metrics collection background task."""

    async def test_system_metrics_task_disabled(self, mocker: MockerFixture) -> None:
        """Test that system metrics task is not started when disabled."""
        # Mock settings with metrics disabled
        mock_settings = Settings()
        mock_settings.observability_config.enable_metrics = False
        mocker.patch("src.api.main.get_settings", return_value=mock_settings)

        # Mock setup_tracing to avoid actual initialization
        mocker.patch("src.api.main.setup_tracing")

        # Mock database check
        mocker.patch(
            "src.api.main.check_database_connection",
            return_value=(True, None),
        )

        # Mock logger
        mock_logger = mocker.patch("src.api.main.get_logger")

        # Mock FastAPI app
        mock_app = mocker.Mock()
        mock_app.title = "Test App"
        mock_app.version = "1.0.0"

        # Track if background task was created
        mock_create_task = mocker.patch("asyncio.create_task")

        # Run lifespan
        async with lifespan(mock_app):
            pass

        # Verify no background task was created
        mock_create_task.assert_not_called()

        # Verify no cancellation logs
        mock_logger.return_value.info.assert_any_call(
            "Application startup complete",
            app_name="Test App",
            version="1.0.0",
        )

    async def test_system_metrics_task_enabled(self, mocker: MockerFixture) -> None:
        """Test that system metrics task starts when enabled."""
        # Mock settings with metrics enabled and short interval
        mock_settings = Settings()
        mock_settings.observability_config.enable_metrics = True
        mock_settings.observability_config.enable_system_metrics = True
        mock_settings.observability_config.system_metrics_interval_s = (
            60  # Normal interval
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
        mock_logger = mocker.patch("src.api.main.get_logger")

        # Mock get_engine and pool metrics
        mock_engine = mocker.Mock()
        mock_pool = mocker.Mock()
        mock_engine.pool = mock_pool
        mocker.patch("src.api.main.get_engine", return_value=mock_engine)

        # Mock get_database_pool_metrics
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

        # Track background task
        created_tasks: list[asyncio.Task[None]] = []
        original_create_task = asyncio.create_task

        def mock_create_task(coro: Coroutine[Any, Any, None]) -> asyncio.Task[None]:
            task = original_create_task(coro)
            created_tasks.append(task)
            return task

        mocker.patch("asyncio.create_task", side_effect=mock_create_task)

        # Run lifespan
        async with lifespan(mock_app):
            # Let startup complete
            await asyncio.sleep(0.01)

        # Verify background task was created
        assert len(created_tasks) == 1
        background_task = created_tasks[0]
        assert background_task.done()

        # Verify startup logs
        mock_logger.return_value.info.assert_any_call(
            "Starting system metrics collection task",
            interval_seconds=60,
        )

        # Verify cancellation logs
        mock_logger.return_value.info.assert_any_call(
            "Cancelling system metrics collection task"
        )

    async def test_database_startup_failure(self, mocker: MockerFixture) -> None:
        """Test application startup fails when database is unavailable."""
        # Mock settings
        mock_settings = Settings()
        mocker.patch("src.api.main.get_settings", return_value=mock_settings)

        # Mock setup_tracing
        mocker.patch("src.api.main.setup_tracing")

        # Mock failed database check
        mocker.patch(
            "src.api.main.check_database_connection",
            return_value=(False, "Connection refused"),
        )

        # Mock logger
        mock_logger_instance = mocker.Mock()
        mocker.patch("src.api.main.get_logger", return_value=mock_logger_instance)

        # Mock tracer and span
        mock_tracer = mocker.Mock()
        mock_span = mocker.Mock()
        mock_tracer.start_as_current_span.return_value.__enter__ = mocker.Mock(
            return_value=mock_span
        )
        mock_tracer.start_as_current_span.return_value.__exit__ = mocker.Mock(
            return_value=None
        )
        mocker.patch("src.api.main.get_tracer", return_value=mock_tracer)

        # Mock FastAPI app
        mock_app = mocker.Mock()
        mock_app.title = "Test App"
        mock_app.version = "1.0.0"

        # Test that RuntimeError is raised
        with pytest.raises(RuntimeError, match="Database connection failed"):
            async with lifespan(mock_app):
                pass

        # Verify error logging
        mock_logger_instance.error.assert_called_once_with(
            "Database connection failed during startup",
            error_message="Connection refused",
        )

        # Verify span attributes
        mock_span.set_attribute.assert_any_call("database.connection_check", "failed")
        mock_span.set_attribute.assert_any_call("error.message", "Connection refused")
