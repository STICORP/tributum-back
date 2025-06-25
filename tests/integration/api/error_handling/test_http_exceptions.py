"""Integration tests for HTTP exception handling."""

import pytest
from fastapi import FastAPI, HTTPException, status
from fastapi.testclient import TestClient

from src.core.exceptions import ErrorCode


@pytest.mark.integration
class TestHTTPException:
    """Test handling of Starlette HTTPException."""

    def test_http_exception(self, client: TestClient) -> None:
        """Test HTTPException is converted to our error format."""
        response = client.get("/test/http-exception")

        assert response.status_code == 403

        data = response.json()
        assert data["error_code"] == ErrorCode.INTERNAL_ERROR.value
        assert data["message"] == "Access forbidden"
        assert "correlation_id" in data
        assert "timestamp" in data
        assert "service_info" in data

    def test_http_400_bad_request(self, app_with_handlers: FastAPI) -> None:
        """Test HTTPException with 400 status maps to VALIDATION_ERROR."""

        @app_with_handlers.get("/test/http-400")
        async def raise_http_400() -> None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Bad request data"
            )

        client = TestClient(app_with_handlers)
        response = client.get("/test/http-400")

        assert response.status_code == 400

        data = response.json()
        assert data["error_code"] == ErrorCode.VALIDATION_ERROR.value
        assert data["message"] == "Bad request data"
        assert data["severity"] == "LOW"

    def test_http_401_unauthorized(self, app_with_handlers: FastAPI) -> None:
        """Test HTTPException with 401 status maps to UNAUTHORIZED."""

        @app_with_handlers.get("/test/http-401")
        async def raise_http_401() -> None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )

        client = TestClient(app_with_handlers)
        response = client.get("/test/http-401")

        assert response.status_code == 401

        data = response.json()
        assert data["error_code"] == ErrorCode.UNAUTHORIZED.value
        assert data["message"] == "Authentication required"
        assert data["severity"] == "HIGH"

    def test_http_404_not_found(self, app_with_handlers: FastAPI) -> None:
        """Test HTTPException with 404 status maps to NOT_FOUND."""

        @app_with_handlers.get("/test/http-404")
        async def raise_http_404() -> None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found"
            )

        client = TestClient(app_with_handlers)
        response = client.get("/test/http-404")

        assert response.status_code == 404

        data = response.json()
        assert data["error_code"] == ErrorCode.NOT_FOUND.value
        assert data["message"] == "Resource not found"
        assert data["severity"] == "LOW"

    def test_http_500_server_error(self, app_with_handlers: FastAPI) -> None:
        """Test HTTPException with 500+ status has HIGH severity."""

        @app_with_handlers.get("/test/http-500")
        async def raise_http_500() -> None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Server error occurred",
            )

        client = TestClient(app_with_handlers)
        response = client.get("/test/http-500")

        assert response.status_code == 500

        data = response.json()
        assert data["error_code"] == ErrorCode.INTERNAL_ERROR.value
        assert data["message"] == "Server error occurred"
        assert data["severity"] == "HIGH"

    def test_http_503_service_unavailable(self, app_with_handlers: FastAPI) -> None:
        """Test HTTPException with 503 status (5xx) has HIGH severity."""

        @app_with_handlers.get("/test/http-503")
        async def raise_http_503() -> None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service temporarily unavailable",
            )

        client = TestClient(app_with_handlers)
        response = client.get("/test/http-503")

        assert response.status_code == 503

        data = response.json()
        assert data["error_code"] == ErrorCode.INTERNAL_ERROR.value
        assert data["message"] == "Service temporarily unavailable"
        assert data["severity"] == "HIGH"
