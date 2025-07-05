"""Integration tests for HTTP exception handling."""

import pytest
from httpx import AsyncClient

from src.core.exceptions import ErrorCode


@pytest.mark.integration
class TestHTTPException:
    """Test handling of Starlette HTTPException."""

    async def test_http_exception(self, async_client: AsyncClient) -> None:
        """Test HTTPException is converted to our error format."""
        response = await async_client.get("/test/http-exception")

        assert response.status_code == 403

        data = response.json()
        assert data["error_code"] == ErrorCode.INTERNAL_ERROR.value
        assert data["message"] == "Access forbidden"
        assert "correlation_id" in data
        assert "timestamp" in data
        assert "service_info" in data

    async def test_http_400_bad_request(self, async_client: AsyncClient) -> None:
        """Test HTTPException with 400 status maps to VALIDATION_ERROR."""
        response = await async_client.get("/test/http-400")

        assert response.status_code == 400

        data = response.json()
        assert data["error_code"] == ErrorCode.VALIDATION_ERROR.value
        assert data["message"] == "Bad request data"
        assert data["severity"] == "LOW"

    async def test_http_401_unauthorized(self, async_client: AsyncClient) -> None:
        """Test HTTPException with 401 status maps to UNAUTHORIZED."""
        response = await async_client.get("/test/http-401")

        assert response.status_code == 401

        data = response.json()
        assert data["error_code"] == ErrorCode.UNAUTHORIZED.value
        assert data["message"] == "Authentication required"
        assert data["severity"] == "HIGH"

    async def test_http_404_not_found(self, async_client: AsyncClient) -> None:
        """Test HTTPException with 404 status maps to NOT_FOUND."""
        response = await async_client.get("/test/http-404")

        assert response.status_code == 404

        data = response.json()
        assert data["error_code"] == ErrorCode.NOT_FOUND.value
        assert data["message"] == "Resource not found"
        assert data["severity"] == "LOW"

    async def test_http_500_server_error(self, async_client: AsyncClient) -> None:
        """Test HTTPException with 500+ status has HIGH severity."""
        response = await async_client.get("/test/http-500")

        assert response.status_code == 500

        data = response.json()
        assert data["error_code"] == ErrorCode.INTERNAL_ERROR.value
        assert data["message"] == "Server error occurred"
        assert data["severity"] == "HIGH"

    async def test_http_503_service_unavailable(
        self, async_client: AsyncClient
    ) -> None:
        """Test HTTPException with 503 status (5xx) has HIGH severity."""
        response = await async_client.get("/test/http-503")

        assert response.status_code == 503

        data = response.json()
        assert data["error_code"] == ErrorCode.INTERNAL_ERROR.value
        assert data["message"] == "Service temporarily unavailable"
        assert data["severity"] == "HIGH"
