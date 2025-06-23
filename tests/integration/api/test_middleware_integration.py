"""Integration tests for middleware execution order and behavior."""

import pytest
from httpx import ASGITransport, AsyncClient

from src.api.main import app
from src.core.context import CORRELATION_ID_HEADER


@pytest.mark.integration
@pytest.mark.asyncio
async def test_all_middleware_active() -> None:
    """Test that all middleware are active and working together."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/")

        # Check that security headers are present (from SecurityHeadersMiddleware)
        assert "X-Content-Type-Options" in response.headers
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert "X-Frame-Options" in response.headers
        assert response.headers["X-Frame-Options"] == "DENY"
        assert "X-XSS-Protection" in response.headers
        assert response.headers["X-XSS-Protection"] == "1; mode=block"
        assert "Strict-Transport-Security" in response.headers

        # Check that correlation ID is present (from RequestContextMiddleware)
        assert CORRELATION_ID_HEADER in response.headers
        correlation_id = response.headers[CORRELATION_ID_HEADER]
        assert len(correlation_id) == 36  # UUID format
        assert correlation_id.count("-") == 4

        # RequestLoggingMiddleware doesn't add headers, but we can
        # verify it doesn't break anything
        assert response.status_code == 200
        assert response.json() == {"message": "Hello from Tributum!"}


@pytest.mark.integration
@pytest.mark.asyncio
async def test_middleware_execution_order() -> None:
    """Test that middleware execute in the correct order.

    The expected order is:
    1. SecurityHeadersMiddleware (first to process request, last to process response)
    2. RequestContextMiddleware (creates or preserves correlation ID)
    3. RequestLoggingMiddleware (uses correlation ID for logging)
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Test 1: Send request without correlation ID - should generate one
        response1 = await client.get("/")
        assert CORRELATION_ID_HEADER in response1.headers
        generated_correlation_id = response1.headers[CORRELATION_ID_HEADER]
        assert len(generated_correlation_id) == 36  # Valid UUID

        # Test 2: Send request with custom correlation ID - should preserve it
        custom_correlation_id = "12345678-1234-1234-1234-123456789012"
        headers = {CORRELATION_ID_HEADER: custom_correlation_id}
        response2 = await client.get("/", headers=headers)

        # The correlation ID in the response should match what we sent
        # because RequestContextMiddleware preserves existing
        # correlation IDs for distributed tracing
        response_correlation_id = response2.headers[CORRELATION_ID_HEADER]
        assert response_correlation_id == custom_correlation_id

        # All security headers should be present in both responses
        for response in [response1, response2]:
            assert "X-Content-Type-Options" in response.headers
            assert "X-Frame-Options" in response.headers
            assert "X-XSS-Protection" in response.headers


@pytest.mark.integration
@pytest.mark.asyncio
async def test_middleware_error_handling() -> None:
    """Test that middleware work correctly even when errors occur."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Request a non-existent endpoint
        response = await client.get("/nonexistent")

        # Even on 404, all middleware should still function
        assert response.status_code == 404

        # Security headers should be present
        assert "X-Content-Type-Options" in response.headers
        assert "X-Frame-Options" in response.headers
        assert "X-XSS-Protection" in response.headers

        # Correlation ID should be present
        assert CORRELATION_ID_HEADER in response.headers
        assert len(response.headers[CORRELATION_ID_HEADER]) == 36


@pytest.mark.integration
@pytest.mark.asyncio
async def test_multiple_requests_different_correlation_ids() -> None:
    """Test that each request gets a unique correlation ID."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Send multiple requests
        responses = []
        for _ in range(5):
            response = await client.get("/")
            responses.append(response)

        # Extract correlation IDs
        correlation_ids = [r.headers[CORRELATION_ID_HEADER] for r in responses]

        # All correlation IDs should be unique
        assert len(set(correlation_ids)) == 5

        # All responses should have security headers
        for response in responses:
            assert "X-Content-Type-Options" in response.headers
            assert "X-Frame-Options" in response.headers
            assert "X-XSS-Protection" in response.headers


@pytest.mark.integration
@pytest.mark.asyncio
async def test_health_endpoint_with_middleware() -> None:
    """Test that the health endpoint works with all middleware."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ("healthy", "degraded")
        assert "database" in data

        # All middleware should be active
        assert "X-Content-Type-Options" in response.headers
        assert CORRELATION_ID_HEADER in response.headers


@pytest.mark.integration
@pytest.mark.asyncio
async def test_info_endpoint_with_middleware() -> None:
    """Test that the info endpoint works with all middleware."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/info")

        assert response.status_code == 200

        # Check response content
        data = response.json()
        assert "app_name" in data
        assert "version" in data
        assert "environment" in data
        assert "debug" in data

        # All middleware should be active
        assert "X-Content-Type-Options" in response.headers
        assert CORRELATION_ID_HEADER in response.headers
