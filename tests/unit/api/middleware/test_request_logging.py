"""Unit tests for RequestLoggingMiddleware."""

from typing import Any
from unittest.mock import Mock, patch

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from src.api.middleware.request_context import RequestContextMiddleware
from src.api.middleware.request_logging import RequestLoggingMiddleware
from src.core.context import CORRELATION_ID_HEADER


def create_test_app(add_logging_middleware: bool = True) -> FastAPI:
    """Create a test FastAPI app."""
    test_app = FastAPI()
    # Note: Middleware is executed in reverse order in FastAPI/Starlette
    # So we add RequestLoggingMiddleware first, then RequestContextMiddleware
    if add_logging_middleware:
        test_app.add_middleware(RequestLoggingMiddleware)
    test_app.add_middleware(RequestContextMiddleware)

    @test_app.get("/test")
    async def test_endpoint() -> dict[str, str]:
        """Test endpoint that returns success."""
        return {"status": "ok"}

    @test_app.get("/test-with-params")
    async def test_params_endpoint(name: str, age: int) -> dict[str, Any]:
        """Test endpoint with query parameters."""
        return {"name": name, "age": age}

    @test_app.get("/error")
    async def error_endpoint() -> None:
        """Test endpoint that raises an error."""
        raise HTTPException(status_code=500, detail="Test error")

    @test_app.post("/auth/login")
    async def login_endpoint() -> dict[str, str]:
        """Sensitive endpoint for testing sanitization."""
        return {"token": "secret-token"}

    @test_app.get("/api/v1/auth/token")
    async def token_endpoint() -> dict[str, str]:
        """Another sensitive endpoint."""
        return {"token": "another-secret"}

    @test_app.get("/unhandled-error")
    async def unhandled_error_endpoint() -> None:
        """Test endpoint that raises an unhandled exception."""
        raise ValueError("This is an unhandled error")

    return test_app


