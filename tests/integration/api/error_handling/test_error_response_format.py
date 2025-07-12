"""Integration tests for error response format and sanitization."""

import pytest
from httpx import AsyncClient

from src.api.schemas.errors import ErrorResponse


@pytest.mark.integration
class TestErrorResponseFormat:
    """Test the error response format and fields."""

    async def test_all_fields_present(self, async_client: AsyncClient) -> None:
        """Test that all expected fields are present in error response."""
        response = await async_client.get("/test/validation-error")

        data = response.json()

        # Required fields
        assert "error_code" in data
        assert "message" in data
        assert "timestamp" in data

        # Optional fields that should be present
        assert "details" in data
        assert "correlation_id" in data
        assert "severity" in data
        assert "service_info" in data

        # Service info structure
        service_info = data["service_info"]
        assert "name" in service_info
        assert "version" in service_info
        assert "environment" in service_info

    async def test_timestamp_format(self, async_client: AsyncClient) -> None:
        """Test that timestamp is in ISO format with timezone."""
        response = await async_client.get("/test/validation-error")

        data = response.json()
        timestamp = data["timestamp"]

        # Should be ISO format with timezone
        assert "T" in timestamp  # Date-time separator
        assert "+" in timestamp or "Z" in timestamp  # Timezone indicator

    async def test_correlation_id_present(self, async_client: AsyncClient) -> None:
        """Test that correlation ID is included in error responses."""
        # Send request with correlation ID
        correlation_id = "test-correlation-123"
        response = await async_client.get(
            "/test/validation-error",
            headers={"X-Correlation-ID": correlation_id},
        )

        data = response.json()
        assert data["correlation_id"] == correlation_id

    async def test_correlation_id_generated_when_missing(
        self, async_client: AsyncClient
    ) -> None:
        """Test that a correlation ID is generated when not provided."""
        # Send request without correlation ID
        response = await async_client.get("/test/validation-error")

        data = response.json()
        # Should have a generated correlation ID
        assert "correlation_id" in data
        assert data["correlation_id"] is not None
        assert len(data["correlation_id"]) > 0

    async def test_different_error_types_have_correct_format(
        self, async_client: AsyncClient
    ) -> None:
        """Test that different error types all follow the same format."""
        endpoints = [
            "/test/validation-error",
            "/test/not-found",
            "/test/unauthorized",
            "/test/business-rule",
        ]

        for endpoint in endpoints:
            response = await async_client.get(endpoint)
            data = response.json()

            # All errors should have the same base structure
            assert "error_code" in data
            assert "message" in data
            assert "timestamp" in data
            assert "correlation_id" in data
            assert "severity" in data
            assert "service_info" in data

    async def test_error_response_matches_schema(
        self, async_client: AsyncClient
    ) -> None:
        """Test that actual API error responses match the ErrorResponse schema."""
        response = await async_client.get("/test/validation-error")

        # Get the response data
        data = response.json()

        # Verify it can be parsed by our ErrorResponse model
        # This tests the integration between API responses and our schema
        error_response = ErrorResponse(**data)

        # Verify the parsed model has the expected structure
        assert error_response.error_code == "VALIDATION_ERROR"
        assert error_response.message == "Email format is invalid"
        assert error_response.severity is not None
        assert error_response.timestamp is not None
