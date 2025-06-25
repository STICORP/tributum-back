"""Unit tests for ORJSONRenderer custom processor."""

import datetime
import json
import uuid

import pytest
from pytest_mock import MockerFixture

from src.core.logging import ORJSONRenderer


@pytest.mark.unit
class TestORJSONRenderer:
    """Test the ORJSONRenderer custom processor."""

    def test_basic_json_rendering(self, mocker: MockerFixture) -> None:
        """Test basic JSON rendering with simple types."""
        renderer = ORJSONRenderer()
        logger = mocker.MagicMock()
        event_dict = {
            "event": "test message",
            "level": "INFO",
            "number": 123,
            "float": 45.67,
            "bool": True,
            "none": None,
        }

        result = renderer(logger, "test", event_dict)

        # Parse the result to verify it's valid JSON

        parsed = json.loads(result)
        assert parsed["event"] == "test message"
        assert parsed["level"] == "INFO"
        assert parsed["number"] == 123
        assert parsed["float"] == 45.67
        assert parsed["bool"] is True
        assert parsed["none"] is None

    def test_datetime_handling(self, mocker: MockerFixture) -> None:
        """Test that datetime objects are serialized correctly."""
        renderer = ORJSONRenderer()
        logger = mocker.MagicMock()
        now = datetime.datetime.now(datetime.UTC)
        event_dict = {"event": "test", "timestamp": now}

        result = renderer(logger, "test", event_dict)

        parsed = json.loads(result)
        assert parsed["event"] == "test"
        # orjson serializes datetime to ISO format string
        assert isinstance(parsed["timestamp"], str)
        assert now.isoformat() in parsed["timestamp"]

    def test_uuid_handling(self, mocker: MockerFixture) -> None:
        """Test that UUID objects are serialized correctly."""
        renderer = ORJSONRenderer()
        logger = mocker.MagicMock()
        test_uuid = uuid.uuid4()
        event_dict = {"event": "test", "id": test_uuid}

        result = renderer(logger, "test", event_dict)

        parsed = json.loads(result)
        assert parsed["event"] == "test"
        assert parsed["id"] == str(test_uuid)

    def test_exception_handling(self, mocker: MockerFixture) -> None:
        """Test that exceptions are converted to strings."""
        renderer = ORJSONRenderer()
        logger = mocker.MagicMock()
        error = ValueError("Test error")
        event_dict = {"event": "error occurred", "exception": error}

        result = renderer(logger, "test", event_dict)

        parsed = json.loads(result)
        assert parsed["event"] == "error occurred"
        assert parsed["exception"] == "Test error"

    def test_type_handling(self, mocker: MockerFixture) -> None:
        """Test that type objects are converted to their names."""
        renderer = ORJSONRenderer()
        logger = mocker.MagicMock()
        event_dict = {"event": "test", "error_type": ValueError}

        result = renderer(logger, "test", event_dict)

        parsed = json.loads(result)
        assert parsed["event"] == "test"
        assert parsed["error_type"] == "ValueError"

    def test_nested_dict_processing(self, mocker: MockerFixture) -> None:
        """Test that nested dictionaries are processed correctly."""
        renderer = ORJSONRenderer()
        logger = mocker.MagicMock()
        error = Exception("nested error")
        event_dict = {
            "event": "test",
            "context": {
                "user": {"id": 123, "name": "test"},
                "error": error,
                "metadata": {"type": ValueError},
            },
        }

        result = renderer(logger, "test", event_dict)

        parsed = json.loads(result)
        assert parsed["event"] == "test"
        assert parsed["context"]["user"]["id"] == 123
        assert parsed["context"]["error"] == "nested error"
        assert parsed["context"]["metadata"]["type"] == "ValueError"

    def test_list_processing(self, mocker: MockerFixture) -> None:
        """Test that lists containing special types are processed."""
        renderer = ORJSONRenderer()
        logger = mocker.MagicMock()
        errors = [ValueError("error1"), TypeError("error2")]
        event_dict = {"event": "test", "errors": errors, "numbers": [1, 2, 3]}

        result = renderer(logger, "test", event_dict)

        parsed = json.loads(result)
        assert parsed["event"] == "test"
        assert parsed["errors"] == ["error1", "error2"]
        assert parsed["numbers"] == [1, 2, 3]

    def test_tuple_processing(self, mocker: MockerFixture) -> None:
        """Test that tuples containing special types are processed."""
        renderer = ORJSONRenderer()
        logger = mocker.MagicMock()
        # Test with tuple containing various types
        event_dict = {
            "event": "test",
            "tuple_data": (ValueError("error1"), dict, {"nested": True}, 123),
            "mixed_tuple": (1, "string", None, True),
        }

        result = renderer(logger, "test", event_dict)

        parsed = json.loads(result)
        assert parsed["event"] == "test"
        # Tuples are converted to lists in JSON
        assert parsed["tuple_data"] == ["error1", "dict", {"nested": True}, 123]
        assert parsed["mixed_tuple"] == [1, "string", None, True]

    def test_sort_keys_option(self, mocker: MockerFixture) -> None:
        """Test that keys are sorted for consistency."""
        renderer = ORJSONRenderer()
        logger = mocker.MagicMock()
        event_dict = {
            "zebra": 1,
            "alpha": 2,
            "beta": 3,
            "event": "test",
        }

        result = renderer(logger, "test", event_dict)

        # Keys should be in sorted order
        assert result.index("alpha") < result.index("beta")
        assert result.index("beta") < result.index("event")
        assert result.index("event") < result.index("zebra")

    def test_custom_options_initialization(self, mocker: MockerFixture) -> None:
        """Test ORJSONRenderer with custom options."""
        # Test with valid orjson option
        renderer = ORJSONRenderer(OPT_INDENT_2=True)
        logger = mocker.MagicMock()
        event_dict = {"event": "test", "nested": {"key": "value"}}

        result = renderer(logger, "test", event_dict)

        # Should include indentation
        assert "  " in result  # Check for indentation

        # Test with invalid option (should be ignored)
        renderer2 = ORJSONRenderer(INVALID_OPTION=True)
        result2 = renderer2(logger, "test", event_dict)

        # Should still produce valid JSON

        parsed = json.loads(result2)
        assert parsed["event"] == "test"

    def test_performance_comparison(self, mocker: MockerFixture) -> None:
        """Test that ORJSONRenderer performs well compared to JSONRenderer."""
        # Create test data with various types
        event_dict = {
            "event": "performance test",
            "timestamp": datetime.datetime.now(datetime.UTC),
            "user_id": 12345,
            "metadata": {
                "nested": True,
                "values": list(range(100)),
                "mapping": {str(i): i for i in range(50)},
            },
        }

        # Test ORJSONRenderer
        orjson_renderer = ORJSONRenderer()
        logger = mocker.MagicMock()

        # Warm up
        for _ in range(10):
            orjson_renderer(logger, "test", event_dict)

        # Just verify it works correctly and produces valid output
        result = orjson_renderer(logger, "test", event_dict)

        parsed = json.loads(result)

        # Verify the output is correct
        assert parsed["event"] == "performance test"
        assert parsed["user_id"] == 12345
        assert len(parsed["metadata"]["values"]) == 100
        assert len(parsed["metadata"]["mapping"]) == 50

    def test_complex_real_world_log(self, mocker: MockerFixture) -> None:
        """Test with a complex log entry similar to real usage."""
        renderer = ORJSONRenderer()
        logger = mocker.MagicMock()

        # Simulate a real log entry
        event_dict = {
            "event": "api_request_completed",
            "level": "INFO",
            "timestamp": datetime.datetime.now(datetime.UTC),
            "correlation_id": str(uuid.uuid4()),
            "logger": "api.handlers",
            "filename": "handlers.py",
            "lineno": 123,
            "func_name": "handle_request",
            "request": {
                "method": "POST",
                "path": "/api/users",
                "headers": {"content-type": "application/json"},
            },
            "response": {"status_code": 200, "duration_ms": 45.23},
            "user_id": 789,
            "error_context": None,
            "tags": ["api", "success"],
        }

        result = renderer(logger, "test", event_dict)

        # Should produce valid JSON

        parsed = json.loads(result)
        assert parsed["event"] == "api_request_completed"
        assert parsed["request"]["method"] == "POST"
        assert parsed["response"]["duration_ms"] == 45.23
        assert parsed["tags"] == ["api", "success"]
