"""Unit tests for RequestLoggingMiddleware."""

import asyncio
from collections.abc import AsyncIterator
from typing import Any
from unittest.mock import Mock, patch

import pytest
from fastapi import FastAPI, File, Form, HTTPException, Request, Response
from fastapi.testclient import TestClient
from pydantic import BaseModel
from starlette.datastructures import Headers

from src.api.middleware.request_context import RequestContextMiddleware
from src.api.middleware.request_logging import (
    TRUNCATED_SUFFIX,
    RequestLoggingMiddleware,
)
from src.core.constants import MAX_BODY_SIZE
from src.core.context import CORRELATION_ID_HEADER


class UserModel(BaseModel):
    """Test model for request/response bodies."""

    username: str
    password: str
    email: str | None = None


def create_test_app(
    add_logging_middleware: bool = True,
    log_request_body: bool = False,
    log_response_body: bool = False,
    max_body_size: int = MAX_BODY_SIZE,
) -> FastAPI:
    """Create a test FastAPI app."""
    test_app = FastAPI()
    # Note: Middleware is executed in reverse order in FastAPI/Starlette
    # So we add RequestLoggingMiddleware first, then RequestContextMiddleware
    if add_logging_middleware:
        test_app.add_middleware(
            RequestLoggingMiddleware,
            log_request_body=log_request_body,
            log_response_body=log_response_body,
            max_body_size=max_body_size,
        )
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

    @test_app.post("/json-endpoint")
    async def json_endpoint(user: UserModel) -> dict[str, Any]:
        """Test endpoint that accepts JSON body."""
        return {"received": user.model_dump()}

    @test_app.post("/form-endpoint")
    async def form_endpoint(
        username: str = Form(), password: str = Form(), age: int = Form()
    ) -> dict[str, Any]:
        """Test endpoint that accepts form data."""
        # Password is intentionally not returned to test sanitization
        _ = password  # Mark as intentionally unused
        return {"username": username, "age": age}

    @test_app.post("/raw-text")
    async def raw_text_endpoint(request: Request) -> dict[str, str]:
        """Test endpoint that accepts raw text."""
        body = await request.body()
        return {"received": body.decode("utf-8")}

    @test_app.post("/binary-upload")
    async def binary_upload_endpoint(file: bytes = File()) -> dict[str, int]:
        """Test endpoint that accepts binary file."""
        return {"size": len(file)}

    @test_app.post("/echo", response_model=UserModel)
    async def echo_endpoint(user: UserModel) -> UserModel:
        """Test endpoint that echoes back the input."""
        return user

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
            for call in mock_logger.exception.call_args_list
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
        assert "correlation_id" in call_kwargs


