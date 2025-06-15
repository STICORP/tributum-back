"""Tests for error response models."""

import json
from datetime import UTC, datetime
from typing import Any

import pytest
from pydantic import ValidationError

from src.api.schemas.errors import ErrorResponse, ServiceInfo


class TestServiceInfo:
    """Test cases for the ServiceInfo model."""

    def test_service_info_creation(self) -> None:
        """Test ServiceInfo creation with all fields."""
        service_info = ServiceInfo(
            name="Tributum",
            version="0.1.0",
            environment="production",
        )

        assert service_info.name == "Tributum"
        assert service_info.version == "0.1.0"
        assert service_info.environment == "production"

    def test_service_info_json_serialization(self) -> None:
        """Test ServiceInfo JSON serialization."""
        service_info = ServiceInfo(
            name="PaymentService",
            version="2.1.3",
            environment="staging",
        )

        json_data = json.loads(service_info.model_dump_json())
        assert json_data == {
            "name": "PaymentService",
            "version": "2.1.3",
            "environment": "staging",
        }

    def test_service_info_missing_required_fields(self) -> None:
        """Test that ServiceInfo requires all fields."""
        with pytest.raises(ValidationError) as exc_info:
            ServiceInfo.model_validate({"name": "Tributum"})

        errors = exc_info.value.errors()
        assert len(errors) == 2  # Missing version and environment
        error_fields = {error["loc"][0] for error in errors}
        assert error_fields == {"version", "environment"}


