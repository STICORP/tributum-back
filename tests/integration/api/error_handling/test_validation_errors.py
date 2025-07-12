"""Integration tests for request validation error handling."""

import pytest
from httpx import AsyncClient

from src.core.exceptions import ErrorCode


@pytest.mark.integration
class TestRequestValidationError:
    """Test handling of FastAPI RequestValidationError."""

    async def test_request_validation_error(self, async_client: AsyncClient) -> None:
        """Test request validation error returns 422 with field details."""
        response = await async_client.post(
            "/test/request-validation",
            json={"data": "not-a-dict"},  # Should be dict[str, int]
        )

        assert response.status_code == 422

        data = response.json()
        assert data["error_code"] == ErrorCode.VALIDATION_ERROR.value
        assert data["message"] == "Request validation failed"
        assert "validation_errors" in data["details"]
        assert data["severity"] == "LOW"

    async def test_missing_required_field(self, async_client: AsyncClient) -> None:
        """Test missing required field in request."""
        response = await async_client.post("/test/request-validation", json={})

        assert response.status_code == 422

        data = response.json()
        assert "validation_errors" in data["details"]
        # Field errors should be grouped
        assert isinstance(data["details"]["validation_errors"], dict)

    async def test_root_validation_error(self, async_client: AsyncClient) -> None:
        """Test validation error at root level (no specific field)."""
        # Send request that triggers root validation error
        response = await async_client.post(
            "/test/root-validation",
            json={"value1": 60, "value2": 50},  # Sum = 110, exceeds limit
        )

        assert response.status_code == 422

        data = response.json()
        assert data["error_code"] == ErrorCode.VALIDATION_ERROR.value
        assert "validation_errors" in data["details"]
        # Root validation errors should be under "root" field
        assert "root" in data["details"]["validation_errors"]
