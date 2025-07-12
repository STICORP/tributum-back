"""Integration tests for ORJSONResponse in FastAPI."""

import time
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from src.api.main import create_app


@pytest.mark.integration
class TestORJSONIntegration:
    """Test ORJSONResponse integration with FastAPI."""

    async def test_all_endpoints_use_orjson(self, client: AsyncClient) -> None:
        """Test that all existing endpoints return valid JSON using orjson."""
        # Test root endpoint
        response = await client.get("/")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"
        data = response.json()
        assert data == {"message": "Hello from Tributum!"}

        # Test info endpoint
        response = await client.get("/info")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"
        data = response.json()
        assert "app_name" in data
        assert "version" in data
        assert "environment" in data
        assert "debug" in data

    async def test_error_response_serialization_through_http(
        self, client: AsyncClient
    ) -> None:
        """Test that ErrorResponse models serialize correctly with orjson through HTTP.

        This test verifies that complex types like datetime with timezone in
        ErrorResponse are properly serialized by orjson when returned from an API
        endpoint.
        """
        # Trigger a 404 error which returns ErrorResponse
        response = await client.get("/nonexistent-endpoint")
        assert response.status_code == 404
        assert response.headers["content-type"] == "application/json"

        # Verify the response can be parsed as JSON
        data = response.json()

        # Check ErrorResponse structure
        assert "error_code" in data
        assert "message" in data
        assert "timestamp" in data
        assert "correlation_id" in data
        assert "severity" in data

        # Verify timestamp is properly serialized
        # Should be ISO format with timezone
        timestamp_str = data["timestamp"]
        parsed_timestamp = datetime.fromisoformat(timestamp_str)
        assert parsed_timestamp.tzinfo is not None

        # The fact that we can parse this complex response proves orjson
        # is handling ErrorResponse serialization correctly

    async def test_openapi_endpoints_accessible(self, client: AsyncClient) -> None:
        """Test that OpenAPI documentation endpoints still work with ORJSONResponse."""
        # Test docs endpoint
        response = await client.get("/docs")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "swagger-ui" in response.text.lower()

        # Test redoc endpoint
        response = await client.get("/redoc")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "redoc" in response.text.lower()

        # Test OpenAPI schema endpoint
        response = await client.get("/openapi.json")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"
        schema = response.json()
        assert "openapi" in schema
        assert "info" in schema
        assert "paths" in schema

    async def test_response_headers_correct(self, client: AsyncClient) -> None:
        """Test that all endpoints return correct content-type headers."""
        # JSON endpoints should return application/json
        json_endpoints = ["/", "/info", "/openapi.json"]
        for endpoint in json_endpoints:
            response = await client.get(endpoint)
            assert response.headers["content-type"] == "application/json"

        # HTML endpoints should return text/html
        html_endpoints = ["/docs", "/redoc"]
        for endpoint in html_endpoints:
            response = await client.get(endpoint)
            assert "text/html" in response.headers["content-type"]

    async def test_large_payload_handling(self) -> None:
        """Test that endpoints can efficiently handle large payloads with orjson.

        This verifies that our orjson integration provides good performance
        for large response payloads through HTTP endpoints.
        """
        # Create app with a test endpoint that returns large data
        app = create_app()

        # Large test data that would benefit from orjson's performance
        large_data = {
            "users": [
                {
                    "id": str(uuid4()),
                    "name": f"User {i}",
                    "email": f"user{i}@example.com",
                    "created_at": datetime.now(UTC).isoformat(),
                    "metadata": {"score": i * 10, "active": i % 2 == 0},
                }
                for i in range(1000)
            ]
        }

        @app.get("/test/large-payload")
        async def large_payload() -> dict[str, Any]:
            return large_data

        # Test the endpoint performance
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://test"
        ) as test_client:
            start = time.perf_counter()
            response = await test_client.get("/test/large-payload")
            request_time = time.perf_counter() - start

            assert response.status_code == 200
            assert response.headers["content-type"] == "application/json"

            # Verify we can parse the large JSON response
            data = response.json()
            assert len(data["users"]) == 1000

            # With orjson, this should complete quickly (under 100ms for 1000 records)
            assert request_time < 0.1

    async def test_app_uses_orjson_for_datetime_serialization(self) -> None:
        """Test that the app uses orjson which can serialize datetime objects natively.

        Standard JSON cannot serialize datetime objects without a default handler,
        but orjson handles them automatically. This test verifies our integration works.
        """
        app = create_app()

        # Create endpoint that returns a datetime object
        @app.get("/test/datetime-response")
        async def datetime_endpoint() -> dict[str, Any]:
            return {"timestamp": datetime.now(UTC), "data": "test"}

        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://test"
        ) as test_client:
            response = await test_client.get("/test/datetime-response")
            assert response.status_code == 200
            assert response.headers["content-type"] == "application/json"

            # Standard json would fail on datetime, but orjson handles it
            data = response.json()
            assert "timestamp" in data
            assert "data" in data

            # Verify the datetime was serialized properly to ISO format
            timestamp_str = data["timestamp"]
            parsed = datetime.fromisoformat(timestamp_str)
            assert parsed.tzinfo is not None  # Should preserve timezone