@pytest.fixture
def app() -> FastAPI:
    """Create a test FastAPI app with RequestLoggingMiddleware."""
    return create_test_app()


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Create a test client for the app."""
    return TestClient(app)


class TestRequestLoggingMiddleware:
    """Test cases for RequestLoggingMiddleware."""

    @patch("src.api.middleware.request_logging.get_logger")
    def test_logs_request_started(self, mock_get_logger: Mock) -> None:
        """Test that middleware logs request start."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        # Create app and client after patching
        app = create_test_app()
        client = TestClient(app)

        response = client.get("/test")

        # Verify request was logged - check if any call has the expected arguments
        request_started_calls = [
            call
            for call in mock_logger.info.call_args_list
            if call[0] and call[0][0] == "request_started"
        ]
        assert len(request_started_calls) > 0, "No request_started calls found"

        # Check the kwargs of the call
        call_kwargs = request_started_calls[0][1]
        assert call_kwargs["method"] == "GET"
        assert call_kwargs["path"] == "/test"
        # Correlation ID should match what's in response header
        assert call_kwargs["correlation_id"] == response.headers.get(
            CORRELATION_ID_HEADER
        )

    @patch("src.api.middleware.request_logging.get_logger")
    def test_logs_request_completed(self, mock_get_logger: Mock) -> None:
        """Test that middleware logs request completion."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        # Create app and client after patching
        app = create_test_app()
        client = TestClient(app)

        response = client.get("/test")

        # Find the request_completed call
        completed_calls = [
            call
            for call in mock_logger.info.call_args_list
            if call[0][0] == "request_completed"
        ]
        assert len(completed_calls) == 1

        # Verify the call arguments
        call_args = completed_calls[0][1]
        assert call_args["method"] == "GET"
        assert call_args["path"] == "/test"
        assert call_args["status_code"] == 200
        assert "duration_ms" in call_args
        assert isinstance(call_args["duration_ms"], float)
        assert call_args["duration_ms"] >= 0
        assert call_args["correlation_id"] == response.headers.get(
            CORRELATION_ID_HEADER
        )

    @patch("src.api.middleware.request_logging.get_logger")
    def test_logs_query_parameters(self, mock_get_logger: Mock) -> None:
        """Test that middleware logs query parameters."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        # Create app and client after patching
        app = create_test_app()
        client = TestClient(app)

        client.get("/test-with-params?name=John&age=30")

        # Find the request_started call
        started_calls = [
            call
            for call in mock_logger.info.call_args_list
            if call[0][0] == "request_started"
        ]
        assert len(started_calls) == 1

        # Verify query params were logged
        call_kwargs = started_calls[0][1]
        assert "query_params" in call_kwargs
        assert call_kwargs["query_params"] == {"name": "John", "age": "30"}

    @patch("src.api.middleware.request_logging.get_logger")
    def test_sanitizes_sensitive_query_params(self, mock_get_logger: Mock) -> None:
        """Test that middleware sanitizes sensitive query parameters."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        # Create app and client after patching
        app = create_test_app()
        client = TestClient(app)

        # Make request with sensitive query params
        client.get("/api/v1/auth/token?api_key=secret123&refresh_token=abc&user=john")

        # Find the request_started call
        started_calls = [
            call
            for call in mock_logger.info.call_args_list
            if call[0][0] == "request_started"
        ]
        assert len(started_calls) == 1

        # Verify sensitive query params were sanitized
        call_kwargs = started_calls[0][1]
        assert "query_params" in call_kwargs
        assert call_kwargs["query_params"]["api_key"] == "[REDACTED]"
        assert call_kwargs["query_params"]["refresh_token"] == "[REDACTED]"
        assert call_kwargs["query_params"]["user"] == "john"  # Non-sensitive

    @patch("src.api.middleware.request_logging.get_logger")
    def test_logs_all_paths_including_sensitive(self, mock_get_logger: Mock) -> None:
        """Test that middleware logs all paths including auth endpoints."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        # Create app and client after patching
        app = create_test_app()
        client = TestClient(app)

        # Test sensitive endpoint
        client.post("/auth/login", json={"username": "user", "password": "pass"})

        # Find the request_started call
        started_calls = [
            call
            for call in mock_logger.info.call_args_list
            if call[0][0] == "request_started"
        ]
        assert len(started_calls) == 1

        # Verify the path was logged
        call_kwargs = started_calls[0][1]
        assert call_kwargs["method"] == "POST"
        assert call_kwargs["path"] == "/auth/login"
        # Should still have correlation ID
        assert "correlation_id" in call_kwargs

    @patch("src.api.middleware.request_logging.get_logger")
    def test_sanitizes_password_in_query(self, mock_get_logger: Mock) -> None:
        """Test that password in query params is sanitized."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        # Create app and client after patching
        app = create_test_app()
        client = TestClient(app)

        client.get("/test?username=john&password=secret123")

        # Find the request_started call
        started_calls = [
            call
            for call in mock_logger.info.call_args_list
            if call[0][0] == "request_started"
        ]
        assert len(started_calls) == 1

        # Verify password was sanitized
        call_kwargs = started_calls[0][1]
        assert "query_params" in call_kwargs
        assert call_kwargs["query_params"]["username"] == "john"
        assert call_kwargs["query_params"]["password"] == "[REDACTED]"

    @patch("src.api.middleware.request_logging.get_logger")
    def test_logs_errors(self, mock_get_logger: Mock) -> None:
        """Test that middleware logs errors."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        # Create app and client after patching
        app = create_test_app()
        client = TestClient(app)

        # This should raise an HTTP 500 error
        response = client.get("/error")
        assert response.status_code == 500

        # Should still log request_started
        request_started_calls = [
            call
            for call in mock_logger.info.call_args_list
            if call[0] and call[0][0] == "request_started"
        ]
        assert len(request_started_calls) == 1
        call_kwargs = request_started_calls[0][1]
        assert call_kwargs["method"] == "GET"
        assert call_kwargs["path"] == "/error"
        assert call_kwargs["correlation_id"] == response.headers.get(
            CORRELATION_ID_HEADER
        )

        # Should log request_completed (HTTPException is handled by FastAPI)
        completed_calls = [
            call
            for call in mock_logger.info.call_args_list
            if call[0][0] == "request_completed"
        ]
        assert len(completed_calls) == 1
        assert completed_calls[0][1]["status_code"] == 500

    @patch("src.api.middleware.request_logging.get_logger")
    def test_duration_calculation(self, mock_get_logger: Mock) -> None:
        """Test that duration is calculated correctly."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        # Create app and client after patching
        app = create_test_app()
        client = TestClient(app)

        client.get("/test")

        # Find the request_completed call
        completed_calls = [
            call
            for call in mock_logger.info.call_args_list
            if call[0][0] == "request_completed"
        ]
        assert len(completed_calls) == 1

        # Check duration
        duration_ms = completed_calls[0][1]["duration_ms"]
        assert isinstance(duration_ms, float)
        assert duration_ms >= 0
        assert duration_ms < 1000  # Should be less than 1 second for a simple request

    def test_correlation_id_present_in_logs(self, client: TestClient) -> None:
        """Test that correlation ID is included in logs."""
        # Make request with specific correlation ID
        correlation_id = "test-correlation-12345"
        response = client.get("/test", headers={CORRELATION_ID_HEADER: correlation_id})

        # Verify the correlation ID was returned
        assert response.headers[CORRELATION_ID_HEADER] == correlation_id

    def test_middleware_does_not_interfere_with_response(
        self, client: TestClient
    ) -> None:
        """Test that middleware doesn't modify the response."""
        response = client.get("/test")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_multiple_requests_logged_separately(self, client: TestClient) -> None:
        """Test that multiple requests are logged separately."""
        # Make multiple requests
        response1 = client.get("/test")
        response2 = client.get("/test-with-params?name=Alice&age=25")

        # Each should have different correlation IDs
        assert (
            response1.headers[CORRELATION_ID_HEADER]
            != response2.headers[CORRELATION_ID_HEADER]
        )

    @patch("src.api.middleware.request_logging.get_logger")
    def test_logs_unhandled_exceptions(self, mock_get_logger: Mock) -> None:
        """Test that middleware logs unhandled exceptions."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        # Create app and client after patching
        app = create_test_app()
        client = TestClient(app)

        # This should raise an unhandled ValueError
        with pytest.raises(ValueError, match="This is an unhandled error"):
            client.get("/unhandled-error")

        # Should log request_started
        request_started_calls = [
            call
            for call in mock_logger.info.call_args_list
            if call[0] and call[0][0] == "request_started"
        ]
        assert len(request_started_calls) == 1

        # Should log request_failed (not request_completed)
        failed_calls = [
            call
            for call in mock_logger.error.call_args_list
            if call[0][0] == "request_failed"
        ]
        assert len(failed_calls) == 1

        # Verify the error details
        call_kwargs = failed_calls[0][1]
        assert call_kwargs["method"] == "GET"
        assert call_kwargs["path"] == "/unhandled-error"
        assert "duration_ms" in call_kwargs
        assert isinstance(call_kwargs["duration_ms"], float)
        assert call_kwargs["error_type"] == "ValueError"
        assert "exc_info" in call_kwargs
        assert "correlation_id" in call_kwargs