class TestErrorResponse:
    """Test cases for the ErrorResponse model."""

    def test_error_response_with_required_fields_only(self) -> None:
        """Test ErrorResponse creation with only required fields."""
        error = ErrorResponse(
            error_code="TEST_ERROR",
            message="This is a test error",
        )

        assert error.error_code == "TEST_ERROR"
        assert error.message == "This is a test error"
        assert error.details is None
        assert error.correlation_id is None
        assert error.severity is None
        assert error.service_info is None
        assert isinstance(error.timestamp, datetime)
        assert error.timestamp.tzinfo is not None  # Ensure it has timezone info

    def test_error_response_with_all_fields(self) -> None:
        """Test ErrorResponse creation with all fields."""
        error = ErrorResponse(
            error_code="VALIDATION_ERROR",
            message="Invalid input",
            details={"field": "email", "reason": "Invalid format"},
            correlation_id="550e8400-e29b-41d4-a716-446655440000",
        )

        assert error.error_code == "VALIDATION_ERROR"
        assert error.message == "Invalid input"
        assert error.details == {"field": "email", "reason": "Invalid format"}
        assert error.correlation_id == "550e8400-e29b-41d4-a716-446655440000"

    def test_error_response_missing_required_field_error_code(self) -> None:
        """Test that ErrorResponse requires error_code field."""
        with pytest.raises(ValidationError) as exc_info:
            ErrorResponse.model_validate({"message": "Missing error code"})

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("error_code",)
        assert errors[0]["type"] == "missing"

    def test_error_response_missing_required_field_message(self) -> None:
        """Test that ErrorResponse requires message field."""
        with pytest.raises(ValidationError) as exc_info:
            ErrorResponse.model_validate({"error_code": "TEST_ERROR"})

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("message",)
        assert errors[0]["type"] == "missing"

    def test_error_response_json_serialization(self) -> None:
        """Test ErrorResponse JSON serialization."""
        error = ErrorResponse(
            error_code="NOT_FOUND",
            message="Resource not found",
            correlation_id="test-correlation-id",
        )

        json_str = error.model_dump_json()
        json_data = json.loads(json_str)

        assert json_data["error_code"] == "NOT_FOUND"
        assert json_data["message"] == "Resource not found"
        assert json_data["details"] is None
        assert json_data["correlation_id"] == "test-correlation-id"

    def test_error_response_dict_serialization_excludes_none(self) -> None:
        """Test ErrorResponse dict serialization with exclude_none option."""
        error = ErrorResponse(
            error_code="INTERNAL_ERROR",
            message="Something went wrong",
        )

        # Without exclude_none
        dict_with_none = error.model_dump()
        assert "details" in dict_with_none
        assert "correlation_id" in dict_with_none
        assert "severity" in dict_with_none
        assert "service_info" in dict_with_none
        assert "timestamp" in dict_with_none  # Always present due to default factory

        # With exclude_none
        dict_without_none = error.model_dump(exclude_none=True)
        assert "details" not in dict_without_none
        assert "correlation_id" not in dict_without_none
        assert "severity" not in dict_without_none
        assert "service_info" not in dict_without_none
        assert "timestamp" in dict_without_none  # Still present because it has a value
        assert dict_without_none["error_code"] == "INTERNAL_ERROR"
        assert dict_without_none["message"] == "Something went wrong"
        assert isinstance(dict_without_none["timestamp"], datetime)

    def test_error_response_with_complex_details(self) -> None:
        """Test ErrorResponse with complex nested details."""
        complex_details = {
            "validation_errors": [
                {"field": "email", "reason": "Invalid format"},
                {"field": "password", "reason": "Too short"},
            ],
            "timestamp": "2024-06-14T12:00:00",
            "request_id": "req-123",
        }

        error = ErrorResponse(
            error_code="VALIDATION_ERROR",
            message="Multiple validation errors",
            details=complex_details,
        )

        assert error.details == complex_details
        assert error.details["validation_errors"][0]["field"] == "email"
        assert len(error.details["validation_errors"]) == 2

    def test_error_response_model_config_examples(self) -> None:
        """Test that model config contains proper examples."""
        schema = ErrorResponse.model_json_schema()
        examples = schema.get("examples", [])

        assert len(examples) == 3

        # Check first example (validation error with details)
        assert examples[0]["error_code"] == "VALIDATION_ERROR"
        assert "details" in examples[0]
        assert "correlation_id" in examples[0]
        assert "timestamp" in examples[0]
        assert "severity" in examples[0]
        assert "service_info" in examples[0]

        # Check second example (not found with correlation ID)
        assert examples[1]["error_code"] == "NOT_FOUND"
        assert "correlation_id" in examples[1]
        assert "timestamp" in examples[1]
        assert "severity" in examples[1]
        assert "service_info" in examples[1]

        # Check third example (unauthorized, minimal)
        assert examples[2]["error_code"] == "UNAUTHORIZED"
        assert "details" not in examples[2]
        assert "timestamp" in examples[2]
        assert "severity" in examples[2]
        # This example doesn't include service_info
        assert "service_info" not in examples[2]

    def test_error_response_from_dict(self) -> None:
        """Test creating ErrorResponse from dictionary."""
        error_dict: dict[str, Any] = {
            "error_code": "BUSINESS_RULE_ERROR",
            "message": "Cannot process empty order",
            "details": {"order_items": 0},
        }

        error = ErrorResponse(**error_dict)

        assert error.error_code == "BUSINESS_RULE_ERROR"
        assert error.message == "Cannot process empty order"
        assert error.details == {"order_items": 0}

    def test_error_response_field_descriptions(self) -> None:
        """Test that fields have proper descriptions."""
        schema = ErrorResponse.model_json_schema()
        properties = schema["properties"]

        assert "description" in properties["error_code"]
        assert "description" in properties["message"]
        assert "description" in properties["details"]
        assert "description" in properties["correlation_id"]
        assert "description" in properties["timestamp"]
        assert "description" in properties["severity"]
        assert "description" in properties["service_info"]

        # Check that examples are included
        assert "examples" in properties["error_code"]
        assert "examples" in properties["message"]

    def test_error_response_timestamp_serialization(self) -> None:
        """Test that timestamp serializes to ISO format with timezone."""
        error = ErrorResponse(
            error_code="TEST_ERROR",
            message="Test message",
        )

        json_str = error.model_dump_json()
        json_data = json.loads(json_str)

        # Check timestamp format (ISO with timezone)
        timestamp_str = json_data["timestamp"]
        assert "T" in timestamp_str  # ISO format
        assert "+" in timestamp_str or "Z" in timestamp_str  # Has timezone

        # Verify it can be parsed back
        parsed_timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        assert parsed_timestamp.tzinfo is not None

    def test_error_response_with_severity(self) -> None:
        """Test ErrorResponse with severity field."""
        error = ErrorResponse(
            error_code="CRITICAL_ERROR",
            message="Critical system error",
            severity="CRITICAL",
        )

        assert error.severity == "CRITICAL"

        # Test JSON serialization includes severity
        json_data = json.loads(error.model_dump_json())
        assert json_data["severity"] == "CRITICAL"

    def test_error_response_custom_timestamp(self) -> None:
        """Test ErrorResponse with custom timestamp."""
        custom_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
        error = ErrorResponse(
            error_code="TEST_ERROR",
            message="Test message",
            timestamp=custom_time,
        )

        assert error.timestamp == custom_time
        json_str = error.model_dump_json()
        assert "2024-01-01T12:00:00" in json_str

    def test_error_response_with_service_info(self) -> None:
        """Test ErrorResponse with service_info field."""
        service_info = ServiceInfo(
            name="Tributum",
            version="0.1.0",
            environment="production",
        )

        error = ErrorResponse(
            error_code="SYSTEM_ERROR",
            message="System error occurred",
            service_info=service_info,
        )

        assert error.service_info is not None
        assert error.service_info.name == "Tributum"
        assert error.service_info.version == "0.1.0"
        assert error.service_info.environment == "production"

        # Test JSON serialization includes nested service_info
        json_data = json.loads(error.model_dump_json())
        assert json_data["service_info"]["name"] == "Tributum"
        assert json_data["service_info"]["version"] == "0.1.0"
        assert json_data["service_info"]["environment"] == "production"
