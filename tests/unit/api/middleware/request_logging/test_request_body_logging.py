"""Tests for request body logging functionality in RequestLoggingMiddleware."""

import asyncio
from typing import Any

import pytest
from fastapi import Request, Response
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

from src.api.middleware.request_logging import RequestLoggingMiddleware
from src.core.constants import TRUNCATED_SUFFIX

from .conftest import create_test_app


@pytest.mark.unit
class TestRequestBodyLogging:
    """Test cases for request body logging functionality."""

    def test_logs_json_request_body(self, mocker: MockerFixture) -> None:
        """Test that middleware logs JSON request body."""
        mock_logger = mocker.Mock()
        mocker.patch(
            "src.api.middleware.request_logging.get_logger", return_value=mock_logger
        )

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

    def test_logs_form_data_request_body(self, mocker: MockerFixture) -> None:
        """Test that middleware logs form data request body."""
        mock_logger = mocker.Mock()
        mocker.patch(
            "src.api.middleware.request_logging.get_logger", return_value=mock_logger
        )

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

    def test_logs_text_request_body(self, mocker: MockerFixture) -> None:
        """Test that middleware logs text request body."""
        mock_logger = mocker.Mock()
        mocker.patch(
            "src.api.middleware.request_logging.get_logger", return_value=mock_logger
        )

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

    def test_logs_binary_request_metadata(self, mocker: MockerFixture) -> None:
        """Test that middleware logs binary request metadata only."""
        mock_logger = mocker.Mock()
        mocker.patch(
            "src.api.middleware.request_logging.get_logger", return_value=mock_logger
        )

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

    def test_truncates_large_request_body(self, mocker: MockerFixture) -> None:
        """Test that middleware truncates large request bodies."""
        mock_logger = mocker.Mock()
        mocker.patch(
            "src.api.middleware.request_logging.get_logger", return_value=mock_logger
        )

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

    def test_sanitizes_headers_when_body_logging_enabled(
        self, mocker: MockerFixture
    ) -> None:
        """Test that headers are sanitized when body logging is enabled."""
        mock_logger = mocker.Mock()
        mocker.patch(
            "src.api.middleware.request_logging.get_logger", return_value=mock_logger
        )

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

    def test_handles_invalid_json_gracefully(self, mocker: MockerFixture) -> None:
        """Test that middleware handles invalid JSON gracefully."""
        mock_logger = mocker.Mock()
        mocker.patch(
            "src.api.middleware.request_logging.get_logger", return_value=mock_logger
        )

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

    def test_request_body_still_available_to_endpoint(
        self, mocker: MockerFixture
    ) -> None:
        """Test that request body is still available to the endpoint."""
        mock_logger = mocker.Mock()
        mocker.patch(
            "src.api.middleware.request_logging.get_logger", return_value=mock_logger
        )

        app = create_test_app(log_request_body=True)
        client = TestClient(app)

        # Send JSON body
        body = {"username": "test", "password": "pass", "email": "test@example.com"}
        response = client.post("/json-endpoint", json=body)

        # Verify endpoint received the body correctly
        assert response.status_code == 200
        assert response.json()["received"]["username"] == "test"
        assert response.json()["received"]["email"] == "test@example.com"

    def test_receive_function_works_correctly(self, mocker: MockerFixture) -> None:
        """Test that the receive function properly returns the body."""
        mock_logger = mocker.Mock()
        mocker.patch(
            "src.api.middleware.request_logging.get_logger", return_value=mock_logger
        )

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

    def test_handles_form_data_with_invalid_utf8(self, mocker: MockerFixture) -> None:
        """Test that middleware handles form data with invalid UTF-8 bytes."""
        mock_logger = mocker.Mock()
        mocker.patch(
            "src.api.middleware.request_logging.get_logger", return_value=mock_logger
        )

        app = create_test_app(log_request_body=True)
        client = TestClient(app)

        # Send form data with invalid UTF-8 bytes
        invalid_utf8_data = b"field1=value1&field2=\xff\xfe"
        client.post(
            "/form-endpoint",
            content=invalid_utf8_data,
            headers={"content-type": "application/x-www-form-urlencoded"},
        )

        # Should handle the error and truncate the body
        started_calls = [
            call
            for call in mock_logger.info.call_args_list
            if call[0][0] == "request_started"
        ]
        assert len(started_calls) == 1

        # Verify the body was truncated due to decode error
        call_kwargs = started_calls[0][1]
        assert "body" in call_kwargs
        assert isinstance(call_kwargs["body"], str)
        assert call_kwargs["body"].startswith("field1=value1&field2=")

    @pytest.mark.asyncio
    async def test_receive_function_coverage(self, mocker: MockerFixture) -> None:
        """Test the receive function implementation to cover line 362."""
        # Create middleware
        middleware = RequestLoggingMiddleware(mocker.Mock(), log_request_body=True)

        # Create a mock request
        mock_request = mocker.Mock(spec=Request)
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
            # Call it to test line 362
            result = await request._receive()
            assert result == {"type": "http.request", "body": test_body}

            # Return a mock response
            mock_response = mocker.Mock(spec=Response)
            mock_response.status_code = 200
            mock_response.headers = {}
            assert isinstance(mock_response, Response)
            return mock_response

        # Call dispatch
        await middleware.dispatch(mock_request, mock_call_next)

    def test_no_body_logging_when_disabled(self, mocker: MockerFixture) -> None:
        """Test that body is not logged when disabled."""
        mock_logger = mocker.Mock()
        mocker.patch(
            "src.api.middleware.request_logging.get_logger", return_value=mock_logger
        )

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

    def test_body_logging_only_for_write_methods(self, mocker: MockerFixture) -> None:
        """Test that body logging only happens for POST/PUT/PATCH."""
        mock_logger = mocker.Mock()
        mocker.patch(
            "src.api.middleware.request_logging.get_logger", return_value=mock_logger
        )

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

    def test_handles_request_body_read_failure(self, mocker: MockerFixture) -> None:
        """Test that middleware handles request body read failures gracefully."""
        mock_logger = mocker.Mock()
        mocker.patch(
            "src.api.middleware.request_logging.get_logger", return_value=mock_logger
        )

        app = create_test_app(log_request_body=True)

        # Mock request that fails to read body
        async def failing_body() -> bytes:
            raise RuntimeError("Failed to read body")

        # Create a mock request
        mock_request = mocker.Mock(spec=Request)
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

    def test_handles_empty_request_body(self, mocker: MockerFixture) -> None:
        """Test that middleware handles empty request body correctly."""
        mock_logger = mocker.Mock()
        mocker.patch(
            "src.api.middleware.request_logging.get_logger", return_value=mock_logger
        )

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

    def test_handles_invalid_form_data_gracefully(self, mocker: MockerFixture) -> None:
        """Test that middleware handles invalid form data gracefully."""
        mock_logger = mocker.Mock()
        mocker.patch(
            "src.api.middleware.request_logging.get_logger", return_value=mock_logger
        )

        app = create_test_app(log_request_body=True)
        client = TestClient(app)

        # Send malformed form data
        client.post(
            "/form-endpoint",
            content=b"malformed&&&&data==",
            headers={"content-type": "application/x-www-form-urlencoded"},
        )

        # Should not crash, just log what it can
        started_calls = [
            call
            for call in mock_logger.info.call_args_list
            if call[0][0] == "request_started"
        ]
        assert len(started_calls) == 1
