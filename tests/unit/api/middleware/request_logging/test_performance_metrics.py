"""Tests for performance metrics in RequestLoggingMiddleware."""

import asyncio
from unittest.mock import MagicMock

import pytest
from fastapi import Response
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

from src.core.config import LogConfig

from .conftest import create_test_app


@pytest.mark.unit
class TestPerformanceMetrics:
    """Test cases for performance metrics in RequestLoggingMiddleware."""

    def test_logs_slow_request_warning(self, mocker: MockerFixture) -> None:
        """Test that slow requests trigger warning logs."""
        mock_logger = mocker.Mock()
        _mock_get_logger = mocker.patch(
            "src.api.middleware.request_logging.get_logger", return_value=mock_logger
        )

        # Create app with low slow request threshold
        app = create_test_app(log_config=LogConfig(slow_request_threshold_ms=1))

        # Add endpoint with delay
        @app.get("/slow")
        async def slow_endpoint() -> Response:
            await asyncio.sleep(0.01)  # 10ms delay
            return Response(content="slow response")

        client = TestClient(app)
        response = client.get("/slow")
        assert response.status_code == 200

        # Should log warning for slow request
        warning_calls = [
            call
            for call in mock_logger.warning.call_args_list
            if call[0][0] == "request_completed_slow"
        ]
        assert len(warning_calls) == 1

        # Verify warning content
        call_kwargs = warning_calls[0][1]
        assert call_kwargs["method"] == "GET"
        assert call_kwargs["path"] == "/slow"
        assert call_kwargs["status_code"] == 200
        assert call_kwargs["duration_ms"] >= 10  # At least 10ms
        assert call_kwargs["threshold_ms"] == 1

    def test_logs_critical_slowness_error(self, mocker: MockerFixture) -> None:
        """Test that critically slow requests trigger error logs."""
        mock_logger = mocker.Mock()
        _mock_get_logger = mocker.patch(
            "src.api.middleware.request_logging.get_logger", return_value=mock_logger
        )

        # Create app with low critical threshold
        app = create_test_app(
            log_config=LogConfig(
                slow_request_threshold_ms=1, critical_request_threshold_ms=5
            )
        )

        # Add endpoint with longer delay
        @app.get("/very-slow")
        async def very_slow_endpoint() -> Response:
            await asyncio.sleep(0.01)  # 10ms delay
            return Response(content="very slow response")

        client = TestClient(app)
        response = client.get("/very-slow")
        assert response.status_code == 200

        # Should log error for critically slow request
        error_calls = [
            call
            for call in mock_logger.error.call_args_list
            if call[0][0] == "request_completed_critical_slowness"
        ]
        assert len(error_calls) == 1

        # Verify error content
        call_kwargs = error_calls[0][1]
        assert call_kwargs["method"] == "GET"
        assert call_kwargs["path"] == "/very-slow"
        assert call_kwargs["status_code"] == 200
        assert call_kwargs["duration_ms"] >= 10  # At least 10ms
        assert call_kwargs["threshold_ms"] == 5

    def test_tracks_request_response_sizes(self, mocker: MockerFixture) -> None:
        """Test that request and response sizes are tracked with body logging."""
        mock_logger = mocker.Mock()
        _mock_get_logger = mocker.patch(
            "src.api.middleware.request_logging.get_logger", return_value=mock_logger
        )

        # Create app with body logging enabled
        app = create_test_app(
            log_config=LogConfig(log_request_body=True, log_response_body=True)
        )

        client = TestClient(app)
        # Use the existing /echo endpoint from conftest
        request_body = {"username": "testuser", "password": "testpass"}
        response = client.post("/echo", json=request_body)
        assert response.status_code == 200

        # Find the request_completed call
        completed_calls = [
            call
            for call in mock_logger.info.call_args_list
            if call[0][0] == "request_completed"
        ]
        assert len(completed_calls) == 1

        # Verify size metrics are included
        call_kwargs = completed_calls[0][1]
        assert "request_size_bytes" in call_kwargs
        assert call_kwargs["request_size_bytes"] > 0  # Should have content
        assert "response_size_bytes" in call_kwargs
        assert call_kwargs["response_size_bytes"] > 0  # Should have content

    def test_tracks_active_asyncio_tasks(self, mocker: MockerFixture) -> None:
        """Test that active asyncio tasks are tracked."""
        mock_logger = mocker.Mock()
        _mock_get_logger = mocker.patch(
            "src.api.middleware.request_logging.get_logger", return_value=mock_logger
        )

        # Create app
        app = create_test_app()
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

        # Verify active tasks are tracked
        call_kwargs = completed_calls[0][1]
        assert "active_tasks" in call_kwargs
        assert isinstance(call_kwargs["active_tasks"], int)
        assert call_kwargs["active_tasks"] >= 0
        assert "active_tasks_delta" in call_kwargs
        assert isinstance(call_kwargs["active_tasks_delta"], int)

    def test_memory_tracking_when_enabled(self, mocker: MockerFixture) -> None:
        """Test that memory tracking works when enabled."""
        mock_logger = mocker.Mock()
        _mock_get_logger = mocker.patch(
            "src.api.middleware.request_logging.get_logger", return_value=mock_logger
        )

        # Mock tracemalloc
        mock_tracemalloc = mocker.patch(
            "src.api.middleware.request_logging.tracemalloc"
        )
        mock_tracemalloc.is_tracing.return_value = False
        mock_tracemalloc.get_traced_memory.side_effect = [
            (1000000, 2000000),  # Start: 1MB current, 2MB peak
            (1500000, 2000000),  # End: 1.5MB current, 2MB peak
        ]

        # Create app with memory tracking enabled
        app = create_test_app(log_config=LogConfig(enable_memory_tracking=True))
        client = TestClient(app)
        response = client.get("/test")
        assert response.status_code == 200

        # Verify tracemalloc was started
        mock_tracemalloc.start.assert_called_once()

        # Find the request_completed call
        completed_calls = [
            call
            for call in mock_logger.info.call_args_list
            if call[0][0] == "request_completed"
        ]
        assert len(completed_calls) == 1

        # Verify memory delta is tracked
        call_kwargs = completed_calls[0][1]
        assert "memory_delta_mb" in call_kwargs
        assert call_kwargs["memory_delta_mb"] == 0.48  # (1.5 - 1.0) MB

    def test_memory_tracking_disabled_by_default(self, mocker: MockerFixture) -> None:
        """Test that memory tracking is disabled by default."""
        mock_logger = mocker.Mock()
        _mock_get_logger = mocker.patch(
            "src.api.middleware.request_logging.get_logger", return_value=mock_logger
        )

        # Mock tracemalloc
        mock_tracemalloc = mocker.patch(
            "src.api.middleware.request_logging.tracemalloc"
        )

        # Create app with default config (memory tracking disabled)
        app = create_test_app()
        client = TestClient(app)
        response = client.get("/test")
        assert response.status_code == 200

        # Verify tracemalloc was not used
        mock_tracemalloc.is_tracing.assert_not_called()
        mock_tracemalloc.start.assert_not_called()
        mock_tracemalloc.get_traced_memory.assert_not_called()

        # Find the request_completed call
        completed_calls = [
            call
            for call in mock_logger.info.call_args_list
            if call[0][0] == "request_completed"
        ]
        assert len(completed_calls) == 1

        # Verify memory delta is not included
        call_kwargs = completed_calls[0][1]
        assert "memory_delta_mb" not in call_kwargs

    def test_opentelemetry_span_attributes(self, mocker: MockerFixture) -> None:
        """Test that OpenTelemetry span attributes are added."""
        mock_logger = mocker.Mock()
        _mock_get_logger = mocker.patch(
            "src.api.middleware.request_logging.get_logger", return_value=mock_logger
        )

        # Mock OpenTelemetry span
        mock_span = MagicMock()
        mock_span.is_recording.return_value = True
        mocker.patch(
            "src.api.middleware.request_logging.trace.get_current_span",
            return_value=mock_span,
        )

        # Create app with body logging for size tracking
        app = create_test_app(
            log_config=LogConfig(log_request_body=True, log_response_body=True)
        )
        client = TestClient(app)
        response = client.post(
            "/echo", json={"username": "testuser", "password": "secret"}
        )
        assert response.status_code == 200

        # Verify span attributes were set
        mock_span.set_attribute.assert_any_call("http.request.duration_ms", mocker.ANY)
        mock_span.set_attribute.assert_any_call("http.request.size_bytes", mocker.ANY)
        mock_span.set_attribute.assert_any_call("http.response.size_bytes", mocker.ANY)
        mock_span.set_attribute.assert_any_call("process.active_tasks", mocker.ANY)

        # Verify attribute values
        attribute_calls = {
            call[0][0]: call[0][1] for call in mock_span.set_attribute.call_args_list
        }
        assert attribute_calls["http.request.duration_ms"] >= 0
        assert attribute_calls["http.request.size_bytes"] > 0
        assert attribute_calls["http.response.size_bytes"] > 0
        assert attribute_calls["process.active_tasks"] >= 0

    def test_opentelemetry_span_attributes_with_memory(
        self, mocker: MockerFixture
    ) -> None:
        """Test that memory span attribute is added when memory tracking is enabled."""
        mock_logger = mocker.Mock()
        _mock_get_logger = mocker.patch(
            "src.api.middleware.request_logging.get_logger", return_value=mock_logger
        )

        # Mock OpenTelemetry span
        mock_span = MagicMock()
        mock_span.is_recording.return_value = True
        mocker.patch(
            "src.api.middleware.request_logging.trace.get_current_span",
            return_value=mock_span,
        )

        # Mock tracemalloc
        mock_tracemalloc = mocker.patch(
            "src.api.middleware.request_logging.tracemalloc"
        )
        mock_tracemalloc.is_tracing.return_value = False
        mock_tracemalloc.get_traced_memory.side_effect = [
            (1000000, 2000000),  # Start: 1MB current
            (1500000, 2000000),  # End: 1.5MB current
        ]

        # Create app with memory tracking enabled
        app = create_test_app(log_config=LogConfig(enable_memory_tracking=True))
        client = TestClient(app)
        response = client.get("/test")
        assert response.status_code == 200

        # Verify memory delta span attribute was set
        mock_span.set_attribute.assert_any_call("process.memory_delta_mb", 0.48)

    def test_span_events_for_slow_requests(self, mocker: MockerFixture) -> None:
        """Test that span events are added for slow requests."""
        mock_logger = mocker.Mock()
        _mock_get_logger = mocker.patch(
            "src.api.middleware.request_logging.get_logger", return_value=mock_logger
        )

        # Mock OpenTelemetry span
        mock_span = MagicMock()
        mock_span.is_recording.return_value = True
        mocker.patch(
            "src.api.middleware.request_logging.trace.get_current_span",
            return_value=mock_span,
        )

        # Create app with low thresholds
        app = create_test_app(
            log_config=LogConfig(
                slow_request_threshold_ms=1, critical_request_threshold_ms=20
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

        # Verify span event was added for slow request (not critical)
        mock_span.add_event.assert_called_once()
        event_call = mock_span.add_event.call_args
        assert event_call[0][0] == "slow_request_threshold_exceeded"
        assert "threshold_ms" in event_call[1]["attributes"]
        assert "duration_ms" in event_call[1]["attributes"]
        assert event_call[1]["attributes"]["threshold_ms"] == 1

    def test_span_events_for_critical_requests(self, mocker: MockerFixture) -> None:
        """Test that span events are added for critically slow requests."""
        mock_logger = mocker.Mock()
        _mock_get_logger = mocker.patch(
            "src.api.middleware.request_logging.get_logger", return_value=mock_logger
        )

        # Mock OpenTelemetry span
        mock_span = MagicMock()
        mock_span.is_recording.return_value = True
        mocker.patch(
            "src.api.middleware.request_logging.trace.get_current_span",
            return_value=mock_span,
        )

        # Create app with low thresholds
        app = create_test_app(
            log_config=LogConfig(
                slow_request_threshold_ms=1, critical_request_threshold_ms=5
            )
        )

        # Add critically slow endpoint
        @app.get("/critical")
        async def critical_endpoint() -> Response:
            await asyncio.sleep(0.01)  # 10ms delay
            return Response(content="critical")

        client = TestClient(app)
        response = client.get("/critical")
        assert response.status_code == 200

        # Verify span event was added for critical slowness
        mock_span.add_event.assert_called_once()
        event_call = mock_span.add_event.call_args
        assert event_call[0][0] == "critical_slowness_threshold_exceeded"
        assert "threshold_ms" in event_call[1]["attributes"]
        assert "duration_ms" in event_call[1]["attributes"]
        assert event_call[1]["attributes"]["threshold_ms"] == 5

    def test_no_span_operations_when_not_recording(self, mocker: MockerFixture) -> None:
        """Test that span operations are skipped when span is not recording."""
        mock_logger = mocker.Mock()
        _mock_get_logger = mocker.patch(
            "src.api.middleware.request_logging.get_logger", return_value=mock_logger
        )

        # Mock non-recording span
        mock_span = MagicMock()
        mock_span.is_recording.return_value = False
        mocker.patch(
            "src.api.middleware.request_logging.trace.get_current_span",
            return_value=mock_span,
        )

        # Create app
        app = create_test_app()
        client = TestClient(app)
        response = client.get("/test")
        assert response.status_code == 200

        # Verify no span operations were performed
        mock_span.set_attribute.assert_not_called()
        mock_span.add_event.assert_not_called()

    def test_error_handling_with_performance_metrics(
        self, mocker: MockerFixture
    ) -> None:
        """Test that performance metrics are still tracked when errors occur."""
        mock_logger = mocker.Mock()
        _mock_get_logger = mocker.patch(
            "src.api.middleware.request_logging.get_logger", return_value=mock_logger
        )

        # Create app
        app = create_test_app()
        client = TestClient(app)

        # This endpoint raises an unhandled ValueError
        with pytest.raises(ValueError, match="This is an unhandled error"):
            client.get("/unhandled-error")

        # Should log request_failed with duration
        exception_calls = mock_logger.exception.call_args_list
        assert len(exception_calls) == 1

        # Verify error logging includes duration
        call_kwargs = exception_calls[0][1]
        assert "duration_ms" in call_kwargs
        assert isinstance(call_kwargs["duration_ms"], float)
        assert call_kwargs["duration_ms"] >= 0
        assert call_kwargs["error_type"] == "ValueError"
