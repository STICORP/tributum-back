"""Unit tests for the types module.

This module tests the type aliases defined in src.core.types to ensure
they work correctly and that the module can be imported successfully.
"""

from src.core.types import AsgiScope, ErrorContext, JsonValue, LogContext


class TestTypeAliases:
    """Test type aliases defined in the types module."""

    def test_import_types_module(self) -> None:
        """Test that we can import all type aliases from the types module."""
        # Verify imports succeeded by checking they exist
        assert JsonValue is not None
        assert LogContext is not None
        assert ErrorContext is not None
        assert AsgiScope is not None

    def test_json_value_type_structure(self) -> None:
        """Test that JsonValue type represents valid JSON structure."""
        # Test various valid JSON values
        valid_json_values: list[JsonValue] = [
            None,
            True,
            False,
            42,
            3.14,
            "string",
            [],
            [1, 2, 3],
            ["a", "b", "c"],
            {},
            {"key": "value"},
            {"nested": {"structure": [1, 2, {"deep": True}]}},
            [{"list": "of"}, {"dicts": "works"}],
        ]

        # Just verify the list compiles correctly with type checking
        assert len(valid_json_values) > 0

    def test_log_context_type_usage(self) -> None:
        """Test that LogContext type works for logging contexts."""
        # Test various log contexts
        log_contexts: list[LogContext] = [
            {},
            {"user_id": 123},
            {"request_id": "req-123", "correlation_id": "corr-456"},
            {"nested": {"data": {"structure": True}}},
            {"mixed": [1, "two", {"three": 3}]},
        ]

        # Verify we can create log contexts
        assert all(isinstance(ctx, dict) for ctx in log_contexts)

    def test_error_context_type_usage(self) -> None:
        """Test that ErrorContext type works for error contexts."""
        # Test various error contexts
        error_contexts: list[ErrorContext] = [
            {},
            {"error": "Something went wrong"},
            {"field": "email", "value": "invalid@", "reason": "Invalid format"},
            {"code": 500, "details": {"internal": "error"}},
            {"stack_trace": ["line1", "line2"], "variables": {"x": 1}},
        ]

        # Verify we can create error contexts
        assert all(isinstance(ctx, dict) for ctx in error_contexts)

    def test_asgi_scope_type_usage(self) -> None:
        """Test that AsgiScope type works for ASGI scopes."""
        # Test a typical ASGI HTTP scope
        http_scope: AsgiScope = {
            "type": "http",
            "asgi": {"version": "3.0", "spec_version": "2.3"},
            "http_version": "1.1",
            "method": "GET",
            "scheme": "https",
            "path": "/api/users",
            "query_string": b"page=1&limit=10",
            "root_path": "",
            "headers": [(b"host", b"example.com"), (b"user-agent", b"test")],
            "server": ("example.com", 443),
            "client": ("192.168.1.1", 54321),
            "state": {},
        }

        # Test a websocket scope
        ws_scope: AsgiScope = {
            "type": "websocket",
            "asgi": {"version": "3.0"},
            "scheme": "wss",
            "path": "/ws",
            "query_string": b"",
            "headers": [],
            "server": ("localhost", 8000),
            "client": ("127.0.0.1", 12345),
            "subprotocols": ["chat"],
        }

        # Verify the scopes are valid dictionaries
        assert http_scope["type"] == "http"
        assert ws_scope["type"] == "websocket"

    def test_type_annotations_are_correct(self) -> None:
        """Test that the type annotations match expected patterns."""
        # In Python 3.12+, type aliases are special objects, not raw types
        # Just verify they exist and can be used in annotations
        assert LogContext is not None
        assert ErrorContext is not None
        assert AsgiScope is not None
        assert JsonValue is not None

        # Test that we can use them in type annotations without errors
        test_log: LogContext = {"test": "log"}
        test_error: ErrorContext = {"error": "context"}
        test_scope: AsgiScope = {"type": "http"}
        test_json: JsonValue = {"key": "value"}

        assert isinstance(test_log, dict)
        assert isinstance(test_error, dict)
        assert isinstance(test_scope, dict)
        assert test_json == {"key": "value"}

    def test_types_can_be_used_in_annotations(self) -> None:
        """Test that types can be used in function annotations."""

        def process_json(data: JsonValue) -> JsonValue:
            """Function using JsonValue type."""
            return data

        def log_with_context(message: str, context: LogContext) -> None:
            """Function using LogContext type."""

        def handle_error(error: Exception, context: ErrorContext) -> None:
            """Function using ErrorContext type."""

        def handle_asgi(scope: AsgiScope) -> None:
            """Function using AsgiScope type."""

        # Test the functions work with appropriate values
        assert process_json({"key": "value"}) == {"key": "value"}
        assert process_json([1, 2, 3]) == [1, 2, 3]
        assert process_json("string") == "string"
        assert process_json(42) == 42
        # Test with boolean value
        bool_value = True
        bool_result = process_json(bool_value)
        assert bool_result is bool_value
        assert process_json(None) is None

        # Just call the void functions to ensure they work
        log_with_context("test", {"level": "info"})
        handle_error(ValueError("test"), {"code": 400})
        handle_asgi({"type": "http", "method": "GET"})
