"""Security tests for error handling - ensuring sensitive data is not exposed."""

import pytest
from httpx import AsyncClient


@pytest.mark.integration
class TestErrorHandlingSecurity:
    """Test security aspects of error handling."""

    async def test_error_context_sanitization_in_response(
        self, async_client: AsyncClient
    ) -> None:
        """Ensure sensitive data is sanitized in error responses."""
        # Test endpoint that raises an error with sensitive context
        response = await async_client.get("/test/sensitive-context")

        assert response.status_code == 400
        response_data = response.json()

        # Verify sensitive fields are redacted
        assert response_data["details"]["password"] == "[REDACTED]"
        assert response_data["details"]["api_key"] == "[REDACTED]"
        assert response_data["details"]["token"] == "[REDACTED]"

        # Verify non-sensitive fields are preserved
        assert response_data["details"]["username"] == "john_doe"
        assert response_data["details"]["error"] == "Invalid credentials"

        # Ensure raw values don't appear anywhere in response
        response_text = response.text
        assert "secret123" not in response_text
        assert "sk-12345-abcdef" not in response_text
        assert "jwt.token.here" not in response_text

    async def test_nested_sensitive_data_sanitization(
        self, async_client: AsyncClient
    ) -> None:
        """Test that nested sensitive data structures are sanitized."""
        response = await async_client.get("/test/nested-sensitive-context")

        assert response.status_code == 422  # BusinessRuleError
        response_data = response.json()

        # Check user nested data
        user_data = response_data["details"]["user"]
        assert user_data["password"] == "[REDACTED]"
        assert user_data["api_key"] == "[REDACTED]"
        assert user_data["email"] == "test@example.com"  # Not sensitive
        assert user_data["id"] == 123  # Not sensitive

        # Check payment nested data
        payment_data = response_data["details"]["payment"]
        assert payment_data["card_number"] == "[REDACTED]"
        assert payment_data["cvv"] == "[REDACTED]"
        assert payment_data["amount"] == 100.50  # Not sensitive
        assert payment_data["currency"] == "USD"  # Not sensitive

        # Check merchant nested data
        merchant_data = response_data["details"]["merchant"]
        assert merchant_data["secret_key"] == "[REDACTED]"
        assert merchant_data["id"] == "merchant_123"  # Not sensitive

        # Ensure raw sensitive values don't appear in response
        response_text = response.text
        assert "hashed_password_here" not in response_text
        assert "4111111111111111" not in response_text
        assert "merchant_secret_key" not in response_text

    async def test_debug_info_sanitization_in_development(
        self, async_client: AsyncClient, development_env: None
    ) -> None:
        """Ensure debug info also sanitizes sensitive data in development mode."""
        _ = development_env  # Ensure environment fixture runs first

        response = await async_client.get("/test/sensitive-context")
        response_data = response.json()

        # In development, debug_info should be present
        assert response_data.get("debug_info") is not None

        # Check that error_context in debug_info is also sanitized
        debug_context = response_data["debug_info"]["error_context"]
        assert debug_context["password"] == "[REDACTED]"
        assert debug_context["api_key"] == "[REDACTED]"
        assert debug_context["token"] == "[REDACTED]"

        # Non-sensitive data should be preserved
        assert debug_context["username"] == "john_doe"
        assert debug_context["error"] == "Invalid credentials"

    async def test_validation_error_non_sensitive_context(
        self, async_client: AsyncClient
    ) -> None:
        """Test that non-sensitive validation errors are not redacted."""
        response = await async_client.get("/test/validation-error")

        assert response.status_code == 400
        response_data = response.json()

        # Original test endpoint context should not be redacted
        assert response_data["details"]["field"] == "email"
        assert response_data["details"]["value"] == "not-an-email"
        assert "[REDACTED]" not in response.text

    async def test_production_mode_no_debug_info(
        self, async_client_production: AsyncClient
    ) -> None:
        """Ensure debug info is not exposed in production mode."""
        # Using async_client_production fixture which creates app with
        # production settings
        response = await async_client_production.get("/test/sensitive-context")
        response_data = response.json()

        # In production, debug_info should be None
        assert response_data.get("debug_info") is None

        # Details should still be sanitized
        assert response_data["details"]["password"] == "[REDACTED]"
        assert response_data["details"]["api_key"] == "[REDACTED]"
        assert response_data["details"]["token"] == "[REDACTED]"

        # Verify error structure is still complete
        assert "error_code" in response_data
        assert "message" in response_data
        assert "severity" in response_data
        assert "correlation_id" in response_data