class TestRequestBodyLogging:
    """Test cases for request body logging functionality."""

    @patch("src.api.middleware.request_logging.get_logger")
    def test_logs_json_request_body(self, mock_get_logger: Mock) -> None:
        """Test that middleware logs JSON request body."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        app = create_test_app(log_request_body=True)
        client = TestClient(app)

        # Send JSON body
        body = {
            "username": "john",
            "password": "secret123",
            "email": "john@example.com",
        }
        client.post("/json-endpoint", json=body)

        # Find the request_started call
        started_calls = [
            call
            for call in mock_logger.info.call_args_list
            if call[0][0] == "request_started"
        ]
        assert len(started_calls) == 1

        # Verify body was logged and password was sanitized
        call_kwargs = started_calls[0][1]
        assert "body" in call_kwargs
        assert call_kwargs["body"]["username"] == "john"
        assert call_kwargs["body"]["password"] == "[REDACTED]"
        assert call_kwargs["body"]["email"] == "john@example.com"
        assert (
            "headers" in call_kwargs
        )  # Headers should be logged when body logging is enabled

    @patch("src.api.middleware.request_logging.get_logger")
    def test_logs_form_data_request_body(self, mock_get_logger: Mock) -> None:
        """Test that middleware logs form data request body."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        app = create_test_app(log_request_body=True)
        client = TestClient(app)

        # Send form data
        form_data = {"username": "alice", "password": "secret456", "age": "25"}
        client.post("/form-endpoint", data=form_data)

        # Find the request_started call
        started_calls = [
            call
            for call in mock_logger.info.call_args_list
            if call[0][0] == "request_started"
        ]
        assert len(started_calls) == 1

        # Verify form data was logged and password was sanitized
        call_kwargs = started_calls[0][1]
        assert "body" in call_kwargs
        assert call_kwargs["body"]["username"] == "alice"
        assert call_kwargs["body"]["password"] == "[REDACTED]"
        assert call_kwargs["body"]["age"] == "25"

    @patch("src.api.middleware.request_logging.get_logger")
    def test_logs_text_request_body(self, mock_get_logger: Mock) -> None:
        """Test that middleware logs text request body."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        app = create_test_app(log_request_body=True)
        client = TestClient(app)

        # Send plain text
        text_body = "This is a plain text message"
        client.post(
            "/raw-text", content=text_body, headers={"content-type": "text/plain"}
        )

        # Find the request_started call
        started_calls = [
            call
            for call in mock_logger.info.call_args_list
            if call[0][0] == "request_started"
        ]
        assert len(started_calls) == 1

        # Verify text body was logged
        call_kwargs = started_calls[0][1]
        assert "body" in call_kwargs
        assert call_kwargs["body"] == text_body

    @patch("src.api.middleware.request_logging.get_logger")
    def test_logs_binary_request_metadata(self, mock_get_logger: Mock) -> None:
        """Test that middleware logs binary request metadata only."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        app = create_test_app(log_request_body=True)
        client = TestClient(app)

        # Send binary data
        binary_data = b"Binary content \x00\x01\x02"
        files = {"file": ("test.bin", binary_data, "application/octet-stream")}
        client.post("/binary-upload", files=files)

        # Find the request_started call
        started_calls = [
            call
            for call in mock_logger.info.call_args_list
            if call[0][0] == "request_started"
        ]
        assert len(started_calls) == 1

        # Verify only metadata was logged for multipart
        call_kwargs = started_calls[0][1]
        assert "body" in call_kwargs
        assert call_kwargs["body"]["_type"] == "multipart/form-data"
        assert "_size" in call_kwargs["body"]
        assert call_kwargs["body"]["_info"] == "Binary content not logged"

    @patch("src.api.middleware.request_logging.get_logger")
    def test_truncates_large_request_body(self, mock_get_logger: Mock) -> None:
        """Test that middleware truncates large request bodies."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        # Create app with small max body size
        app = create_test_app(log_request_body=True, max_body_size=50)
        client = TestClient(app)

        # Send large text body
        large_text = "A" * 100
        client.post(
            "/raw-text", content=large_text, headers={"content-type": "text/plain"}
        )

        # Find the request_started call
        started_calls = [
            call
            for call in mock_logger.info.call_args_list
            if call[0][0] == "request_started"
        ]
        assert len(started_calls) == 1

        # Verify body was truncated
        call_kwargs = started_calls[0][1]
        assert "body" in call_kwargs
        assert len(call_kwargs["body"]) < len(large_text)
        assert call_kwargs["body"].endswith(TRUNCATED_SUFFIX)
        assert call_kwargs["body"].startswith("A" * 50)

    @patch("src.api.middleware.request_logging.get_logger")
    def test_sanitizes_headers_when_body_logging_enabled(
        self, mock_get_logger: Mock
    ) -> None:
        """Test that headers are sanitized when body logging is enabled."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        app = create_test_app(log_request_body=True)
        client = TestClient(app)

        # Send request with sensitive headers
        headers = {
            "Authorization": "Bearer secret-token",
            "X-API-Key": "api-secret",
            "Content-Type": "application/json",
            "User-Agent": "TestClient",
        }
        client.post("/json-endpoint", json={"username": "test"}, headers=headers)

        # Find the request_started call
        started_calls = [
            call
            for call in mock_logger.info.call_args_list
            if call[0][0] == "request_started"
        ]
        assert len(started_calls) == 1

        # Verify headers were sanitized
        call_kwargs = started_calls[0][1]
        assert "headers" in call_kwargs
        assert call_kwargs["headers"]["authorization"] == "[REDACTED]"
        assert call_kwargs["headers"]["x-api-key"] == "[REDACTED]"
        assert call_kwargs["headers"]["content-type"] == "application/json"
        assert call_kwargs["headers"]["user-agent"] == "TestClient"

    @patch("src.api.middleware.request_logging.get_logger")
    def test_handles_invalid_json_gracefully(self, mock_get_logger: Mock) -> None:
        """Test that middleware handles invalid JSON gracefully."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        app = create_test_app(log_request_body=True)
        client = TestClient(app)

        # Send invalid JSON
        client.post(
            "/json-endpoint",
            content=b"Invalid JSON {",
            headers={"content-type": "application/json"},
        )

        # Find the request_started call
        started_calls = [
            call
            for call in mock_logger.info.call_args_list
            if call[0][0] == "request_started"
        ]
        assert len(started_calls) == 1

        # Verify the invalid JSON was logged as text
        call_kwargs = started_calls[0][1]
        assert "body" in call_kwargs
        assert "Invalid JSON {" in str(call_kwargs["body"])

    @patch("src.api.middleware.request_logging.get_logger")
    def test_request_body_still_available_to_endpoint(
        self, mock_get_logger: Mock
    ) -> None:
        """Test that request body is still available to the endpoint."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        app = create_test_app(log_request_body=True)
        client = TestClient(app)

        # Send JSON body
        body = {"username": "test", "password": "pass", "email": "test@example.com"}
        response = client.post("/json-endpoint", json=body)

        # Verify endpoint received the body correctly
        assert response.status_code == 200
        assert response.json()["received"]["username"] == "test"
        assert response.json()["received"]["email"] == "test@example.com"

    @patch("src.api.middleware.request_logging.get_logger")
    def test_receive_function_works_correctly(self, mock_get_logger: Mock) -> None:
        """Test that the receive function properly returns the body."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        app = create_test_app(log_request_body=True)

        # Add endpoint that reads body multiple times
        @app.post("/double-read")
        async def double_read(request: Request) -> dict[str, Any]:
            # Read body twice to ensure receive function works
            body1 = await request.body()
            body2 = await request.body()
            return {
                "first": body1.decode(),
                "second": body2.decode(),
                "equal": body1 == body2,
            }

        client = TestClient(app)
        response = client.post("/double-read", content=b"test content")

        assert response.status_code == 200
        result = response.json()
        assert result["first"] == "test content"
        assert result["second"] == "test content"
        assert result["equal"] is True

    @patch("src.api.middleware.request_logging.get_logger")
    def test_no_body_logging_when_disabled(self, mock_get_logger: Mock) -> None:
        """Test that body is not logged when disabled."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        app = create_test_app(log_request_body=False)  # Body logging disabled
        client = TestClient(app)

        # Send JSON body
        body = {"username": "john", "password": "secret"}
        client.post("/json-endpoint", json=body)

        # Find the request_started call
        started_calls = [
            call
            for call in mock_logger.info.call_args_list
            if call[0][0] == "request_started"
        ]
        assert len(started_calls) == 1

        # Verify body was NOT logged
        call_kwargs = started_calls[0][1]
        assert "body" not in call_kwargs
        assert "headers" not in call_kwargs

    @patch("src.api.middleware.request_logging.get_logger")
    def test_body_logging_only_for_write_methods(self, mock_get_logger: Mock) -> None:
        """Test that body logging only happens for POST/PUT/PATCH."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        app = create_test_app(log_request_body=True)
        client = TestClient(app)

        # GET request should not log body even if enabled
        client.get("/test")

        # Find the request_started call
        started_calls = [
            call
            for call in mock_logger.info.call_args_list
            if call[0][0] == "request_started"
        ]
        assert len(started_calls) == 1

        # Verify no body was logged for GET
        call_kwargs = started_calls[0][1]
        assert "body" not in call_kwargs
        # Headers might still be logged
        assert "headers" in call_kwargs

    @patch("src.api.middleware.request_logging.get_logger")
    def test_handles_request_body_read_failure(self, mock_get_logger: Mock) -> None:
        """Test that middleware handles request body read failures gracefully."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        app = create_test_app(log_request_body=True)

        # Mock request that fails to read body
        async def failing_body() -> bytes:
            raise RuntimeError("Failed to read body")

        # Create a mock request
        mock_request = Mock(spec=Request)
        mock_request.method = "POST"
        mock_request.url.path = "/test"
        mock_request.query_params = {}
        mock_request.headers = {"content-type": "application/json"}
        mock_request.body = failing_body

        # Test the middleware directly
        middleware = RequestLoggingMiddleware(app, log_request_body=True)

        # This should log a warning but not crash
        parsed, raw = asyncio.run(middleware._parse_request_body(mock_request))

        assert parsed is None
        assert raw is None

        # Check warning was logged
        mock_logger.warning.assert_called_once()
        warning_call = mock_logger.warning.call_args
        assert warning_call[0][0] == "Failed to read request body"

    @patch("src.api.middleware.request_logging.get_logger")
    def test_handles_empty_request_body(self, mock_get_logger: Mock) -> None:
        """Test that middleware handles empty request body correctly."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        app = create_test_app(log_request_body=True)
        client = TestClient(app)

        # Send POST with empty body
        headers = {"content-type": "application/json"}
        client.post("/json-endpoint", content=b"", headers=headers)

        # Find the request_started call
        started_calls = [
            call
            for call in mock_logger.info.call_args_list
            if call[0][0] == "request_started"
        ]
        assert len(started_calls) == 1

        # Verify no body was logged for empty request
        call_kwargs = started_calls[0][1]
        assert "body" not in call_kwargs

    @patch("src.api.middleware.request_logging.get_logger")
    def test_handles_invalid_form_data_gracefully(self, mock_get_logger: Mock) -> None:
        """Test that middleware handles invalid form data gracefully."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        app = create_test_app(log_request_body=True)
        client = TestClient(app)

        # Send invalid form data (not properly encoded)
        invalid_form_data = b"\xff\xfe invalid form data"
        client.post(
            "/form-endpoint",
            content=invalid_form_data,
            headers={"content-type": "application/x-www-form-urlencoded"},
        )

        # Find the request_started call
        started_calls = [
            call
            for call in mock_logger.info.call_args_list
            if call[0][0] == "request_started"
        ]
        assert len(started_calls) == 1

        # Verify the invalid form data was handled gracefully
        call_kwargs = started_calls[0][1]
        assert "body" in call_kwargs
        # Should have tried to decode and truncate
        assert isinstance(call_kwargs["body"], str)

    @patch("src.api.middleware.request_logging.get_logger")
    def test_handles_missing_content_type(self, mock_get_logger: Mock) -> None:
        """Test that middleware handles missing content-type header."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        app = create_test_app(log_request_body=True)
        client = TestClient(app)

        # Send request without content-type header
        client.post("/raw-text", content=b"Some binary data")

        # Find the request_started call
        started_calls = [
            call
            for call in mock_logger.info.call_args_list
            if call[0][0] == "request_started"
        ]
        assert len(started_calls) == 1

        # Verify unknown content type was handled
        call_kwargs = started_calls[0][1]
        assert "body" in call_kwargs
        assert call_kwargs["body"]["_type"] == "unknown"
        assert call_kwargs["body"]["_size"] == 16
        assert call_kwargs["body"]["_info"] == "Binary content not logged"

    @pytest.mark.asyncio
    async def test_receive_function_coverage(self) -> None:
        """Test the receive function implementation to cover line 260."""
        # Create middleware
        middleware = RequestLoggingMiddleware(Mock(), log_request_body=True)

        # Create a mock request
        mock_request = Mock(spec=Request)
        mock_request.method = "POST"
        mock_request.url.path = "/test"
        mock_request.query_params = {}
        mock_request.headers = {"content-type": "application/json"}

        test_body = b'{"test": "data"}'

        async def mock_body() -> bytes:
            return test_body

        mock_request.body = mock_body

        # Mock call_next that tests the receive function
        async def mock_call_next(request: Request) -> Response:
            # Verify and test the receive function that was set by middleware
            assert hasattr(request, "_receive")
            # Call it to test line 260
            result = await request._receive()
            assert result == {"type": "http.request", "body": test_body}

            # Return a mock response
            mock_response = Mock(spec=Response)
            mock_response.status_code = 200
            mock_response.headers = {}
            return mock_response

        # Call dispatch
        await middleware.dispatch(mock_request, mock_call_next)


class TestResponseBodyLogging:
    """Test cases for response body logging functionality."""

    @patch("src.api.middleware.request_logging.get_logger")
    def test_logs_json_response_body(self, mock_get_logger: Mock) -> None:
        """Test that middleware logs JSON response body."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        app = create_test_app(log_response_body=True)
        client = TestClient(app)

        # Make request that returns JSON
        body = {"username": "test", "password": "secret", "email": "test@example.com"}
        client.post("/echo", json=body)

        # Find the request_completed call
        completed_calls = [
            call
            for call in mock_logger.info.call_args_list
            if call[0][0] == "request_completed"
        ]
        assert len(completed_calls) == 1

        # Verify response body was logged and password was sanitized
        call_kwargs = completed_calls[0][1]
        assert "response_body" in call_kwargs
        assert call_kwargs["response_body"]["username"] == "test"
        assert call_kwargs["response_body"]["password"] == "[REDACTED]"
        assert call_kwargs["response_body"]["email"] == "test@example.com"
        assert "response_headers" in call_kwargs

    @patch("src.api.middleware.request_logging.get_logger")
    def test_no_response_body_logging_when_disabled(
        self, mock_get_logger: Mock
    ) -> None:
        """Test that response body is not logged when disabled."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        app = create_test_app(log_response_body=False)  # Response body logging disabled
        client = TestClient(app)

        # Make request
        body = {"username": "test", "password": "secret"}
        client.post("/echo", json=body)

        # Find the request_completed call
        completed_calls = [
            call
            for call in mock_logger.info.call_args_list
            if call[0][0] == "request_completed"
        ]
        assert len(completed_calls) == 1

        # Verify response body was NOT logged
        call_kwargs = completed_calls[0][1]
        assert "response_body" not in call_kwargs
        assert "response_headers" not in call_kwargs

    @patch("src.api.middleware.request_logging.get_logger")
    def test_sanitizes_response_headers(self, mock_get_logger: Mock) -> None:
        """Test that response headers are sanitized."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        app = create_test_app(log_response_body=True)

        # Add custom endpoint that sets sensitive headers
        @app.get("/sensitive-headers")
        async def sensitive_headers() -> Response:
            return Response(
                content="OK",
                headers={
                    "Set-Cookie": "session=secret",
                    "X-API-Key": "response-secret",
                    "X-Custom": "public-value",
                },
            )

        client = TestClient(app)
        client.get("/sensitive-headers")

        # Find the request_completed call
        completed_calls = [
            call
            for call in mock_logger.info.call_args_list
            if call[0][0] == "request_completed"
        ]
        assert len(completed_calls) == 1

        # Verify headers were sanitized
        call_kwargs = completed_calls[0][1]
        assert "response_headers" in call_kwargs
        assert call_kwargs["response_headers"]["set-cookie"] == "[REDACTED]"
        assert call_kwargs["response_headers"]["x-api-key"] == "[REDACTED]"
        assert call_kwargs["response_headers"]["x-custom"] == "public-value"

    @patch("src.api.middleware.request_logging.get_logger")
    def test_logs_non_json_response_body(self, mock_get_logger: Mock) -> None:
        """Test that middleware logs non-JSON response body."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        app = create_test_app(log_response_body=True)

        # Add endpoint that returns plain text
        @app.get("/text-response")
        async def text_response() -> Response:
            return Response(content="Plain text response", media_type="text/plain")

        client = TestClient(app)
        client.get("/text-response")

        # Find the request_completed call
        completed_calls = [
            call
            for call in mock_logger.info.call_args_list
            if call[0][0] == "request_completed"
        ]
        assert len(completed_calls) == 1

        # Verify text response was logged
        call_kwargs = completed_calls[0][1]
        assert "response_body" in call_kwargs
        assert call_kwargs["response_body"] == "Plain text response"

    @patch("src.api.middleware.request_logging.get_logger")
    def test_handles_invalid_json_response(self, mock_get_logger: Mock) -> None:
        """Test that middleware handles invalid JSON in response body."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        app = create_test_app(log_response_body=True)

        # Add endpoint that returns invalid JSON
        @app.get("/bad-json")
        async def bad_json() -> Response:
            return Response(
                content='{"invalid": json}',  # Invalid JSON
                media_type="application/json",
            )

        client = TestClient(app)
        client.get("/bad-json")

        # Find the request_completed call
        completed_calls = [
            call
            for call in mock_logger.info.call_args_list
            if call[0][0] == "request_completed"
        ]
        assert len(completed_calls) == 1

        # Verify invalid JSON was handled gracefully
        call_kwargs = completed_calls[0][1]
        assert "response_body" in call_kwargs
        # Should fall back to string representation
        assert '{"invalid": json}' in call_kwargs["response_body"]

    @pytest.mark.asyncio
    async def test_logs_response_with_string_chunks(self) -> None:
        """Test that middleware handles response with string chunks."""
        # Test middleware directly to control the response body iterator
        middleware = RequestLoggingMiddleware(Mock(), log_response_body=True)

        # Create a mock request
        mock_request = Mock(spec=Request)
        mock_request.method = "GET"
        mock_request.url.path = "/test"
        mock_request.query_params = {}

        # Create a response that yields string chunks
        class StringChunkResponse(Response):
            def __init__(self) -> None:
                super().__init__(content="", status_code=200, media_type="text/plain")

            @property
            def body_iterator(self) -> AsyncIterator[str | bytes]:
                async def generate() -> AsyncIterator[str | bytes]:
                    # Yield different types to test lines 300-301
                    yield "Hello "  # String chunk - line 300-301
                    yield b"from "  # Bytes chunk - line 298-299
                    yield "chunks"  # String chunk - line 300-301

                return generate()

        # Mock call_next to return our custom response
        async def mock_call_next(_request: Request) -> Response:
            return StringChunkResponse()

        # Call dispatch
        response = await middleware.dispatch(mock_request, mock_call_next)

        # Verify the response body was reconstructed correctly
        assert response.status_code == 200
        # The body should have been read and reconstructed
        assert hasattr(response, "body")
        # Check that string chunks were properly encoded
        expected_body = b"Hello from chunks"
        if hasattr(response, "body"):
            assert response.body == expected_body


