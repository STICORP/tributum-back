"""Tests for performance metrics configuration in RequestLoggingMiddleware."""

import asyncio

import pytest
from fastapi import Response
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

from src.core.config import LogConfig

from .conftest import create_test_app


@pytest.mark.unit
class TestPerformanceMetricsConfiguration:
    """Test cases for performance metrics configuration."""

    def test_disable_all_performance_metrics(self, mocker: MockerFixture) -> None:
        """Test that all performance metrics can be disabled."""
        mock_logger = mocker.Mock()
        _mock_get_logger = mocker.patch(
            "src.api.middleware.request_logging.get_logger", return_value=mock_logger
        )

        # Create app with performance metrics disabled
        app = create_test_app(log_config=LogConfig(enable_performance_metrics=False))
        client = TestClient(app)
        response = client.get("/test")
        assert response.status_code == 200

        # Find the request_completed call
        completed_calls = [
            call
            for call in mock_logger.info.call_args_list
            if call[0][0] == "request_completed"
        ]
        assert len(completed_calls) == 1

        # Verify no performance metrics are included
        call_kwargs = completed_calls[0][1]
        assert "duration_ms" not in call_kwargs
        assert "active_tasks" not in call_kwargs
        assert "active_tasks_delta" not in call_kwargs
        assert "memory_delta_mb" not in call_kwargs

    def test_disable_duration_tracking_only(self, mocker: MockerFixture) -> None:
        """Test disabling only duration tracking."""
        mock_logger = mocker.Mock()
        _mock_get_logger = mocker.patch(
            "src.api.middleware.request_logging.get_logger", return_value=mock_logger
        )

        # Create app with only duration tracking disabled
        app = create_test_app(
            log_config=LogConfig(
                enable_performance_metrics=True,
                track_request_duration=False,
                track_active_tasks=True,
            )
        )
        client = TestClient(app)
        response = client.get("/test")
        assert response.status_code == 200

        # Find the request_completed call
        completed_calls = [
            call
            for call in mock_logger.info.call_args_list
            if call[0][0] == "request_completed"
        ]
        assert len(completed_calls) == 1

        # Verify duration is not included but other metrics are
        call_kwargs = completed_calls[0][1]
        assert "duration_ms" not in call_kwargs
        assert "active_tasks" in call_kwargs
        assert "active_tasks_delta" in call_kwargs

    def test_disable_active_tasks_tracking_only(self, mocker: MockerFixture) -> None:
        """Test disabling only active tasks tracking."""
        mock_logger = mocker.Mock()
        _mock_get_logger = mocker.patch(
            "src.api.middleware.request_logging.get_logger", return_value=mock_logger
        )

        # Create app with only active tasks tracking disabled
        app = create_test_app(
            log_config=LogConfig(
                enable_performance_metrics=True,
                track_request_duration=True,
                track_active_tasks=False,
            )
        )
        client = TestClient(app)
        response = client.get("/test")
        assert response.status_code == 200

        # Find the request_completed call
        completed_calls = [
            call
            for call in mock_logger.info.call_args_list
            if call[0][0] == "request_completed"
        ]
        assert len(completed_calls) == 1

        # Verify active tasks are not included but duration is
        call_kwargs = completed_calls[0][1]
        assert "duration_ms" in call_kwargs
        assert "active_tasks" not in call_kwargs
        assert "active_tasks_delta" not in call_kwargs

    def test_disable_request_sizes_tracking(self, mocker: MockerFixture) -> None:
        """Test disabling request/response size tracking."""
        mock_logger = mocker.Mock()
        _mock_get_logger = mocker.patch(
            "src.api.middleware.request_logging.get_logger", return_value=mock_logger
        )

        # Create app with size tracking disabled but body logging enabled
        app = create_test_app(
            log_config=LogConfig(
                enable_performance_metrics=True,
                track_request_sizes=False,
                log_request_body=True,
                log_response_body=True,
            )
        )
        client = TestClient(app)
        response = client.post("/echo", json={"username": "test", "password": "pass"})
        assert response.status_code == 200

        # Find the request_completed call
        completed_calls = [
            call
            for call in mock_logger.info.call_args_list
            if call[0][0] == "request_completed"
        ]
        assert len(completed_calls) == 1

        # Verify size metrics are not included even with body logging
        call_kwargs = completed_calls[0][1]
        assert "request_size_bytes" not in call_kwargs
        assert "response_size_bytes" not in call_kwargs
        # But body content should still be logged
        assert "request_body" in call_kwargs or "response_body" in call_kwargs

    def test_threshold_warnings_respect_config(self, mocker: MockerFixture) -> None:
        """Test that threshold warnings respect performance metrics config."""
        mock_logger = mocker.Mock()
        _mock_get_logger = mocker.patch(
            "src.api.middleware.request_logging.get_logger", return_value=mock_logger
        )

        # Create app with performance metrics disabled but low thresholds
        app = create_test_app(
            log_config=LogConfig(
                enable_performance_metrics=False,
                slow_request_threshold_ms=1,
                critical_request_threshold_ms=5,
            )
        )

        # Add slow endpoint
        @app.get("/slow")
        async def slow_endpoint() -> Response:
            await asyncio.sleep(0.01)  # 10ms delay
            return Response(content="slow")

        client = TestClient(app)
        response = client.get("/slow")
        assert response.status_code == 200

        # Should not log warning/error when metrics disabled
        assert mock_logger.warning.call_count == 0
        assert mock_logger.error.call_count == 0
        # Should still log info
        info_calls = [
            call
            for call in mock_logger.info.call_args_list
            if call[0][0] == "request_completed"
        ]
        assert len(info_calls) == 1

    def test_opentelemetry_span_attributes_respect_config(
        self, mocker: MockerFixture
    ) -> None:
        """Test that OpenTelemetry span attributes respect configuration."""
        mock_logger = mocker.Mock()
        _mock_get_logger = mocker.patch(
            "src.api.middleware.request_logging.get_logger", return_value=mock_logger
        )

        # Mock OpenTelemetry span
        mock_span = mocker.MagicMock()
        mock_span.is_recording.return_value = True
        mocker.patch(
            "src.api.middleware.request_logging.trace.get_current_span",
            return_value=mock_span,
        )

        # Create app with performance metrics disabled
        app = create_test_app(log_config=LogConfig(enable_performance_metrics=False))
        client = TestClient(app)
        response = client.get("/test")
        assert response.status_code == 200

        # Verify no performance attributes were added to span
        mock_span.set_attribute.assert_not_called()
        mock_span.add_event.assert_not_called()

    def test_memory_tracking_requires_performance_metrics(
        self, mocker: MockerFixture
    ) -> None:
        """Test that memory tracking requires performance metrics to be enabled."""
        mock_logger = mocker.Mock()
        _mock_get_logger = mocker.patch(
            "src.api.middleware.request_logging.get_logger", return_value=mock_logger
        )

        # Mock tracemalloc
        mock_tracemalloc = mocker.patch(
            "src.api.middleware.request_logging.tracemalloc"
        )

        # Create app with memory tracking enabled but performance metrics disabled
        app = create_test_app(
            log_config=LogConfig(
                enable_performance_metrics=False,
                enable_memory_tracking=True,
            )
        )
        client = TestClient(app)
        response = client.get("/test")
        assert response.status_code == 200

        # Verify tracemalloc was not used
        mock_tracemalloc.is_tracing.assert_not_called()
        mock_tracemalloc.start.assert_not_called()
        mock_tracemalloc.get_traced_memory.assert_not_called()

    def test_selective_span_attributes(self, mocker: MockerFixture) -> None:
        """Test selective span attribute addition based on config."""
        mock_logger = mocker.Mock()
        _mock_get_logger = mocker.patch(
            "src.api.middleware.request_logging.get_logger", return_value=mock_logger
        )

        # Mock OpenTelemetry span
        mock_span = mocker.MagicMock()
        mock_span.is_recording.return_value = True
        mocker.patch(
            "src.api.middleware.request_logging.trace.get_current_span",
            return_value=mock_span,
        )

        # Create app with selective tracking
        app = create_test_app(
            log_config=LogConfig(
                enable_performance_metrics=True,
                track_request_duration=True,
                track_active_tasks=False,
                track_request_sizes=False,
            )
        )
        client = TestClient(app)
        response = client.post("/echo", json={"username": "test", "password": "pass"})
        assert response.status_code == 200

        # Verify only duration was added to span
        attribute_calls = {
            call[0][0]: call[0][1] for call in mock_span.set_attribute.call_args_list
        }
        assert "http.request.duration_ms" in attribute_calls
        assert "process.active_tasks" not in attribute_calls
        assert "http.request.size_bytes" not in attribute_calls
        assert "http.response.size_bytes" not in attribute_calls
