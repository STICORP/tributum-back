"""Integration tests for API endpoints."""

import pytest
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

    async def test_disabled_docs_endpoints(self, client_no_docs: AsyncClient) -> None:
        """Test that documentation endpoints return 404 when disabled."""
        # Test disabled Swagger UI
        response = await client_no_docs.get("/docs")
        assert response.status_code == 404

        # Test disabled ReDoc
        response = await client_no_docs.get("/redoc")
        assert response.status_code == 404

        # Test disabled OpenAPI schema
        response = await client_no_docs.get("/openapi.json")
        assert response.status_code == 404

    async def test_health_endpoint(self, client: AsyncClient) -> None:
        """Test GET /health endpoint returns correct response."""
        response = await client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ("healthy", "degraded")
        assert "database" in data

    async def test_health_endpoint_with_real_database(
        self, client_with_db: AsyncClient
    ) -> None:
        """Test /health endpoint with real database connection."""
        response = await client_with_db.get("/health")

        assert response.status_code == 200
        data = response.json()
        # With a real database connection, it should be healthy
        assert data["status"] == "healthy"
        assert data["database"] is True

    async def test_health_endpoint_with_mock_database_failure(
        self, client: AsyncClient, mocker: MockerFixture
    ) -> None:
        """Test /health endpoint when database check fails."""
        # Mock database connection check to return failure
        mock_check = mocker.patch(
            "src.api.main.check_database_connection",
            return_value=(False, "Connection refused"),
        )

        response = await client.get("/health")

        assert response.status_code == 200
        data = response.json()
        # Should be degraded when database is down
        assert data["status"] == "degraded"
        assert data["database"] is False

        # Verify that check_database_connection was called
        mock_check.assert_called_once()

    async def test_info_endpoint(self, client: AsyncClient) -> None:
        """Test GET /info endpoint returns application information."""
        response = await client.get("/info")

        assert response.status_code == 200

        data = response.json()
        # Simplified assertions without pytest_check
        assert "app_name" in data
        assert data["app_name"] == "Tributum"
        assert "version" in data
        assert "environment" in data
        assert data["environment"] == "development"  # Default in test env
        assert "debug" in data
        assert data["debug"] is True  # Default in test env

    @pytest.mark.usefixtures("production_env")
    async def test_info_endpoint_production_env(self, client: AsyncClient) -> None:
        """Test /info endpoint in production environment."""
        response = await client.get("/info")

        assert response.status_code == 200

        data = response.json()
        assert data["environment"] == "production"
        assert data["debug"] is False  # Should be False in production
