"""Unit tests for API error response schemas.

This module tests all aspects of the error response schema models including:
- ServiceInfo model creation, validation, and serialization
- ErrorResponse model with all fields and behaviors
- Field validation and type checking
- JSON serialization/deserialization
- Thread safety of model creation
- FastAPI compatibility and OpenAPI schema generation
"""

import json
import threading
from datetime import UTC, datetime
from typing import Any

import pytest
from pydantic import ValidationError
from pytest_mock import MockerFixture

from src.api.schemas.errors import ErrorResponse, ServiceInfo


@pytest.mark.unit
class TestErrorSchemas:
    """Test suite for error response schema models."""

    # ServiceInfo Model Tests

    @pytest.mark.parametrize(
        ("name", "version", "environment"),
        [
            ("Tributum", "0.1.0", "development"),
            ("PaymentService", "1.2.3", "production"),
            ("API Gateway", "2.0.0-beta", "staging"),
            ("User Service", "v3.4.5", "test"),
            ("", "", ""),  # Empty strings are valid
            ("Service-Name_123", "1.0.0+build.123", "custom-env"),
        ],
    )
    def test_service_info_creation_with_valid_data(
        self,
        name: str,
        version: str,
        environment: str,
    ) -> None:
        """Test ServiceInfo model can be created with all required fields."""
        # Execution
        service_info = ServiceInfo(
            name=name,
            version=version,
            environment=environment,
        )

        # Assertions
        assert service_info.name == name
        assert service_info.version == version
        assert service_info.environment == environment

    @pytest.mark.parametrize(
        ("invalid_data", "expected_error"),
        [
            ({"name": 123, "version": "1.0", "environment": "dev"}, "name"),
            ({"name": "Service", "version": 456, "environment": "dev"}, "version"),
            (
                {"name": "Service", "version": "1.0", "environment": 789},
                "environment",
            ),
            ({"name": None, "version": "1.0", "environment": "dev"}, "name"),
            ({"name": "Service", "version": None, "environment": "dev"}, "version"),
            (
                {"name": "Service", "version": "1.0", "environment": None},
                "environment",
            ),
            ({"name": ["Service"], "version": "1.0", "environment": "dev"}, "name"),
            (
                {"name": "Service", "version": {"v": "1.0"}, "environment": "dev"},
                "version",
            ),
        ],
    )
    async def test_service_info_field_validation(
        self,
        invalid_data: dict[str, Any],
        expected_error: str,
    ) -> None:
        """Test ServiceInfo model validates field types correctly."""
        # Execution & Assertions
        with pytest.raises(ValidationError) as exc_info:
            ServiceInfo(**invalid_data)

        # Verify the error is for the expected field
        errors = exc_info.value.errors()
        assert any(expected_error in str(error["loc"]) for error in errors)

    async def test_service_info_serialization(self) -> None:
        """Test ServiceInfo model serializes correctly to dict and JSON."""
        # Setup
        service_info = ServiceInfo(
            name="Test Service",
            version="1.0.0",
            environment="production",
        )

        # Test model_dump
        data_dict = service_info.model_dump()
        assert data_dict == {
            "name": "Test Service",
            "version": "1.0.0",
            "environment": "production",
        }

        # Test model_dump_json
        json_str = service_info.model_dump_json()
        parsed = json.loads(json_str)
        assert parsed == data_dict

    @pytest.mark.parametrize(
        "json_input",
        [
            '{"name": "Service", "version": "1.0", "environment": "dev"}',
            '{\n  "name": "Service",\n  "version": "1.0",\n  "environment": "dev"\n}',
            '{"name":"Service","version":"1.0","environment":"dev"}',
        ],
    )
    async def test_service_info_deserialization(
        self,
        json_input: str,
    ) -> None:
        """Test ServiceInfo model deserializes correctly from JSON."""
        # Execution
        service_info = ServiceInfo.model_validate_json(json_input)

        # Assertions
        assert service_info.name == "Service"
        assert service_info.version == "1.0"
        assert service_info.environment == "dev"

    # ErrorResponse Model Tests

    async def test_error_response_minimal_required_fields(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Test ErrorResponse can be created with only required fields."""
        # Mock datetime to ensure predictable timestamp
        mock_datetime = mocker.Mock()
        mock_now = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
        mock_datetime.now.return_value = mock_now
        mocker.patch("src.api.schemas.errors.datetime", mock_datetime)

        # Execution
        error_response = ErrorResponse(
            error_code="TEST_ERROR",
            message="Test error message",
        )

        # Assertions - required fields
        assert error_response.error_code == "TEST_ERROR"
        assert error_response.message == "Test error message"

        # Assertions - default values
        assert error_response.details is None
        assert error_response.correlation_id is None
        assert error_response.timestamp == mock_now
        assert error_response.severity is None
        assert error_response.service_info is None
        assert error_response.request_id is None
        assert error_response.debug_info is None

    @pytest.mark.parametrize(
        ("optional_fields", "expected_values"),
        [
            (
                {
                    "details": {"field": "email", "error": "invalid"},
                    "correlation_id": "corr-123",
                    "severity": "ERROR",
                    "request_id": "req-456",
                },
                {
                    "has_details": True,
                    "has_correlation": True,
                    "has_severity": True,
                    "has_request": True,
                },
            ),
            (
                {
                    "service_info": ServiceInfo(
                        name="TestService", version="1.0", environment="dev"
                    ),
                    "debug_info": {"stack": ["line1", "line2"]},
                },
                {
                    "has_service": True,
                    "has_debug": True,
                },
            ),
            (
                {},  # No optional fields
                {
                    "all_none": True,
                },
            ),
        ],
    )
    async def test_error_response_full_creation(
        self,
        mocker: MockerFixture,
        optional_fields: dict[str, Any],
        expected_values: dict[str, bool],
    ) -> None:
        """Test ErrorResponse can be created with all optional fields populated."""
        # Mock datetime
        mock_datetime = mocker.Mock()
        mock_now = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
        mock_datetime.now.return_value = mock_now
        mocker.patch("src.api.schemas.errors.datetime", mock_datetime)

        # Execution
        error_response = ErrorResponse(
            error_code="FULL_ERROR",
            message="Full error test",
            **optional_fields,
        )

        # Assertions
        assert error_response.error_code == "FULL_ERROR"
        assert error_response.message == "Full error test"

        if expected_values.get("has_details"):
            assert error_response.details == optional_fields["details"]
        if expected_values.get("has_correlation"):
            assert error_response.correlation_id == optional_fields["correlation_id"]
        if expected_values.get("has_severity"):
            assert error_response.severity == optional_fields["severity"]
        if expected_values.get("has_request"):
            assert error_response.request_id == optional_fields["request_id"]
        if expected_values.get("has_service"):
            assert error_response.service_info == optional_fields["service_info"]
        if expected_values.get("has_debug"):
            assert error_response.debug_info == optional_fields["debug_info"]
        if expected_values.get("all_none"):
            assert error_response.details is None
            assert error_response.correlation_id is None

    async def test_error_response_timestamp_timezone(self) -> None:
        """Test timestamp field always includes timezone information (UTC)."""
        # Execution
        error_response = ErrorResponse(
            error_code="TZ_TEST",
            message="Timezone test",
        )

        # Assertions
        assert error_response.timestamp.tzinfo is not None
        assert error_response.timestamp.tzinfo == UTC

    @pytest.mark.parametrize(
        ("invalid_data", "expected_field"),
        [
            ({"error_code": 123, "message": "Test"}, "error_code"),
            ({"error_code": "TEST", "message": 456}, "message"),
            (
                {"error_code": "TEST", "message": "Test", "details": "not_dict"},
                "details",
            ),
            (
                {"error_code": "TEST", "message": "Test", "severity": 123},
                "severity",
            ),
            (
                {"error_code": "TEST", "message": "Test", "timestamp": "invalid"},
                "timestamp",
            ),
            (
                {"error_code": "TEST", "message": "Test", "service_info": "not_object"},
                "service_info",
            ),
            (
                {"error_code": "TEST", "message": "Test", "debug_info": ["not_dict"]},
                "debug_info",
            ),
        ],
    )
    async def test_error_response_field_validation(
        self,
        invalid_data: dict[str, Any],
        expected_field: str,
    ) -> None:
        """Test ErrorResponse validates field types correctly."""
        # Execution & Assertions
        with pytest.raises(ValidationError) as exc_info:
            ErrorResponse(**invalid_data)

        # Verify error is for expected field
        errors = exc_info.value.errors()
        assert any(expected_field in str(error["loc"]) for error in errors)

    async def test_error_response_serialization_excludes_none(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Test ErrorResponse serialization excludes None values by default."""
        # Mock datetime
        mock_datetime = mocker.Mock()
        mock_now = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
        mock_datetime.now.return_value = mock_now
        mocker.patch("src.api.schemas.errors.datetime", mock_datetime)

        # Create response with some None fields
        error_response = ErrorResponse(
            error_code="SERIALIZE_TEST",
            message="Serialization test",
            details=None,
            correlation_id="corr-123",
            severity=None,
        )

        # Test model_dump
        data_dict = error_response.model_dump(exclude_none=True)
        assert "details" not in data_dict
        assert "severity" not in data_dict
        assert "correlation_id" in data_dict

        # Test model_dump_json
        json_str = error_response.model_dump_json(exclude_none=True)
        parsed = json.loads(json_str)
        assert "details" not in parsed
        assert "severity" not in parsed
        assert "correlation_id" in parsed

    async def test_error_response_json_schema_examples(self) -> None:
        """Test the model_config examples are valid according to the model schema."""
        # Get examples from model config
        schema = ErrorResponse.model_json_schema()
        examples = schema.get("examples", [])

        # Verify we have examples
        assert len(examples) > 0

        # Test each example creates a valid instance
        for example in examples:
            # Parse example as ErrorResponse
            error_response = ErrorResponse.model_validate(example)

            # Verify required fields are present
            assert error_response.error_code
            assert error_response.message
            assert error_response.timestamp

            # Verify the example round-trips correctly
            serialized = error_response.model_dump()
            assert serialized["error_code"] == example["error_code"]
            assert serialized["message"] == example["message"]

    async def test_error_response_nested_service_info(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Test ErrorResponse correctly handles nested ServiceInfo model."""
        # Mock datetime
        mock_datetime = mocker.Mock()
        mock_now = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
        mock_datetime.now.return_value = mock_now
        mocker.patch("src.api.schemas.errors.datetime", mock_datetime)

        # Create ServiceInfo
        service_info = ServiceInfo(
            name="TestService",
            version="2.0.0",
            environment="staging",
        )

        # Create ErrorResponse with nested ServiceInfo
        error_response = ErrorResponse(
            error_code="NESTED_TEST",
            message="Nested model test",
            service_info=service_info,
        )

        # Test serialization
        data_dict = error_response.model_dump()
        assert data_dict["service_info"] == {
            "name": "TestService",
            "version": "2.0.0",
            "environment": "staging",
        }

        # Test JSON serialization/deserialization
        json_str = error_response.model_dump_json()
        deserialized = ErrorResponse.model_validate_json(json_str)
        assert deserialized.service_info is not None
        assert deserialized.service_info.name == "TestService"
        assert deserialized.service_info.version == "2.0.0"
        assert deserialized.service_info.environment == "staging"

    @pytest.mark.parametrize(
        "details_structure",
        [
            {"simple": "value"},
            {"nested": {"level1": {"level2": "value"}}},
            {"list": ["item1", "item2", "item3"]},
            {"mixed": {"str": "text", "num": 123, "bool": True, "null": None}},
            {"validation_errors": {"email": ["invalid"], "age": ["too young"]}},
            {},  # Empty dict
            {"complex": {"items": [{"id": 1}, {"id": 2}], "meta": {"count": 2}}},
        ],
    )
    async def test_error_response_details_field_flexibility(
        self,
        details_structure: dict[str, Any],
    ) -> None:
        """Test details field accepts various dict structures."""
        # Execution
        error_response = ErrorResponse(
            error_code="DETAILS_TEST",
            message="Details field test",
            details=details_structure,
        )

        # Assertions
        assert error_response.details == details_structure

        # Test serialization preserves structure
        serialized = error_response.model_dump()
        assert serialized["details"] == details_structure

    @pytest.mark.parametrize(
        "debug_info",
        [
            {
                "stack_trace": [
                    "File 'app.py', line 10",
                    "File 'handler.py', line 20",
                ],
                "error_context": {"user_id": 123},
                "exception_type": "ValueError",
            },
            {
                "stack_trace": [],
                "variables": {"x": 10, "y": 20},
            },
            {
                "exception": {"type": "RuntimeError", "message": "Test error"},
                "system": {"memory": "4GB", "cpu": "2 cores"},
            },
            {},  # Empty debug info
        ],
    )
    async def test_error_response_debug_info_structure(
        self,
        debug_info: dict[str, Any],
    ) -> None:
        """Test debug_info field properly handles complex debug data structures."""
        # Execution
        error_response = ErrorResponse(
            error_code="DEBUG_TEST",
            message="Debug info test",
            debug_info=debug_info,
        )

        # Assertions
        assert error_response.debug_info == debug_info

        # Test serialization preserves structure
        json_str = error_response.model_dump_json()
        deserialized = ErrorResponse.model_validate_json(json_str)
        assert deserialized.debug_info == debug_info

    # Thread Safety Tests

    @pytest.mark.timeout(10)
    def test_concurrent_model_creation(
        self,
        thread_sync: dict[str, Any],
    ) -> None:
        """Test models can be safely created concurrently in multiple threads."""
        # Setup
        thread_count = 5
        barrier = thread_sync["barrier"](thread_count)
        results = thread_sync["create_results"]()
        errors: list[Exception] = []

        def create_models(thread_id: int) -> None:
            """Create models in a thread."""
            try:
                # Wait for all threads to be ready
                barrier.wait()

                # Create ServiceInfo
                service_info = ServiceInfo(
                    name=f"Service-{thread_id}",
                    version=f"{thread_id}.0.0",
                    environment="test",
                )

                # Create ErrorResponse
                error_response = ErrorResponse(
                    error_code=f"THREAD_{thread_id}",
                    message=f"Message from thread {thread_id}",
                    service_info=service_info,
                    details={"thread_id": thread_id},
                )

                # Store results
                results.append(
                    {
                        "thread_id": thread_id,
                        "service_info": service_info,
                        "error_response": error_response,
                    }
                )
            except Exception as e:
                errors.append(e)

        # Create and start threads
        threads = []
        for i in range(thread_count):
            thread = threading.Thread(target=create_models, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # Assertions
        assert len(errors) == 0, f"Thread errors: {errors}"
        assert len(results) == thread_count

        # Verify each thread created unique models
        thread_ids = {r["thread_id"] for r in results}
        assert len(thread_ids) == thread_count

        # Verify model integrity
        for result in results:
            tid = result["thread_id"]
            assert result["service_info"].name == f"Service-{tid}"
            assert result["error_response"].error_code == f"THREAD_{tid}"

    # Integration with FastAPI Tests

    async def test_error_response_fastapi_compatible(self) -> None:
        """Test ErrorResponse model works with FastAPI's JSON response handling."""
        # Test that model can generate JSON schema
        schema = ErrorResponse.model_json_schema()

        # Verify schema has required fields
        assert "properties" in schema
        assert "error_code" in schema["properties"]
        assert "message" in schema["properties"]

        # Verify required fields are marked as such
        assert "required" in schema
        assert "error_code" in schema["required"]
        assert "message" in schema["required"]

        # Test schema includes examples
        assert "examples" in schema
        assert len(schema["examples"]) > 0

    @pytest.mark.parametrize(
        "field_name",
        [
            "error_code",
            "message",
            "details",
            "correlation_id",
            "timestamp",
            "severity",
            "service_info",
            "request_id",
            "debug_info",
        ],
    )
    async def test_error_response_field_descriptions(
        self,
        field_name: str,
    ) -> None:
        """Test all fields have proper descriptions and examples for OpenAPI docs."""
        # Get field info
        field_info = ErrorResponse.model_fields[field_name]

        # Verify field has description
        assert field_info.description is not None
        assert len(field_info.description) > 0

        # Verify field has examples (if not timestamp which has default_factory)
        if field_name != "timestamp" and field_name in [
            "error_code",
            "message",
            "correlation_id",
            "severity",
            "request_id",
        ]:
            assert field_info.examples is not None

    async def test_error_response_json_schema_generation(self) -> None:
        """Test ErrorResponse generates correct JSON schema for OpenAPI."""
        # Generate schema
        schema = ErrorResponse.model_json_schema()

        # Verify basic schema structure
        assert schema["type"] == "object"
        assert "properties" in schema
        assert "required" in schema

        # Verify all fields are in schema
        expected_fields = {
            "error_code",
            "message",
            "details",
            "correlation_id",
            "timestamp",
            "severity",
            "service_info",
            "request_id",
            "debug_info",
        }
        assert set(schema["properties"].keys()) == expected_fields

        # Verify field types
        assert schema["properties"]["error_code"]["type"] == "string"
        assert schema["properties"]["message"]["type"] == "string"
        assert schema["properties"]["timestamp"]["type"] == "string"
        assert schema["properties"]["timestamp"]["format"] == "date-time"

        # Verify optional fields allow null
        for field in [
            "details",
            "correlation_id",
            "severity",
            "service_info",
            "request_id",
            "debug_info",
        ]:
            field_schema = schema["properties"][field]
            assert "anyOf" in field_schema or "type" in field_schema

    @pytest.mark.parametrize(
        "json_input",
        [
            '{"error_code": "TEST", "message": "Test message"}',
            (
                '{"error_code": "VALIDATION_ERROR", "message": "Invalid input", '
                '"details": {"field": "email"}}'
            ),
            """{
                "error_code": "NOT_FOUND",
                "message": "Resource not found",
                "correlation_id": "123",
                "severity": "WARNING",
                "timestamp": "2024-01-01T12:00:00+00:00"
            }""",
        ],
    )
    async def test_error_response_deserialization_from_json(
        self,
        json_input: str,
    ) -> None:
        """Test ErrorResponse can be deserialized from JSON strings."""
        # Execution
        error_response = ErrorResponse.model_validate_json(json_input)

        # Assertions
        assert isinstance(error_response, ErrorResponse)
        assert error_response.error_code
        assert error_response.message
        assert isinstance(error_response.timestamp, datetime)

    async def test_error_response_copy_behavior(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Test ErrorResponse model supports copy operations correctly."""
        # Mock datetime
        mock_datetime = mocker.Mock()
        mock_now = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
        mock_datetime.now.return_value = mock_now
        mocker.patch("src.api.schemas.errors.datetime", mock_datetime)

        # Create original
        original = ErrorResponse(
            error_code="ORIGINAL",
            message="Original message",
            details={"key": "value"},
            correlation_id="corr-123",
        )

        # Test model_copy with no changes
        copy1 = original.model_copy()
        assert copy1.error_code == "ORIGINAL"
        assert copy1.message == "Original message"
        assert copy1.details == {"key": "value"}
        assert copy1 is not original

        # Test model_copy with updates
        copy2 = original.model_copy(
            update={"error_code": "UPDATED", "message": "Updated message"}
        )
        assert copy2.error_code == "UPDATED"
        assert copy2.message == "Updated message"
        assert copy2.details == {"key": "value"}  # Unchanged fields preserved
        assert copy2.correlation_id == "corr-123"

        # Test deep copy behavior
        copy3 = original.model_copy(deep=True)
        if copy3.details is not None:
            copy3.details["key"] = "modified"
        if original.details is not None:
            assert original.details["key"] == "value"  # Original unchanged
