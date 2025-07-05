"""Integration tests for middleware execution order and behavior."""

import pytest
from httpx import AsyncClient

from src.api.middleware.request_context import CORRELATION_ID_HEADER


@pytest.mark.integration
class TestMiddlewareIntegration:
    """Test middleware execution order and behavior."""

    async def test_all_middleware_active(self, client: AsyncClient) -> None:
        """Test that all middleware are active and working together."""
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

        # Verify middleware doesn't break anything
        assert response.status_code == 200
        assert response.json() == {"message": "Hello from Tributum!"}

    async def test_middleware_execution_order(self, client: AsyncClient) -> None:
        """Test that middleware execute in the correct order.

        The expected order is:
        1. SecurityHeadersMiddleware (first to process request,
           last to process response)
        2. RequestContextMiddleware (creates or preserves correlation ID)
        """
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

    async def test_middleware_error_handling(self, client: AsyncClient) -> None:
        """Test that middleware work correctly even when errors occur."""
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

    async def test_multiple_requests_different_correlation_ids(
        self, client: AsyncClient
    ) -> None:
        """Test that each request gets a unique correlation ID."""
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

    async def test_health_endpoint_with_middleware(self, client: AsyncClient) -> None:
        """Test that the health endpoint works with all middleware.

        Note: This test uses the standard client fixture which connects to the
        real database configuration, allowing us to test actual database
        connectivity as the health endpoint would experience in production.
        """
        response = await client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ("healthy", "degraded")
        assert "database" in data

        # All middleware should be active
        assert "X-Content-Type-Options" in response.headers
        assert CORRELATION_ID_HEADER in response.headers
        # Note: X-Request-ID is not present for /health
        # as it's excluded from logging

    async def test_info_endpoint_with_middleware(self, client: AsyncClient) -> None:
        """Test that the info endpoint works with all middleware."""
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
        assert "X-Request-ID" in response.headers
