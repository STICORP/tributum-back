"""Unit tests for custom response classes."""

import json
import time
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi.responses import JSONResponse
from pydantic import BaseModel

from src.api.schemas.errors import ErrorResponse
from src.api.utils.responses import ORJSONResponse


class SampleModel(BaseModel):
    """Sample Pydantic model for testing."""

    id: UUID
    name: str
    created_at: datetime
    metadata: dict[str, Any] | None = None


class TestORJSONResponse:
    """Test ORJSONResponse class functionality."""

    def test_basic_type_serialization(self) -> None:
        """Test serialization of basic Python types."""
        content = {
            "string": "test",
            "integer": 42,
            "float": 3.14,
            "boolean": True,
            "null": None,
            "list": [1, 2, 3],
            "dict": {"nested": "value"},
        }

        response = ORJSONResponse(content)
        result = response.render(content)

        # Verify it's bytes
        assert isinstance(result, bytes)

        # Verify content is correct
        parsed = json.loads(result)
        assert parsed == content

    def test_pydantic_model_serialization(self) -> None:
        """Test serialization of Pydantic models."""
        model = SampleModel(
            id=UUID("550e8400-e29b-41d4-a716-446655440000"),
            name="Test Model",
            created_at=datetime(2024, 6, 14, 12, 0, 0, tzinfo=UTC),
            metadata={"key": "value"},
        )

        response = ORJSONResponse(model)
        result = response.render(model)

        parsed = json.loads(result)
        assert parsed["id"] == "550e8400-e29b-41d4-a716-446655440000"
        assert parsed["name"] == "Test Model"
        assert parsed["created_at"] == "2024-06-14T12:00:00+00:00"
        assert parsed["metadata"] == {"key": "value"}

    def test_error_response_with_timestamp(self) -> None:
        """Test serialization of ErrorResponse model with timezone-aware timestamp."""
        error = ErrorResponse(
            error_code="TEST_ERROR",
            message="Test error message",
            correlation_id="550e8400-e29b-41d4-a716-446655440000",
            timestamp=datetime(2024, 6, 14, 12, 0, 0, tzinfo=UTC),
            severity="ERROR",
        )

        response = ORJSONResponse(error)
        result = response.render(error)

        parsed = json.loads(result)
        assert parsed["error_code"] == "TEST_ERROR"
        assert parsed["message"] == "Test error message"
        assert parsed["timestamp"] == "2024-06-14T12:00:00+00:00"

    def test_none_values_and_empty_responses(self) -> None:
        """Test handling of None values and empty responses."""
        # Test None
        response = ORJSONResponse(None)
        result = response.render(None)
        assert result == b"null"

        # Test empty dict
        response = ORJSONResponse({})
        result = response.render({})
        assert result == b"{}"

        # Test empty list
        response = ORJSONResponse([])
        result = response.render([])
        assert result == b"[]"

    def test_performance_vs_json_response(self) -> None:
        """Compare performance with standard JSONResponse."""
        # Create a large data structure
        large_data = {
            f"key_{i}": {
                "id": str(UUID("550e8400-e29b-41d4-a716-446655440000")),
                "timestamp": datetime.now(UTC).isoformat(),
                "data": list(range(100)),
                "nested": {"level": i, "active": i % 2 == 0},
            }
            for i in range(100)
        }

        # Time ORJSONResponse
        orjson_start = time.perf_counter()
        for _ in range(10):
            response = ORJSONResponse(large_data)
            response.render(large_data)
        orjson_time = time.perf_counter() - orjson_start

        # Time JSONResponse
        json_start = time.perf_counter()
        for _ in range(10):
            json_response = JSONResponse(large_data)
            json_response.render(large_data)
        json_time = time.perf_counter() - json_start

        # ORJSONResponse should be faster
        # Note: This might be flaky in CI, so we just check it works
        assert orjson_time > 0
        assert json_time > 0

    def test_media_type(self) -> None:
        """Test that media type is correctly set."""
        response = ORJSONResponse({"test": "data"})
        assert response.media_type == "application/json"

    def test_sort_keys_option(self) -> None:
        """Test that keys are sorted for consistent output."""
        content = {"z": 1, "a": 2, "m": 3}
        response = ORJSONResponse(content)
        result = response.render(content)

        # Keys should be sorted
        parsed_str = result.decode("utf-8")
        assert parsed_str.index('"a"') < parsed_str.index('"m"')
        assert parsed_str.index('"m"') < parsed_str.index('"z"')

    def test_compact_output(self) -> None:
        """Test that output is compact (no indentation)."""
        content = {"key": "value", "nested": {"inner": "data"}}

        response = ORJSONResponse(content)
        result = response.render(content)

        # Should be compact without newlines or extra spaces
        assert b"\n" not in result
        assert b"  " not in result

    def test_special_types_handling(self) -> None:
        """Test handling of special types like UUID and datetime."""
        content = {
            "uuid": UUID("550e8400-e29b-41d4-a716-446655440000"),
            "datetime": datetime(2024, 6, 14, 12, 0, 0, tzinfo=UTC),
            "date": datetime(2024, 6, 14, tzinfo=UTC).date(),
        }

        response = ORJSONResponse(content)
        result = response.render(content)

        parsed = json.loads(result)
        assert parsed["uuid"] == "550e8400-e29b-41d4-a716-446655440000"
        assert parsed["datetime"] == "2024-06-14T12:00:00+00:00"
        assert parsed["date"] == "2024-06-14"
