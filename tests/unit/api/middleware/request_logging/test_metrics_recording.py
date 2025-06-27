"""Tests for OpenTelemetry metrics recording in RequestLoggingMiddleware."""

import pytest
from fastapi import Response
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture, MockType

from src.core.config import LogConfig

from .conftest import create_test_app


@pytest.mark.unit
class TestMetricsRecording:
    """Test cases for OpenTelemetry metrics recording in RequestLoggingMiddleware."""

    @pytest.fixture
    def mock_metrics(self, mocker: MockerFixture) -> dict[str, MockType]:
        """Mock all metric instruments."""
        mock_request_counter = mocker.Mock()
        mock_request_duration = mocker.Mock()
        mock_db_counter = mocker.Mock()
        mock_db_duration = mocker.Mock()

        mocker.patch(
            "src.api.middleware.request_logging.request_counter",
            mock_request_counter,
        )
        mocker.patch(
            "src.api.middleware.request_logging.request_duration_histogram",
            mock_request_duration,
        )
        mocker.patch(
            "src.api.middleware.request_logging.db_query_counter",
            mock_db_counter,
        )
        mocker.patch(
            "src.api.middleware.request_logging.db_query_duration_histogram",
            mock_db_duration,
        )

        return {
            "request_counter": mock_request_counter,
            "request_duration": mock_request_duration,
            "db_counter": mock_db_counter,
            "db_duration": mock_db_duration,
        }

    def test_records_request_metrics(
        self,
        mock_metrics: dict[str, MockType],
        mocker: MockerFixture,
    ) -> None:
        """Test that request metrics are recorded correctly."""
        # Mock logger
        mocker.patch("src.api.middleware.request_logging.get_logger")

        # Create app
        app = create_test_app()
        client = TestClient(app)
        response = client.get("/test")
        assert response.status_code == 200

        # Verify request counter was incremented
        mock_metrics["request_counter"].add.assert_called_once()
        counter_call = mock_metrics["request_counter"].add.call_args
        assert counter_call[0][0] == 1  # Count
        assert counter_call[0][1]["http.method"] == "GET"
        assert counter_call[0][1]["http.route"] == "/test"
        assert counter_call[0][1]["http.status_code"] == "200"

        # Verify request duration was recorded
        mock_metrics["request_duration"].record.assert_called_once()
        duration_call = mock_metrics["request_duration"].record.call_args
        assert duration_call[0][0] >= 0  # Duration in ms
        assert duration_call[0][1]["http.method"] == "GET"
        assert duration_call[0][1]["http.route"] == "/test"
        assert duration_call[0][1]["http.status_code"] == "200"

    def test_records_post_request_metrics(
        self,
        mock_metrics: dict[str, MockType],
        mocker: MockerFixture,
    ) -> None:
        """Test metrics recording for POST requests."""
        # Mock logger
        mocker.patch("src.api.middleware.request_logging.get_logger")

        # Create app
        app = create_test_app()
        client = TestClient(app)
        response = client.post(
            "/echo",
            json={
                "username": "testuser",
                "password": "testpass",
                "email": "test@example.com",
            },
        )
        assert response.status_code == 200

        # Verify metrics for POST request
        counter_attrs = mock_metrics["request_counter"].add.call_args[0][1]
        assert counter_attrs["http.method"] == "POST"
        assert counter_attrs["http.route"] == "/echo"
        assert counter_attrs["http.status_code"] == "200"

        duration_attrs = mock_metrics["request_duration"].record.call_args[0][1]
        assert duration_attrs["http.method"] == "POST"
        assert duration_attrs["http.route"] == "/echo"
        assert duration_attrs["http.status_code"] == "200"

    def test_records_error_response_metrics(
        self,
        mock_metrics: dict[str, MockType],
        mocker: MockerFixture,
    ) -> None:
        """Test metrics recording for error responses."""
        # Mock logger
        mocker.patch("src.api.middleware.request_logging.get_logger")

        # Create app
        app = create_test_app()

        # Add endpoint that returns error
        @app.get("/error")
        async def error_endpoint() -> Response:
            return Response(content="error", status_code=500)

        client = TestClient(app)
        response = client.get("/error")
        assert response.status_code == 500

        # Verify metrics include error status
        counter_attrs = mock_metrics["request_counter"].add.call_args[0][1]
        assert counter_attrs["http.status_code"] == "500"

        duration_attrs = mock_metrics["request_duration"].record.call_args[0][1]
        assert duration_attrs["http.status_code"] == "500"

    def test_no_metrics_when_instruments_none(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Test that middleware works when metric instruments are None."""
        # Mock logger
        mocker.patch("src.api.middleware.request_logging.get_logger")

        # Set all metrics to None
        mocker.patch("src.api.middleware.request_logging.request_counter", None)
        mocker.patch(
            "src.api.middleware.request_logging.request_duration_histogram", None
        )
        mocker.patch("src.api.middleware.request_logging.db_query_counter", None)
        mocker.patch(
            "src.api.middleware.request_logging.db_query_duration_histogram", None
        )

        # Create app - should not raise
        app = create_test_app()
        client = TestClient(app)
        response = client.get("/test")
        assert response.status_code == 200

    def test_records_database_metrics(
        self,
        mock_metrics: dict[str, MockType],
        mocker: MockerFixture,
    ) -> None:
        """Test that database query metrics are recorded."""
        # Mock logger
        mocker.patch("src.api.middleware.request_logging.get_logger")

        # Mock get_logger_context to return database metrics
        mock_get_logger_context = mocker.patch(
            "src.api.middleware.request_logging.get_logger_context"
        )
        mock_get_logger_context.return_value = {
            "db_query_count": 3,
            "db_query_duration_ms": 45.0,
        }

        # Mock clear_logger_context
        mocker.patch("src.api.middleware.request_logging.clear_logger_context")

        # Create app
        app = create_test_app()
        client = TestClient(app)
        response = client.get("/test")
        assert response.status_code == 200

        # Verify database query counter
        mock_metrics["db_counter"].add.assert_called_once()
        db_counter_call = mock_metrics["db_counter"].add.call_args
        assert db_counter_call[0][0] == 3  # Total queries
        assert db_counter_call[0][1]["http.method"] == "GET"
        assert db_counter_call[0][1]["http.route"] == "/test"

        # Verify database duration histogram (3 calls for 3 queries)
        assert mock_metrics["db_duration"].record.call_count == 3
        # Each call should record average duration
        for call in mock_metrics["db_duration"].record.call_args_list:
            assert call[0][0] == 15.0  # Average: 45.0 / 3
            assert call[0][1]["http.method"] == "GET"
            assert call[0][1]["http.route"] == "/test"

    def test_no_database_metrics_when_no_queries(
        self,
        mock_metrics: dict[str, MockType],
        mocker: MockerFixture,
    ) -> None:
        """Test that database metrics are not recorded when no queries occur."""
        # Mock logger
        mocker.patch("src.api.middleware.request_logging.get_logger")

        # Mock get_logger_context to return empty dict (no db queries)
        mocker.patch(
            "src.api.middleware.request_logging.get_logger_context", return_value={}
        )
        mocker.patch("src.api.middleware.request_logging.clear_logger_context")

        # Create app
        app = create_test_app()
        client = TestClient(app)
        response = client.get("/test")
        assert response.status_code == 200

        # Verify request metrics were recorded
        assert mock_metrics["request_counter"].add.called
        assert mock_metrics["request_duration"].record.called

        # Verify database metrics were NOT recorded
        mock_metrics["db_counter"].add.assert_not_called()
        mock_metrics["db_duration"].record.assert_not_called()

    def test_metrics_with_multiple_requests(
        self,
        mock_metrics: dict[str, MockType],
        mocker: MockerFixture,
    ) -> None:
        """Test metrics recording across multiple requests."""
        # Mock logger
        mocker.patch("src.api.middleware.request_logging.get_logger")

        # Create app
        app = create_test_app()
        client = TestClient(app)

        # Make multiple requests
        response1 = client.get("/test")
        assert response1.status_code == 200

        response2 = client.post(
            "/echo",
            json={
                "username": "user2",
                "password": "pass2",
                "email": "user2@example.com",
            },
        )
        assert response2.status_code == 200

        response3 = client.get("/test")
        assert response3.status_code == 200

        # Verify counters were called 3 times
        assert mock_metrics["request_counter"].add.call_count == 3
        assert mock_metrics["request_duration"].record.call_count == 3

        # Verify different attributes for different requests
        counter_calls = mock_metrics["request_counter"].add.call_args_list
        assert counter_calls[0][0][1]["http.method"] == "GET"
        assert counter_calls[1][0][1]["http.method"] == "POST"
        assert counter_calls[2][0][1]["http.method"] == "GET"

    def test_metrics_recording_with_performance_thresholds(
        self,
        mock_metrics: dict[str, MockType],
        mocker: MockerFixture,
    ) -> None:
        """Test that metrics are recorded even with performance threshold logging."""
        # Mock logger
        mocker.patch("src.api.middleware.request_logging.get_logger")

        # Create app with low thresholds to trigger warnings
        app = create_test_app(
            log_config=LogConfig(
                slow_request_threshold_ms=1,
                critical_request_threshold_ms=5,
            )
        )

        client = TestClient(app)
        response = client.get("/test")
        assert response.status_code == 200

        # Verify metrics were still recorded
        assert mock_metrics["request_counter"].add.called
        assert mock_metrics["request_duration"].record.called

        # Duration should be recorded regardless of thresholds
        duration_call = mock_metrics["request_duration"].record.call_args
        assert duration_call[0][0] >= 0  # Some positive duration
