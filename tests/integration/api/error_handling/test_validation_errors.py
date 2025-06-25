"""Integration tests for request validation error handling."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel, model_validator

from src.core.exceptions import ErrorCode


@pytest.mark.integration
class TestRequestValidationError:
    """Test handling of FastAPI RequestValidationError."""

    def test_request_validation_error(self, client: TestClient) -> None:
        """Test request validation error returns 422 with field details."""
        response = client.post(
            "/test/request-validation",
            json={"data": "not-a-dict"},  # Should be dict[str, int]
        )

        assert response.status_code == 422

        data = response.json()
        assert data["error_code"] == ErrorCode.VALIDATION_ERROR.value
        assert data["message"] == "Request validation failed"
        assert "validation_errors" in data["details"]
        assert data["severity"] == "LOW"

    def test_missing_required_field(self, client: TestClient) -> None:
        """Test missing required field in request."""
        response = client.post("/test/request-validation", json={})

        assert response.status_code == 422

        data = response.json()
        assert "validation_errors" in data["details"]
        # Field errors should be grouped
        assert isinstance(data["details"]["validation_errors"], dict)

    def test_root_validation_error(
        self, app_with_handlers: FastAPI, client: TestClient
    ) -> None:
        """Test validation error at root level (no specific field)."""
        # Create an endpoint that has root-level validation

        class RootValidationModel(BaseModel):
            value1: int
            value2: int

            @model_validator(mode="after")
            def check_sum(self) -> "RootValidationModel":
                if self.value1 + self.value2 > 100:
                    raise ValueError("Sum must not exceed 100")
                return self

        @app_with_handlers.post("/test/root-validation")
        async def root_validation_endpoint(body: RootValidationModel) -> dict[str, int]:
            return {"sum": body.value1 + body.value2}

        # Send request that triggers root validation error
        response = client.post(
            "/test/root-validation",
            json={"value1": 60, "value2": 50},  # Sum = 110, exceeds limit
        )

        assert response.status_code == 422

        data = response.json()
        assert data["error_code"] == ErrorCode.VALIDATION_ERROR.value
        assert "validation_errors" in data["details"]
        # Root validation errors should be under "root" field
        assert "root" in data["details"]["validation_errors"]