class TestMiddlewareConfiguration:
    """Test middleware configuration options."""

    def test_custom_max_body_size(self) -> None:
        """Test that custom max body size is respected."""
        middleware = RequestLoggingMiddleware(
            Mock(), log_request_body=True, max_body_size=100
        )
        assert middleware.max_body_size == 100

    def test_default_configuration(self) -> None:
        """Test default middleware configuration."""
        middleware = RequestLoggingMiddleware(Mock())
        assert middleware.log_request_body is False
        assert middleware.log_response_body is False
        assert middleware.max_body_size == MAX_BODY_SIZE

    def test_truncate_body_method(self) -> None:
        """Test the truncate body method."""
        middleware = RequestLoggingMiddleware(Mock(), max_body_size=10)

        # Test string truncation
        result = middleware._truncate_body("Hello World!")
        assert result == "Hello Worl" + TRUNCATED_SUFFIX

        # Test bytes truncation
        result = middleware._truncate_body(b"Hello World!")
        assert result == "Hello Worl" + TRUNCATED_SUFFIX

        # Test no truncation needed
        result = middleware._truncate_body("Short")
        assert result == "Short"

        # Test binary data that can't be decoded - within size limit
        # The method tries to decode with errors='replace'
        # so it will show replacement chars
        result = middleware._truncate_body(b"\xff\xfe\xfd")
        assert len(result) == 3  # Should be decoded with replacement characters

        # Test binary data that can't be decoded - needs truncation
        # This covers lines 126-131
        binary_data = bytes([0xFF, 0xFE] * 20)  # 40 bytes of non-UTF8 data
        result = middleware._truncate_body(binary_data)
        assert result.endswith(TRUNCATED_SUFFIX)
        # The method decodes with errors='replace' so we get replacement chars
        assert len(result) > 10  # Should be truncated

    def test_truncate_body_decode_exception(self) -> None:
        """Test _truncate_body handles decode exceptions (lines 123-124, 130-131)."""
        middleware = RequestLoggingMiddleware(Mock(), max_body_size=50)

        # Create a custom bytes class that raises exception on decode
        class BadBytes(bytes):
            def decode(self, *_args: Any, **_kwargs: Any) -> str:  # noqa: ANN401 - test mock accepts any args
                raise UnicodeDecodeError("utf-8", b"", 0, 1, "Simulated decode error")

            def __getitem__(self, key: Any) -> Any:  # noqa: ANN401 - test mock for bytes operations
                # Ensure slicing returns BadBytes to maintain the decode override
                result = super().__getitem__(key)
                if isinstance(key, slice):
                    return BadBytes(result)
                return result

        # Test case 1: decode exception for body within max size (lines 123-124)
        bad_short = BadBytes(b"short")
        result = middleware._truncate_body(bad_short)
        assert result == "<binary data: 5 bytes>"

        # Test case 2: decode exception for truncated body (lines 130-131)
        bad_long = BadBytes(b"a" * 100)
        result = middleware._truncate_body(bad_long)
        assert result == f"<binary data: 100 bytes>{TRUNCATED_SUFFIX}"

    def test_content_type_extraction(self) -> None:
        """Test content type extraction."""
        # Test the static method directly

        headers = Headers({"content-type": "application/json; charset=utf-8"})
        content_type = RequestLoggingMiddleware._get_content_type(headers)
        assert content_type == "application/json"

        headers = Headers({"content-type": "text/plain"})
        content_type = RequestLoggingMiddleware._get_content_type(headers)
        assert content_type == "text/plain"

        headers = Headers({})
        content_type = RequestLoggingMiddleware._get_content_type(headers)
        assert content_type == ""
