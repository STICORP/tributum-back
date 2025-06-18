"""Integration tests for ORJSONResponse in FastAPI."""

import json
import time
from datetime import UTC, datetime
from uuid import uuid4

import orjson
import pytest
from httpx import ASGITransport, AsyncClient

from src.api.main import create_app
from src.api.schemas.errors import ErrorResponse


@pytest.mark.integration
async def test_all_endpoints_use_orjson(client: AsyncClient) -> None:
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


@pytest.mark.integration
async def test_error_response_serialization() -> None:
    """Test that ErrorResponse models serialize correctly with orjson."""
    # Create an error response with timestamp
    error = ErrorResponse(
        error_code="TEST_ERROR",
        message="Test error message",
        details={"field": "test_field", "reason": "invalid"},
        correlation_id=str(uuid4()),
        severity="ERROR",
        timestamp=datetime.now(UTC),
    )

    # Create a test app that returns the error
    app = create_app()

    @app.get("/test-error", response_model=ErrorResponse)
    async def test_error() -> ErrorResponse:
        return error

    # Test the endpoint
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/test-error")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"

        # Verify the response can be parsed as JSON
        data = response.json()
        assert data["error_code"] == "TEST_ERROR"
        assert data["message"] == "Test error message"
        assert data["details"] == {"field": "test_field", "reason": "invalid"}
        assert "correlation_id" in data
        assert data["severity"] == "ERROR"
        assert "timestamp" in data

        # Verify timestamp is properly serialized
        # Should be ISO format with timezone
        timestamp_str = data["timestamp"]
        parsed_timestamp = datetime.fromisoformat(timestamp_str)
        assert parsed_timestamp.tzinfo is not None


@pytest.mark.integration
async def test_openapi_endpoints_accessible(client: AsyncClient) -> None:
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


@pytest.mark.integration
async def test_response_headers_correct(client: AsyncClient) -> None:
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


@pytest.mark.integration
async def test_orjson_performance_improvement() -> None:
    """Test that ORJSONResponse provides performance improvement over standard JSON."""
    # Create a large test data structure
    test_data = {
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

    # Time standard json encoding

    start = time.perf_counter()
    for _ in range(100):
        json.dumps(test_data, default=str)
    json_time = time.perf_counter() - start

    # Time orjson encoding
    start = time.perf_counter()
    for _ in range(100):
        orjson.dumps(test_data)
    orjson_time = time.perf_counter() - start

    # orjson should be faster
    assert orjson_time < json_time
    # Expect at least 2x improvement for this data structure
    assert orjson_time * 2 < json_time


@pytest.mark.integration
async def test_app_uses_orjson_response_class() -> None:
    """Test that the FastAPI app is configured to use ORJSONResponse by default."""
    app = create_app()

    # Add a test endpoint that returns a response
    @app.get("/test-response-class")
    async def test_endpoint() -> dict[str, str]:
        return {"test": "data"}

    # Make a request and verify it uses ORJSONResponse
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/test-response-class")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"
        # The response should be properly serialized by orjson
        assert response.json() == {"test": "data"}
