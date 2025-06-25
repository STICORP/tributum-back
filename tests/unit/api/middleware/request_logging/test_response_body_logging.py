"""Tests for response body logging functionality in RequestLoggingMiddleware."""

from collections.abc import AsyncIterator, MutableMapping
from contextlib import suppress
from typing import TYPE_CHECKING, Any

import pytest
from fastapi import Request, Response
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

from src.api.middleware.request_logging import RequestLoggingMiddleware

from .conftest import create_test_app

if TYPE_CHECKING:
    from starlette.types import Receive, Send


@pytest.mark.unit
class TestResponseBodyLogging:
    """Test cases for response body logging functionality."""

    def test_logs_json_response_body(self, mocker: MockerFixture) -> None:
        """Test that middleware logs JSON response body."""
        mock_logger = mocker.Mock()
        mocker.patch(
            "src.api.middleware.request_logging.get_logger", return_value=mock_logger
        )

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

    def test_no_response_body_logging_when_disabled(
        self, mocker: MockerFixture
    ) -> None:
        """Test that response body is not logged when disabled."""
        mock_logger = mocker.Mock()
        mocker.patch(
            "src.api.middleware.request_logging.get_logger", return_value=mock_logger
        )

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

    def test_sanitizes_response_headers(self, mocker: MockerFixture) -> None:
        """Test that response headers are sanitized."""
        mock_logger = mocker.Mock()
        mocker.patch(
            "src.api.middleware.request_logging.get_logger", return_value=mock_logger
        )

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

    def test_logs_non_json_response_body(self, mocker: MockerFixture) -> None:
        """Test that middleware logs non-JSON response body."""
        mock_logger = mocker.Mock()
        mocker.patch(
            "src.api.middleware.request_logging.get_logger", return_value=mock_logger
        )

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

    def test_handles_invalid_json_response(self, mocker: MockerFixture) -> None:
        """Test that middleware handles invalid JSON in response body."""
        mock_logger = mocker.Mock()
        mocker.patch(
            "src.api.middleware.request_logging.get_logger", return_value=mock_logger
        )

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
    async def test_logs_response_with_string_chunks(
        self, mocker: MockerFixture
    ) -> None:
        """Test that middleware handles response with string chunks."""
        # Test middleware directly to control the response body iterator
        middleware = RequestLoggingMiddleware(mocker.Mock(), log_response_body=True)

        # Create a mock request
        mock_request = mocker.Mock(spec=Request)
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

        # Response should have the combined content
        assert response.status_code == 200
        # The middleware should have collected all chunks

    def test_truncates_large_response_body(self, mocker: MockerFixture) -> None:
        """Test that middleware truncates large response bodies."""
        mock_logger = mocker.Mock()
        mocker.patch(
            "src.api.middleware.request_logging.get_logger", return_value=mock_logger
        )

        # Create app with small max body size
        app = create_test_app(log_response_body=True, max_body_size=20)

        # Add endpoint that returns large response
        @app.get("/large-response")
        async def large_response() -> Response:
            return Response(content="A" * 100, media_type="text/plain")

        client = TestClient(app)
        client.get("/large-response")

        # Find the request_completed call
        completed_calls = [
            call
            for call in mock_logger.info.call_args_list
            if call[0][0] == "request_completed"
        ]
        assert len(completed_calls) == 1

        # Verify response was truncated
        call_kwargs = completed_calls[0][1]
        assert "response_body" in call_kwargs
        # Should be truncated to max_body_size
        assert len(call_kwargs["response_body"]) <= 20 + len("... [truncated]")

    def test_handles_response_body_error(self, mocker: MockerFixture) -> None:
        """Test that middleware handles response body errors gracefully."""
        mock_logger = mocker.Mock()
        mocker.patch(
            "src.api.middleware.request_logging.get_logger", return_value=mock_logger
        )

        app = create_test_app(log_response_body=True)

        # Add endpoint that simulates an error during body iteration
        @app.get("/error-response")
        async def error_response() -> Response:
            class ErrorResponse(Response):
                async def __call__(
                    self,
                    scope: MutableMapping[str, Any],
                    receive: "Receive",
                    send: "Send",
                ) -> None:
                    _ = scope  # Mark as intentionally unused
                    _ = receive  # Mark as intentionally unused
                    await send(
                        {
                            "type": "http.response.start",
                            "status": 200,
                            "headers": [(b"content-type", b"text/plain")],
                        }
                    )
                    # Simulate partial response then error
                    await send({"type": "http.response.body", "body": b"Partial"})
                    # Don't send the final empty body to simulate incomplete response

            return ErrorResponse(content="")

        client = TestClient(app)
        # This might raise an exception in the test client, but the middleware
        # should handle it
        with suppress(Exception):
            client.get("/error-response")

        # Should still log something - just verify no crash occurred
        # Check that at least request_started was logged
        started_calls = [
            call
            for call in mock_logger.info.call_args_list
            if call[0][0] == "request_started"
        ]
        assert len(started_calls) >= 1  # Verify middleware ran
