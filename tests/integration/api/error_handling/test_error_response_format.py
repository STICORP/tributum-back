"""Integration tests for error response format and sanitization."""

import pytest
from fastapi.testclient import TestClient

from src.api.schemas.errors import ErrorResponse


@pytest.mark.integration
class TestErrorResponseFormat:
    """Test the error response format and fields."""

    def test_all_fields_present(self, client: TestClient) -> None:
        """Test that all expected fields are present in error response."""
        response = client.get("/test/validation-error")

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

    def test_timestamp_format(self, client: TestClient) -> None:
        """Test that timestamp is in ISO format with timezone."""
        response = client.get("/test/validation-error")

        data = response.json()
        timestamp = data["timestamp"]

        # Should be ISO format with timezone
        assert "T" in timestamp  # Date-time separator
        assert "+" in timestamp or "Z" in timestamp  # Timezone indicator

    def test_correlation_id_present(self, client: TestClient) -> None:
        """Test that correlation ID is included in error responses."""
        # Send request with correlation ID
        correlation_id = "test-correlation-123"
        response = client.get(
            "/test/validation-error",
            headers={"X-Correlation-ID": correlation_id},
        )

        data = response.json()
        assert data["correlation_id"] == correlation_id

    def test_error_response_model_validation(self) -> None:
        """Test that ErrorResponse model validates correctly."""
        # This ensures our error responses match the schema
        error = ErrorResponse(
            error_code="TEST_ERROR",
            message="Test message",
            details={"key": "value"},
            correlation_id="123",
            severity="HIGH",
        )

        # Should serialize without errors
        data = error.model_dump(mode="json")
        assert data["error_code"] == "TEST_ERROR"
        assert isinstance(data["timestamp"], str)
