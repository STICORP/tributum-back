"""Integration tests for API endpoints."""

import pytest
import pytest_check
from httpx import AsyncClient
from pytest_mock import MockerFixture


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
        data = response.json()
        assert data["status"] in ("healthy", "degraded")
        assert "database" in data

    async def test_health_endpoint_with_mock_database(
        self, client: AsyncClient, mocker: MockerFixture
    ) -> None:
        """Test /health endpoint with mock database ensuring scalar() is called."""
        # Mock database connection check to return success
        mock_check = mocker.patch(
            "src.api.main.check_database_connection", return_value=(True, None)
        )

        response = await client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["database"] is True

        # Verify that check_database_connection was called
        mock_check.assert_called_once()

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
