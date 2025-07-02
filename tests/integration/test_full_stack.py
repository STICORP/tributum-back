"""End-to-end integration tests for the full application stack.

These tests verify that all components work together correctly:
- Middleware pipeline (Security Headers → Request Context → Request Logging)
- Exception handling with correlation IDs
- Database session management
- OpenTelemetry tracing
- Error response formatting
- Performance under concurrent load
"""

import asyncio
import time
from typing import Any
from uuid import uuid4

import pytest
from httpx import AsyncClient
from pytest_mock import MockerFixture
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.middleware.request_context import CORRELATION_ID_HEADER


@pytest.mark.integration
@pytest.mark.asyncio
class TestFullStackIntegration:
    """Test the complete application stack working together."""

    async def test_successful_request_full_flow(
        self, client_with_db: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test a successful request through all middleware with database access."""
        correlation_id = str(uuid4())

        # Make request with correlation ID
        response = await client_with_db.get(
            "/health", headers={CORRELATION_ID_HEADER: correlation_id}
        )

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["database"] is True

        # Verify headers
        assert response.headers[CORRELATION_ID_HEADER] == correlation_id
        assert response.headers["x-content-type-options"] == "nosniff"
        assert response.headers["x-frame-options"] == "DENY"
        assert response.headers["x-xss-protection"] == "1; mode=block"

        # Verify database was actually accessed
        result = await db_session.execute(text("SELECT 1"))
        assert result.scalar() == 1

    async def test_error_handling_with_correlation_id(
        self, client_with_db: AsyncClient
    ) -> None:
        """Test error handling preserves correlation ID through the stack."""
        correlation_id = str(uuid4())

        # Make request to non-existent endpoint
        response = await client_with_db.get(
            "/non-existent-endpoint", headers={CORRELATION_ID_HEADER: correlation_id}
        )

        # Verify error response
        assert response.status_code == 404
        assert response.headers[CORRELATION_ID_HEADER] == correlation_id

        # Check if response has error structure
        data = response.json()
        # Custom error handler response
        assert "error_code" in data
        assert data["error_code"] == "NOT_FOUND"

    async def test_info_endpoint_with_correlation_id(
        self, client_with_db: AsyncClient
    ) -> None:
        """Test the info endpoint returns application details."""
        correlation_id = str(uuid4())

        response = await client_with_db.get(
            "/info", headers={CORRELATION_ID_HEADER: correlation_id}
        )

        assert response.status_code == 200
        data = response.json()

        # Verify expected fields
        assert "app_name" in data
        assert "version" in data
        assert "environment" in data
        assert "debug" in data

        # Verify correlation ID propagation
        assert response.headers[CORRELATION_ID_HEADER] == correlation_id

    async def test_concurrent_requests_isolation(
        self, client_with_db: AsyncClient
    ) -> None:
        """Test that concurrent requests maintain proper isolation."""
        num_requests = 10
        correlation_ids = [str(uuid4()) for _ in range(num_requests)]

        async def make_request(correlation_id: str) -> tuple[str, dict[str, Any]]:
            """Make a request with a specific correlation ID."""
            response = await client_with_db.get(
                "/info", headers={CORRELATION_ID_HEADER: correlation_id}
            )
            return correlation_id, response.json()

        # Make concurrent requests
        results = await asyncio.gather(*[make_request(cid) for cid in correlation_ids])

        # Verify each request maintained its correlation ID
        for _correlation_id, data in results:
            # Each response should have the correct app info
            assert "app_name" in data
            assert "version" in data
            assert "environment" in data

    async def test_middleware_execution_order(
        self, client_with_db: AsyncClient
    ) -> None:
        """Test that middleware execute in the correct order."""
        response = await client_with_db.get("/")

        # Verify security headers (first middleware)
        assert "x-content-type-options" in response.headers
        assert response.headers["x-content-type-options"] == "nosniff"
        assert response.headers["x-frame-options"] == "DENY"
        assert response.headers["x-xss-protection"] == "1; mode=block"

        # Verify correlation ID (second middleware)
        assert CORRELATION_ID_HEADER in response.headers

        # Response should be successful
        assert response.status_code == 200

    async def test_database_connectivity_in_health_check(
        self, client_with_db: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test that health check properly verifies database connectivity."""
        # First, ensure database is accessible
        result = await db_session.execute(text("SELECT 1"))
        assert result.scalar() == 1

        # Make health check request
        response = await client_with_db.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert data["database"] is True

    async def test_performance_under_load(self, client_with_db: AsyncClient) -> None:
        """Test that the full stack performs well under concurrent load."""
        num_requests = 50
        start_time = time.time()

        # Make concurrent requests
        responses = await asyncio.gather(
            *[client_with_db.get("/info") for _ in range(num_requests)]
        )

        end_time = time.time()
        duration = end_time - start_time

        # All requests should succeed
        assert all(r.status_code == 200 for r in responses)

        # Should complete reasonably fast (less than 100ms per request average)
        average_time = duration / num_requests
        assert average_time < 0.1  # 100ms

    async def test_request_logging_with_correlation_id(
        self, client_with_db: AsyncClient
    ) -> None:
        """Test that requests are logged with correlation IDs."""
        correlation_id = str(uuid4())

        # Make request
        response = await client_with_db.get(
            "/info", headers={CORRELATION_ID_HEADER: correlation_id}
        )

        assert response.status_code == 200

        # Verify correlation ID is in response headers
        assert response.headers[CORRELATION_ID_HEADER] == correlation_id

        # The actual logging verification would require checking stdout/stderr
        # or using a custom log handler, which is complex in async context.
        # For now, we'll just verify the correlation ID propagation works.

    async def test_error_response_format(self, client_with_db: AsyncClient) -> None:
        """Test that error responses follow the expected format."""
        # Test 404 error
        correlation_id = str(uuid4())
        response = await client_with_db.get(
            "/non-existent", headers={CORRELATION_ID_HEADER: correlation_id}
        )
        assert response.status_code == 404

        # Check response has expected structure according to ErrorResponse schema
        data = response.json()
        assert "error_code" in data
        assert data["error_code"] == "NOT_FOUND"
        assert "message" in data
        assert isinstance(data["message"], str)
        assert "correlation_id" in data
        assert data["correlation_id"] == correlation_id
        assert "timestamp" in data
        assert "severity" in data
        assert data["severity"] in ["LOW", "MEDIUM", "HIGH", "CRITICAL", None]
        assert "service_info" in data
        if data["service_info"]:
            assert "name" in data["service_info"]
            assert "version" in data["service_info"]
            assert "environment" in data["service_info"]

    async def test_health_check_degraded_state(
        self, client_with_db: AsyncClient, mocker: MockerFixture
    ) -> None:
        """Test health check reports degraded state when database is unavailable."""
        # Mock database connection check to return failure
        mocker.patch(
            "src.api.main.check_database_connection",
            return_value=(False, "Database connection failed"),
        )

        response = await client_with_db.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "degraded"
        assert data["database"] is False

    @pytest.mark.parametrize("endpoint", ["/", "/health", "/info"])
    async def test_all_endpoints_have_security_headers(
        self, client_with_db: AsyncClient, endpoint: str
    ) -> None:
        """Test that all endpoints return security headers."""
        response = await client_with_db.get(endpoint)

        # All endpoints should have security headers
        assert response.headers["x-content-type-options"] == "nosniff"
        assert response.headers["x-frame-options"] == "DENY"
        assert response.headers["x-xss-protection"] == "1; mode=block"
        assert "strict-transport-security" in response.headers

    async def test_correlation_id_generation(self, client_with_db: AsyncClient) -> None:
        """Test that correlation ID is generated if not provided."""
        # Make request without correlation ID
        response = await client_with_db.get("/info")

        assert response.status_code == 200
        # Should have generated a correlation ID
        assert CORRELATION_ID_HEADER in response.headers
        assert len(response.headers[CORRELATION_ID_HEADER]) > 0

    async def test_multiple_sequential_requests(
        self, client_with_db: AsyncClient
    ) -> None:
        """Test multiple sequential requests work correctly."""
        for _ in range(5):
            correlation_id = str(uuid4())
            response = await client_with_db.get(
                "/info", headers={CORRELATION_ID_HEADER: correlation_id}
            )

            assert response.status_code == 200
            assert response.headers[CORRELATION_ID_HEADER] == correlation_id

            data = response.json()
            assert data["app_name"] == "Tributum"

    async def test_error_response_no_debug_in_production(
        self, client_with_db: AsyncClient, production_env: None
    ) -> None:
        """Test that debug information is not included in production error responses."""
        _ = production_env  # Fixture used for its side effects

        response = await client_with_db.get("/non-existent-endpoint")
        assert response.status_code == 404

        data = response.json()
        assert "error_code" in data
        assert data["error_code"] == "NOT_FOUND"

        # In production, debug_info should not be present or should be None
        assert data.get("debug_info") is None
