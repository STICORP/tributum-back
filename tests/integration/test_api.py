"""Integration tests for API endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.integration
async def test_root_endpoint(client: AsyncClient) -> None:
    """Test GET / endpoint returns correct response."""
    response = await client.get("/")

    assert response.status_code == 200
    assert response.json() == {"message": "Hello from Tributum!"}


@pytest.mark.integration
async def test_docs_endpoint(client: AsyncClient) -> None:
    """Test GET /docs endpoint is accessible."""
    response = await client.get("/docs")

    assert response.status_code == 200
    assert "swagger-ui" in response.text.lower()


@pytest.mark.integration
async def test_redoc_endpoint(client: AsyncClient) -> None:
    """Test GET /redoc endpoint is accessible."""
    response = await client.get("/redoc")

    assert response.status_code == 200
    assert "redoc" in response.text.lower()


@pytest.mark.integration
async def test_openapi_schema(client: AsyncClient) -> None:
    """Test GET /openapi.json returns valid OpenAPI schema."""
    response = await client.get("/openapi.json")

    assert response.status_code == 200

    schema = response.json()
    assert schema["info"]["title"] == "Tributum"
    assert schema["info"]["version"] == "0.2.0"
    assert "paths" in schema
    assert "/" in schema["paths"]
