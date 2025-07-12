"""Integration tests for TributumError handling."""

import pytest
from httpx import AsyncClient

from src.core.config import get_settings
from src.core.exceptions import ErrorCode, Severity


@pytest.mark.integration
class TestTributumErrorHandling:
    """Test handling of TributumError and its subclasses."""

    async def test_validation_error(self, async_client: AsyncClient) -> None:
        """Test ValidationError returns 400 with proper format."""
        response = await async_client.get("/test/validation-error")

        assert response.status_code == 400

        data = response.json()
        assert data["error_code"] == ErrorCode.VALIDATION_ERROR.value
        assert data["message"] == "Email format is invalid"
        assert data["details"]["field"] == "email"
        assert data["details"]["value"] == "not-an-email"
        assert data["severity"] == Severity.LOW.value
        assert "correlation_id" in data
        assert "request_id" in data
        assert data["request_id"].startswith("req-")
        assert "timestamp" in data
        assert "service_info" in data

    async def test_not_found_error(self, async_client: AsyncClient) -> None:
        """Test NotFoundError returns 404 with proper format."""
        response = await async_client.get("/test/not-found")

        assert response.status_code == 404

        data = response.json()
        assert data["error_code"] == ErrorCode.NOT_FOUND.value
        assert data["message"] == "User not found"
        assert data["details"]["user_id"] == 123
        assert data["severity"] == Severity.LOW.value

    async def test_unauthorized_error(self, async_client: AsyncClient) -> None:
        """Test UnauthorizedError returns 401 with proper format."""
        response = await async_client.get("/test/unauthorized")

        assert response.status_code == 401

        data = response.json()
        assert data["error_code"] == ErrorCode.UNAUTHORIZED.value
        assert data["message"] == "Invalid API key"
        assert data["severity"] == Severity.HIGH.value

    async def test_business_rule_error(self, async_client: AsyncClient) -> None:
        """Test BusinessRuleError returns 422 with proper format."""
        response = await async_client.get("/test/business-rule")

        assert response.status_code == 422

        data = response.json()
        assert data["error_code"] == ErrorCode.INTERNAL_ERROR.value
        assert data["message"] == "Insufficient balance"
        assert data["details"]["required"] == 100
        assert data["details"]["available"] == 50
        assert data["severity"] == Severity.MEDIUM.value


@pytest.mark.integration
class TestTributumErrorWithCause:
    """Test handling of TributumError with a cause."""

    @pytest.mark.usefixtures("development_env")
    async def test_tributum_error_with_cause_in_debug_info(
        self, async_client: AsyncClient
    ) -> None:
        """Test that exception cause is included in debug info."""
        # Note: development_env fixture ensures we're in development mode
        # The test endpoint is already defined in conftest.py
        response = await async_client.get("/test/error-with-cause")

        assert response.status_code == 400

        data = response.json()

        # Check current environment
        settings = get_settings()
        assert settings.environment == "development", (
            f"Expected development, got {settings.environment}"
        )

        # We're in development mode by default, so debug_info should include cause
        assert "debug_info" in data
        debug_info = data["debug_info"]
        assert debug_info is not None, f"debug_info should not be None, got: {data}"
        assert "exception_type" in debug_info
        assert debug_info["exception_type"] == "ValidationError"

        # Now the cause should be included since we passed it to the constructor
        assert "cause" in debug_info
        assert debug_info["cause"]["type"] == "ValueError"
        assert "invalid literal for int()" in debug_info["cause"]["message"]
