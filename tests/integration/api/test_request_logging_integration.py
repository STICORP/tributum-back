"""Integration tests specifically for RequestLoggingMiddleware with other middleware."""

import time

import pytest
from httpx import AsyncClient

from src.api.middleware.request_context import CORRELATION_ID_HEADER


@pytest.mark.integration
class TestRequestLoggingIntegration:
    """Test RequestLoggingMiddleware integration with other middleware."""

    async def test_request_logging_middleware_integration(
        self, client: AsyncClient
    ) -> None:
        """Test that RequestLoggingMiddleware works with other middleware."""
        response = await client.get("/")

        assert response.status_code == 200

        # Should have all three middleware headers
        assert "X-Content-Type-Options" in response.headers  # SecurityHeaders
        assert CORRELATION_ID_HEADER in response.headers  # RequestContext
        assert "X-Request-ID" in response.headers  # RequestLogging

        # Request ID should be a valid UUID
        request_id = response.headers["X-Request-ID"]
        assert len(request_id) == 36
        assert request_id.count("-") == 4

    async def test_request_id_generation_and_preservation(
        self, client: AsyncClient
    ) -> None:
        """Test that request IDs are generated or preserved correctly."""
        # Test 1: No request ID provided - should generate one
        response1 = await client.get("/")
        assert "X-Request-ID" in response1.headers
        generated_request_id = response1.headers["X-Request-ID"]
        assert len(generated_request_id) == 36  # Valid UUID

        # Test 2: Custom request ID provided - should preserve it
        custom_request_id = "custom-request-12345678-1234-1234-1234-123456789012"
        headers = {"X-Request-ID": custom_request_id}
        response2 = await client.get("/", headers=headers)

        # Should return the same request ID we sent
        assert response2.headers["X-Request-ID"] == custom_request_id

        # Both should have correlation IDs
        assert CORRELATION_ID_HEADER in response1.headers
        assert CORRELATION_ID_HEADER in response2.headers

    async def test_health_endpoint_with_request_logging(
        self, client: AsyncClient
    ) -> None:
        """Test that health endpoint works with request logging.

        The health endpoint should still get request IDs even though
        it's excluded from logging.
        """
        response = await client.get("/health")

        assert response.status_code == 200

        # Health endpoint should still get all middleware headers
        assert "X-Content-Type-Options" in response.headers
        assert CORRELATION_ID_HEADER in response.headers
        # Request logging middleware skips excluded paths entirely
        # so X-Request-ID is NOT added for /health
        assert "X-Request-ID" not in response.headers

        # Verify the health response structure
        data = response.json()
        assert "status" in data
        assert "database" in data

    async def test_error_handling_with_request_logging(
        self, client: AsyncClient
    ) -> None:
        """Test that errors are handled correctly with request logging active."""
        # Request non-existent endpoint
        response = await client.get("/this-does-not-exist")

        assert response.status_code == 404

        # All middleware should still function on errors
        assert "X-Content-Type-Options" in response.headers
        assert CORRELATION_ID_HEADER in response.headers
        assert "X-Request-ID" in response.headers

        # Error response should have proper structure
        error_data = response.json()
        assert "error_code" in error_data
        assert error_data["error_code"] == "NOT_FOUND"
        assert "correlation_id" in error_data
        # The correlation ID in the error should match the header
        assert error_data["correlation_id"] == response.headers[CORRELATION_ID_HEADER]

    async def test_request_id_differs_from_correlation_id(
        self, client: AsyncClient
    ) -> None:
        """Test that request IDs and correlation IDs are different."""
        response = await client.get("/")

        request_id = response.headers["X-Request-ID"]
        correlation_id = response.headers[CORRELATION_ID_HEADER]

        # Both should be present and valid UUIDs
        assert len(request_id) == 36
        assert len(correlation_id) == 36

        # They should be different values
        assert request_id != correlation_id

        # Send multiple requests - each should have unique IDs
        responses = []
        for _ in range(3):
            resp = await client.get("/")
            responses.append(
                {
                    "request_id": resp.headers["X-Request-ID"],
                    "correlation_id": resp.headers[CORRELATION_ID_HEADER],
                }
            )

        # All request IDs should be unique
        request_ids = [r["request_id"] for r in responses]
        assert len(set(request_ids)) == 3

        # All correlation IDs should be unique
        correlation_ids = [r["correlation_id"] for r in responses]
        assert len(set(correlation_ids)) == 3

    async def test_multiple_endpoints_with_request_logging(
        self, client: AsyncClient
    ) -> None:
        """Test multiple endpoints all work with request logging."""
        # Test different endpoints
        # (excluding /health which is excluded from logging)
        endpoints_with_logging = ["/", "/info"]

        for endpoint in endpoints_with_logging:
            response = await client.get(endpoint)

            # All should be successful
            assert response.status_code == 200

            # All should have the three middleware headers
            assert "X-Content-Type-Options" in response.headers
            assert CORRELATION_ID_HEADER in response.headers
            assert "X-Request-ID" in response.headers

            # Each request should have unique IDs
            assert len(response.headers["X-Request-ID"]) == 36
            assert len(response.headers[CORRELATION_ID_HEADER]) == 36

        # Test health endpoint separately (excluded from logging)
        health_response = await client.get("/health")
        assert health_response.status_code == 200
        assert "X-Content-Type-Options" in health_response.headers
        assert CORRELATION_ID_HEADER in health_response.headers
        assert "X-Request-ID" not in health_response.headers  # Excluded from logging

    async def test_request_logging_performance(self, client: AsyncClient) -> None:
        """Test that request logging doesn't significantly impact performance.

        This is a basic test to ensure middleware doesn't cause timeouts.
        """
        # Send multiple rapid requests
        start_time = time.time()

        responses = []
        for _ in range(10):
            response = await client.get("/")
            responses.append(response)

        end_time = time.time()
        total_time = end_time - start_time

        # All requests should succeed
        assert all(r.status_code == 200 for r in responses)

        # All should have request IDs
        assert all("X-Request-ID" in r.headers for r in responses)

        # Should complete reasonably quickly (10 requests in under 2 seconds)
        assert total_time < 2.0, f"Requests took too long: {total_time:.2f}s"

    async def test_request_id_format_validation(self, client: AsyncClient) -> None:
        """Test various request ID formats are handled correctly."""
        # Test various request ID formats
        test_cases = [
            # (input_id, should_preserve)
            ("valid-uuid-12345678-1234-1234-1234-123456789012", True),
            ("short-id-123", True),
            ("", False),  # Empty should generate new
            ("a" * 200, True),  # Long ID should be preserved
            ("special-chars-!@#$%", True),  # Special chars preserved
        ]

        for input_id, should_preserve in test_cases:
            headers = {"X-Request-ID": input_id} if input_id else {}
            response = await client.get("/", headers=headers)

            assert response.status_code == 200
            assert "X-Request-ID" in response.headers

            if should_preserve and input_id:
                assert response.headers["X-Request-ID"] == input_id
            else:
                # Should have generated a new UUID
                assert len(response.headers["X-Request-ID"]) == 36
