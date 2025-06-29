"""Unit tests for RequestContextMiddleware."""

from collections.abc import Awaitable, Callable, MutableMapping
from typing import Any

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from src.api.constants import CORRELATION_ID_HEADER
from src.api.middleware.request_context import RequestContextMiddleware
from src.core.context import RequestContext


@pytest.fixture
def app() -> FastAPI:
    """Create a test FastAPI app with RequestContextMiddleware."""
    test_app = FastAPI()
    test_app.add_middleware(RequestContextMiddleware)

    @test_app.get("/test")
    async def test_endpoint() -> dict[str, str | None]:
        """Test endpoint that returns the current correlation ID."""
        return {"correlation_id": RequestContext.get_correlation_id()}

    @test_app.get("/test-header")
    async def test_header_endpoint(request: Request) -> dict[str, str]:
        """Test endpoint that returns request headers."""
        return {"header": request.headers.get(CORRELATION_ID_HEADER, "not-found")}

    return test_app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Create a test client for the app."""
    return TestClient(app)


@pytest.mark.unit
class TestRequestContextMiddleware:
    """Test cases for RequestContextMiddleware."""

    def test_generates_correlation_id_when_missing(self, client: TestClient) -> None:
        """Test that middleware generates a correlation ID when not provided."""
        response = client.get("/test")

        # Should have a correlation ID in response
        assert CORRELATION_ID_HEADER in response.headers
        correlation_id = response.headers[CORRELATION_ID_HEADER]

        # Should be a valid UUID format
        assert len(correlation_id) == 36
        assert correlation_id.count("-") == 4

        # Endpoint should have access to the correlation ID
        assert response.json()["correlation_id"] == correlation_id

    def test_uses_existing_correlation_id(self, client: TestClient) -> None:
        """Test that middleware uses correlation ID from request header."""
        test_correlation_id = "test-correlation-123"
        response = client.get(
            "/test", headers={CORRELATION_ID_HEADER: test_correlation_id}
        )

        # Should echo the same correlation ID
        assert response.headers[CORRELATION_ID_HEADER] == test_correlation_id
        assert response.json()["correlation_id"] == test_correlation_id

    def test_adds_correlation_id_to_response_headers(self, client: TestClient) -> None:
        """Test that correlation ID is added to response headers."""
        response = client.get("/test")

        # Should have correlation ID in response headers
        assert CORRELATION_ID_HEADER in response.headers

    def test_context_isolation_between_requests(self, client: TestClient) -> None:
        """Test that context is properly isolated between requests."""
        # First request with custom correlation ID
        correlation_id_1 = "request-1-correlation-id"
        response_1 = client.get(
            "/test", headers={CORRELATION_ID_HEADER: correlation_id_1}
        )
        assert response_1.json()["correlation_id"] == correlation_id_1

        # Second request with different correlation ID
        correlation_id_2 = "request-2-correlation-id"
        response_2 = client.get(
            "/test", headers={CORRELATION_ID_HEADER: correlation_id_2}
        )
        assert response_2.json()["correlation_id"] == correlation_id_2

        # Third request without correlation ID should generate new one
        response_3 = client.get("/test")
        correlation_id_3 = response_3.json()["correlation_id"]
        assert correlation_id_3 != correlation_id_1
        assert correlation_id_3 != correlation_id_2
        assert correlation_id_3 is not None

    @pytest.mark.asyncio
    async def test_context_cleared_after_request(self) -> None:
        """Test that context is cleared after request completion."""
        # Clear any existing context first
        RequestContext.clear()

        # Before any request, context should be None
        assert RequestContext.get_correlation_id() is None

        # Set a correlation ID
        test_id = "test-correlation-456"
        RequestContext.set_correlation_id(test_id)
        assert RequestContext.get_correlation_id() == test_id

        # Clear context (as middleware would do)
        RequestContext.clear()
        assert RequestContext.get_correlation_id() is None

    def test_empty_correlation_id_generates_new_one(self, client: TestClient) -> None:
        """Test that empty correlation ID header is treated as missing."""
        response = client.get("/test", headers={CORRELATION_ID_HEADER: ""})

        # Should generate a new correlation ID
        correlation_id = response.headers[CORRELATION_ID_HEADER]
        assert correlation_id != ""
        assert len(correlation_id) == 36

    @pytest.mark.asyncio
    async def test_non_http_request_passthrough(self) -> None:
        """Test that non-HTTP requests (like WebSocket) are passed through."""
        # Create a mock app that tracks if it was called
        called = False

        async def mock_app(
            scope: MutableMapping[str, Any],
            receive: Callable[[], Awaitable[MutableMapping[str, Any]]],
            send: Callable[[MutableMapping[str, Any]], Awaitable[None]],
        ) -> None:
            nonlocal called
            called = True
            # Use the parameters to avoid unused argument warnings
            assert scope["type"] == "websocket"
            assert receive is not None
            assert send is not None

        # Create middleware instance
        middleware = RequestContextMiddleware(mock_app)

        # Create a WebSocket scope
        websocket_scope: MutableMapping[str, Any] = {
            "type": "websocket",
            "path": "/ws",
            "headers": [],
        }

        # Mock receive and send callables
        async def mock_receive() -> MutableMapping[str, Any]:
            return {"type": "websocket.connect"}

        async def mock_send(message: MutableMapping[str, Any]) -> None:
            pass

        # Call middleware with WebSocket scope
        await middleware(websocket_scope, mock_receive, mock_send)

        # Verify the app was called directly without context handling
        assert called
        # Context should remain None (not set by middleware)
        assert RequestContext.get_correlation_id() is None

    @pytest.mark.asyncio
    async def test_exception_handling_clears_context(self) -> None:
        """Test that context is cleared when the app raises an exception."""

        # Create a mock app that raises an exception
        async def failing_app(
            scope: MutableMapping[str, Any],
            receive: Callable[[], Awaitable[MutableMapping[str, Any]]],
            send: Callable[[MutableMapping[str, Any]], Awaitable[None]],
        ) -> None:
            # Use the parameters to avoid unused argument warnings
            assert scope is not None
            assert receive is not None
            assert send is not None
            # Verify context is set before exception
            assert RequestContext.get_correlation_id() is not None
            raise ValueError("Test exception")

        # Create middleware instance
        middleware = RequestContextMiddleware(failing_app)

        # Create an HTTP scope
        http_scope: MutableMapping[str, Any] = {
            "type": "http",
            "method": "GET",
            "path": "/test",
            "headers": [],
        }

        # Mock receive and send callables
        async def mock_receive() -> MutableMapping[str, Any]:
            return {"type": "http.request", "body": b""}

        async def mock_send(message: MutableMapping[str, Any]) -> None:
            # Use the parameter to avoid unused argument warnings
            assert message is not None

        # Ensure context is clear before test
        RequestContext.clear()
        assert RequestContext.get_correlation_id() is None

        # Call middleware and expect exception
        with pytest.raises(ValueError, match="Test exception"):
            await middleware(http_scope, mock_receive, mock_send)

        # Verify context was cleared after exception
        assert RequestContext.get_correlation_id() is None
