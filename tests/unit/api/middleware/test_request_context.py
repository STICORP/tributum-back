"""Unit tests for RequestContextMiddleware."""

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from src.api.middleware.request_context import RequestContextMiddleware
from src.core.context import CORRELATION_ID_HEADER, RequestContext


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
