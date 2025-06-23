"""Integration tests for API endpoints."""

import pytest
import pytest_check
from httpx import AsyncClient


@pytest.mark.integration
class TestAPIEndpoints:
    """Test API endpoints integration."""

    async def test_root_endpoint(self, client: AsyncClient) -> None:
        """Test GET / endpoint returns correct response."""
        response = await client.get("/")

        assert response.status_code == 200
        assert response.json() == {"message": "Hello from Tributum!"}

    async def test_docs_endpoint(self, client: AsyncClient) -> None:
        """Test GET /docs endpoint is accessible."""
        response = await client.get("/docs")

        assert response.status_code == 200
        assert "swagger-ui" in response.text.lower()

    async def test_redoc_endpoint(self, client: AsyncClient) -> None:
        """Test GET /redoc endpoint is accessible."""
        response = await client.get("/redoc")

        assert response.status_code == 200
        assert "redoc" in response.text.lower()

    async def test_openapi_schema(self, client: AsyncClient) -> None:
        """Test GET /openapi.json returns valid OpenAPI schema."""
        response = await client.get("/openapi.json")

        assert response.status_code == 200

        schema = response.json()
        assert schema["info"]["title"] == "Tributum"
        assert schema["info"]["version"]  # Just verify version exists
        assert "paths" in schema
        assert "/" in schema["paths"]

    async def test_health_endpoint(self, client: AsyncClient) -> None:
        """Test GET /health endpoint returns correct response."""
        response = await client.get("/health")

        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}

    async def test_info_endpoint(self, client: AsyncClient) -> None:
        """Test GET /info endpoint returns application information."""
        response = await client.get("/info")

        assert response.status_code == 200

        data = response.json()
        with pytest_check.check:
            assert "app_name" in data
        with pytest_check.check:
            assert data["app_name"] == "Tributum"
        with pytest_check.check:
            assert "version" in data
        with pytest_check.check:
            assert "environment" in data
        with pytest_check.check:
            assert "debug" in data
