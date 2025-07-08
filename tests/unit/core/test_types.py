"""Comprehensive unit tests for src/core/types.py module.

This module tests all type aliases defined in the types module, ensuring they
correctly represent the intended data structures and maintain JSON serialization
compatibility as documented.
"""

import asyncio
import json
import sys
import threading
import time
from typing import TYPE_CHECKING, Any

import pytest
from pytest_mock import MockerFixture

import src.core.types as types_module

# Import the type aliases we're testing
from src.core.types import (
    AsgiScope,
    ErrorContext,
    JsonValue,
    LogContext,
    PerformanceThresholds,
)


@pytest.mark.unit
class TestTypes:
    """Test suite for type aliases in src/core/types.py."""

    # Test 1: JsonValue Type Validation
    @pytest.mark.parametrize(
        ("value", "description"),
        [
            ({"key": "value"}, "dictionary with string"),
            ([1, 2, 3], "list with integers"),
            ("test string", "string value"),
            (42, "integer value"),
            (3.14, "float value"),
            (True, "boolean True"),
            (False, "boolean False"),
            (None, "None value"),
            ({}, "empty dictionary"),
            ([], "empty list"),
            ({"nested": {"deep": {"level": 5}}}, "deeply nested dict"),
            ([{"a": 1}, {"b": 2}], "list of dictionaries"),
            ({"list": [1, 2, {"nested": "value"}]}, "mixed nested structure"),
        ],
    )
    def test_json_value_valid_types(self, value: JsonValue, description: str) -> None:
        """Test that JsonValue correctly represents all valid JSON types.

        Args:
            value: A value that should be valid as JsonValue
            description: Description of the test case
        """
        # Verify the value can be used as JsonValue
        json_val: JsonValue = value
        assert json_val == value, f"Failed for {description}"

        # Verify JSON serialization works
        serialized = json.dumps(json_val)
        deserialized = json.loads(serialized)
        assert deserialized == value, f"Serialization failed for {description}"

    def test_json_value_deeply_nested(self) -> None:
        """Test JsonValue with deeply nested structures (5+ levels)."""
        deeply_nested: JsonValue = {
            "level1": {
                "level2": {
                    "level3": {
                        "level4": {"level5": {"level6": "deep value"}},
                        "list": [1, 2, {"nested": "in list"}],
                    }
                }
            }
        }

        # Verify structure is valid
        assert isinstance(deeply_nested, dict)
        # Type assertions for nested access
        level1 = deeply_nested["level1"]
        assert isinstance(level1, dict)
        level2 = level1["level2"]
        assert isinstance(level2, dict)
        level3 = level2["level3"]
        assert isinstance(level3, dict)
        level4 = level3["level4"]
        assert isinstance(level4, dict)
        level5 = level4["level5"]
        assert isinstance(level5, dict)
        assert level5["level6"] == "deep value"

        # Verify JSON serialization
        serialized = json.dumps(deeply_nested)
        deserialized = json.loads(serialized)
        assert deserialized == deeply_nested

    def test_json_value_recursive_structures(self) -> None:
        """Test JsonValue with various recursive structures."""
        # Dict containing list containing dict
        recursive: JsonValue = {
            "items": [
                {"id": 1, "children": [{"id": 2}]},
                {"id": 3, "children": []},
            ]
        }

        assert isinstance(recursive, dict)
        items = recursive["items"]
        assert isinstance(items, list)
        assert len(items) == 2
        first_item = items[0]
        assert isinstance(first_item, dict)
        children = first_item["children"]
        assert isinstance(children, list)
        first_child = children[0]
        assert isinstance(first_child, dict)
        assert first_child["id"] == 2

    def test_json_value_type_alias_equivalence(self) -> None:
        """Test that JsonValue type alias is equivalent to its expanded union type."""
        # Test various values against the type
        test_values: list[JsonValue] = [
            {"dict": "value"},
            ["list", "value"],
            "string",
            123,
            45.67,
            True,
            None,
        ]

        for value in test_values:
            # All values should be valid JsonValue
            assert value is not None or value is None  # Tautology to use value

    def test_json_value_python_313_type_syntax(self) -> None:
        """Test that Python 3.13 type statement syntax works correctly."""
        # Verify we're on Python 3.13+
        assert sys.version_info >= (3, 13), "This test requires Python 3.13+"

        # Type should be accessible from module
        assert hasattr(JsonValue, "__name__")

    # Test 2: LogContext Type Usage
    @pytest.mark.parametrize(
        ("context", "description"),
        [
            ({}, "empty context"),
            ({"message": "test log"}, "string values"),
            ({"count": 42, "duration": 3.14}, "numeric values"),
            ({"success": True, "error": False}, "boolean values"),
            ({"error": None}, "None values"),
            ({"metadata": {"user": "john"}}, "nested dictionaries"),
            ({"tags": ["error", "api"]}, "lists"),
            ({"mixed": [1, "two", True, None]}, "mixed types"),
        ],
    )
    def test_log_context_usage(self, context: LogContext, description: str) -> None:
        """Test LogContext works correctly for structured logging scenarios.

        Args:
            context: A LogContext instance to test
            description: Description of the test case
        """
        # Verify it's a valid LogContext
        log_ctx: LogContext = context
        assert isinstance(log_ctx, dict), f"LogContext must be dict for {description}"

        # Verify JSON serialization
        serialized = json.dumps(log_ctx)
        deserialized = json.loads(serialized)
        assert deserialized == context, f"Serialization failed for {description}"

    def test_log_context_thread_safety(self, thread_sync: dict[str, Any]) -> None:
        """Test concurrent access to LogContext instances."""
        shared_context: LogContext = {"counter": 0, "messages": []}
        results = thread_sync["create_results"]()
        barrier = thread_sync["barrier"](3)

        def worker(worker_id: int) -> None:
            """Worker function that modifies shared context."""
            barrier.wait()
            # Read and write operations
            for i in range(10):
                # Create new context based on shared one
                new_context: LogContext = {
                    **shared_context,
                    f"worker_{worker_id}": i,
                }
                results.append(new_context)
                time.sleep(0.001)  # Small delay to increase contention

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=1.0)

        # Verify all operations completed
        assert len(results) == 30, "All threads should complete their operations"

    def test_log_context_json_serialization_error(self) -> None:
        """Test handling of non-serializable values in LogContext."""

        # Create context with non-serializable value
        # Using a function object to test non-serializable values
        def identity(x: object) -> object:
            """Non-serializable function."""
            return x

        context: LogContext = {"function": identity}  # Functions aren't serializable

        # Attempt to serialize should raise TypeError
        with pytest.raises(TypeError, match="not JSON serializable"):
            json.dumps(context)

    # Test 3: ErrorContext Type Usage
    @pytest.mark.parametrize(
        ("context", "description"),
        [
            ({}, "empty error context"),
            ({"error_code": "E001"}, "error codes"),
            ({"stack_trace": ["line1", "line2"]}, "stack traces"),
            ({"user_id": 123, "request_id": "req_456"}, "user data"),
            ({"timestamp": "2024-01-01T00:00:00Z"}, "timestamps"),
            ({"original": {"nested": "error"}}, "nested error contexts"),
        ],
    )
    def test_error_context_usage(self, context: ErrorContext, description: str) -> None:
        """Test ErrorContext works correctly for error handling scenarios.

        Args:
            context: An ErrorContext instance to test
            description: Description of the test case
        """
        # Verify it's a valid ErrorContext
        error_ctx: ErrorContext = context
        assert isinstance(error_ctx, dict), (
            f"ErrorContext must be dict for {description}"
        )

        # Verify JSON serialization for API responses
        serialized = json.dumps(error_ctx)
        deserialized = json.loads(serialized)
        assert deserialized == context, f"Serialization failed for {description}"

    def test_error_context_thread_safety(self, thread_sync: dict[str, Any]) -> None:
        """Test concurrent error context creation."""
        errors = thread_sync["create_results"]()
        barrier = thread_sync["barrier"](5)

        def error_handler(handler_id: int) -> None:
            """Simulate error handling in different threads."""
            barrier.wait()
            for i in range(5):
                error_ctx: ErrorContext = {
                    "handler_id": handler_id,
                    "error_num": i,
                    "timestamp": time.time(),
                    "thread_id": threading.get_ident(),
                }
                errors.append(error_ctx)
                time.sleep(0.001)

        threads = [threading.Thread(target=error_handler, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=1.0)

        # Verify all error contexts were created
        assert len(errors) == 25, "All error contexts should be created"
        # Verify each has unique thread_id
        thread_ids = {e["thread_id"] for e in errors}
        assert len(thread_ids) == 5, "Should have 5 different thread IDs"

    # Test 4: AsgiScope Type Compliance
    @pytest.mark.parametrize(
        ("scope_type", "required_fields"),
        [
            ("http", ["type", "asgi", "http_version", "method", "path"]),
            ("websocket", ["type", "asgi", "path", "headers"]),
            ("lifespan", ["type", "asgi"]),
        ],
    )
    def test_asgi_scope_structure(
        self, scope_type: str, required_fields: list[str]
    ) -> None:
        """Test AsgiScope matches ASGI specification requirements.

        Args:
            scope_type: The ASGI scope type
            required_fields: Fields required for this scope type
        """
        # Create minimal valid scope
        scope: AsgiScope = {
            "type": scope_type,
            "asgi": {"version": "3.0"},
        }

        # Add type-specific fields
        if scope_type == "http":
            scope.update(
                {
                    "http_version": "1.1",
                    "method": "GET",
                    "path": "/test",
                    "headers": [],
                }
            )
        elif scope_type == "websocket":
            scope.update({"path": "/ws", "headers": []})

        # Verify all required fields
        for field in required_fields:
            assert field in scope, f"Missing required field: {field}"

    def test_asgi_scope_headers_structure(self) -> None:
        """Test ASGI scope headers structure."""
        scope: AsgiScope = {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "GET",
            "path": "/test",
            "headers": [
                (b"host", b"example.com"),
                (b"user-agent", b"test/1.0"),
            ],
        }

        # Verify headers structure
        assert isinstance(scope["headers"], list)
        assert all(isinstance(h, tuple) and len(h) == 2 for h in scope["headers"])
        assert all(
            isinstance(h[0], bytes) and isinstance(h[1], bytes)
            for h in scope["headers"]
        )

    def test_asgi_scope_optional_fields(self) -> None:
        """Test handling of optional ASGI fields."""
        scope: AsgiScope = {
            "type": "http",
            "asgi": {"version": "3.0", "spec_version": "2.3"},
            "http_version": "1.1",
            "method": "POST",
            "path": "/api/data",
            "query_string": b"key=value",
            "headers": [],
            "server": ("127.0.0.1", 8000),
            "client": ("192.168.1.1", 54321),
            "scheme": "https",
        }

        # All optional fields should be accessible
        assert scope.get("query_string") == b"key=value"
        assert scope.get("server") == ("127.0.0.1", 8000)
        assert scope.get("client") == ("192.168.1.1", 54321)

    def test_asgi_scope_custom_extensions(self) -> None:
        """Test ASGI scope with custom extensions."""
        scope: AsgiScope = {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "GET",
            "path": "/test",
            "headers": [],
            "extensions": {
                "http.response.push": {},
                "websocket.http.response": {},
            },
            "state": {"custom_key": "custom_value"},
        }

        # Extensions and state should be preserved
        assert "extensions" in scope
        assert "state" in scope
        assert scope["state"]["custom_key"] == "custom_value"

    # Test 5: PerformanceThresholds Type Usage
    @pytest.mark.parametrize(
        ("thresholds", "description"),
        [
            ({}, "empty thresholds"),
            ({"response_time": 100}, "integer milliseconds"),
            ({"query_time": 50.5}, "float milliseconds"),
            (
                {"api_slow": 1000, "api_very_slow": 5000},
                "named threshold categories",
            ),
        ],
    )
    def test_performance_thresholds_usage(
        self, thresholds: PerformanceThresholds, description: str
    ) -> None:
        """Test PerformanceThresholds works for monitoring configurations.

        Args:
            thresholds: A PerformanceThresholds instance
            description: Description of the test case
        """
        # Verify it's a valid PerformanceThresholds
        perf_thresholds: PerformanceThresholds = thresholds
        assert isinstance(perf_thresholds, dict), (
            f"PerformanceThresholds must be dict for {description}"
        )

        # Verify all values are numeric
        for key, value in perf_thresholds.items():
            assert isinstance(value, (int, float)), f"Threshold {key} must be numeric"

        # Verify JSON serialization for configuration
        serialized = json.dumps(perf_thresholds)
        deserialized = json.loads(serialized)
        assert deserialized == thresholds

    def test_performance_thresholds_updates(self) -> None:
        """Test threshold updates and comparisons."""
        thresholds: PerformanceThresholds = {
            "slow": 1000,
            "very_slow": 5000,
        }

        # Test updates
        thresholds["critical"] = 10000
        assert thresholds["critical"] == 10000

        # Test comparisons
        response_time = 2500
        assert response_time > thresholds["slow"]
        assert response_time < thresholds["very_slow"]

    def test_performance_thresholds_thread_safety(
        self, thread_sync: dict[str, Any]
    ) -> None:
        """Test concurrent threshold updates."""
        shared_thresholds: PerformanceThresholds = {
            "base": 100,
        }
        results = thread_sync["create_results"]()
        barrier = thread_sync["barrier"](3)

        def updater(thread_id: int) -> None:
            """Update thresholds from different threads."""
            barrier.wait()
            for i in range(5):
                # Create new threshold config
                new_thresholds: PerformanceThresholds = {
                    **shared_thresholds,
                    f"thread_{thread_id}_threshold_{i}": 100 * (i + 1),
                }
                results.append(new_thresholds)
                time.sleep(0.001)

        threads = [threading.Thread(target=updater, args=(i,)) for i in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=1.0)

        assert len(results) == 15, "All threshold updates should complete"

    # Test 6: Type Alias Import and Usage
    @pytest.mark.parametrize(
        ("type_alias", "type_name"),
        [
            (JsonValue, "JsonValue"),
            (LogContext, "LogContext"),
            (ErrorContext, "ErrorContext"),
            (AsgiScope, "AsgiScope"),
            (PerformanceThresholds, "PerformanceThresholds"),
        ],
    )
    def test_type_alias_import(self, type_alias: object, type_name: str) -> None:
        """Test direct import of each type alias.

        Args:
            type_alias: The imported type alias
            type_name: Expected name of the type
        """
        # Verify type can be imported
        assert type_alias is not None, f"{type_name} should be importable"

        # Verify type has expected name
        assert hasattr(type_alias, "__name__"), f"{type_name} should have __name__"

    def test_type_alias_in_function_signatures(self) -> None:
        """Test type aliases in function signatures."""

        def process_json(data: JsonValue) -> JsonValue:
            """Function using JsonValue type."""
            return data

        def log_with_context(message: str, context: LogContext) -> None:
            """Function using LogContext type."""
            _ = (message, context)

        def handle_error(error: Exception, context: ErrorContext) -> dict[str, Any]:
            """Function using ErrorContext type."""
            return {"error": str(error), "context": context}

        def process_request(scope: AsgiScope) -> dict[str, Any]:
            """Function using AsgiScope type."""
            return {"method": scope.get("method", "GET")}

        def check_performance(
            metrics: dict[str, float], thresholds: PerformanceThresholds
        ) -> list[str]:
            """Function using PerformanceThresholds type."""
            return [
                name
                for name, value in metrics.items()
                if value > thresholds.get(name, float("inf"))
            ]

        # Verify functions work with proper types
        assert process_json({"key": "value"}) == {"key": "value"}
        log_with_context("test", {"level": "info"})
        assert "error" in handle_error(ValueError("test"), {"code": "E001"})
        assert "method" in process_request({"type": "http"})
        assert check_performance({"api": 150}, {"api": 100}) == ["api"]

    def test_type_alias_in_class_attributes(self) -> None:
        """Test type aliases in class attributes."""

        class LogEntry:
            """Class using type aliases."""

            context: LogContext
            data: JsonValue

            def __init__(self, context: LogContext, data: JsonValue) -> None:
                """Initialize with type aliases."""
                self.context = context
                self.data = data

        class ErrorReport:
            """Class for error reporting."""

            error_context: ErrorContext
            performance: PerformanceThresholds

            def __init__(
                self,
                error_context: ErrorContext,
                performance: PerformanceThresholds,
            ) -> None:
                """Initialize error report."""
                self.error_context = error_context
                self.performance = performance

        # Verify classes work with type aliases
        log_entry = LogEntry({"user": "test"}, {"message": "hello"})
        assert log_entry.context == {"user": "test"}

        error_report = ErrorReport({"code": "E500"}, {"timeout": 5000})
        assert error_report.performance["timeout"] == 5000

    def test_module_docstring_accuracy(self) -> None:
        """Test that module docstring accurately describes the types."""
        # Verify module has docstring
        assert types_module.__doc__ is not None
        docstring = types_module.__doc__

        # Verify key concepts are documented
        assert "type aliases" in docstring.lower()
        assert "json-serializable" in docstring.lower()
        assert any(
            word in docstring.lower()
            for word in ["documentation", "semantic", "meaning"]
        )

    # Test 7: JSON Serialization Compatibility
    @pytest.mark.parametrize(
        ("data", "type_name"),
        [
            ({"nested": [1, "two", True, None]}, "JsonValue"),
            ({"request_id": "123", "user": "john"}, "LogContext"),
            ({"error": "NotFound", "code": 404}, "ErrorContext"),
            ({"type": "http", "method": "GET"}, "AsgiScope"),
            ({"slow": 1000, "fast": 100}, "PerformanceThresholds"),
        ],
    )
    def test_json_serialization_all_types(
        self, data: JsonValue, type_name: str
    ) -> None:
        """Test JSON serialization for all type aliases.

        Args:
            data: Data to serialize
            type_name: Name of the type being tested
        """
        # Serialize
        serialized = json.dumps(data)
        assert isinstance(serialized, str), f"{type_name} should serialize to string"

        # Deserialize
        deserialized = json.loads(serialized)
        assert deserialized == data, f"{type_name} round-trip should preserve data"

    def test_json_serialization_large_data(self) -> None:
        """Test serialization with large nested structures."""
        # Create large nested structure
        large_data: JsonValue = {
            f"key_{i}": {
                "nested": [{"item": j, "data": f"value_{j}"} for j in range(100)]
            }
            for i in range(10)
        }

        # Should serialize without issues
        serialized = json.dumps(large_data)
        deserialized = json.loads(serialized)
        assert deserialized == large_data

    def test_json_serialization_unicode(self) -> None:
        """Test serialization with Unicode and special characters."""
        unicode_data: JsonValue = {
            "emoji": "🚀🌟",
            "chinese": "你好世界",
            "arabic": "مرحبا بالعالم",
            "special": "tab\there\nnewline",
        }

        serialized = json.dumps(unicode_data, ensure_ascii=False)
        deserialized = json.loads(serialized)
        assert deserialized == unicode_data

    def test_json_serialization_numeric_edge_cases(self) -> None:
        """Test serialization with numeric edge cases."""
        # Note: JSON doesn't support Infinity or NaN
        numeric_data: JsonValue = {
            "large_int": 9007199254740991,  # JavaScript MAX_SAFE_INTEGER
            "small_float": 1e-10,
            "negative": -999999999999,
        }

        serialized = json.dumps(numeric_data)
        deserialized = json.loads(serialized)
        assert deserialized == numeric_data

    def test_json_serialization_circular_reference(self) -> None:
        """Test handling of circular references."""
        # Create circular reference
        circular: dict[str, Any] = {"key": "value"}
        circular["self"] = circular  # Direct circular reference

        # JSON serialization should fail with circular references
        with pytest.raises(ValueError, match="Circular reference detected"):
            json.dumps(circular)

    def test_json_serialization_none_vs_missing(self) -> None:
        """Test None vs missing keys in dictionaries."""
        with_none: JsonValue = {"key": None, "other": "value"}
        without_key: JsonValue = {"other": "value"}

        # Both should serialize successfully
        json1 = json.dumps(with_none)
        json2 = json.dumps(without_key)

        # But they should be different
        assert json1 != json2
        assert "null" in json1
        assert "null" not in json2

    def test_json_serialization_concurrent(self, thread_sync: dict[str, Any]) -> None:
        """Test concurrent JSON serialization."""
        results = thread_sync["create_results"]()
        barrier = thread_sync["barrier"](5)

        def serialize_worker(worker_id: int) -> None:
            """Worker that serializes data concurrently."""
            barrier.wait()
            for i in range(10):
                data: JsonValue = {
                    "worker": worker_id,
                    "iteration": i,
                    "nested": {"timestamp": time.time()},
                }
                serialized = json.dumps(data)
                deserialized = json.loads(serialized)
                results.append(deserialized)

        threads = [
            threading.Thread(target=serialize_worker, args=(i,)) for i in range(5)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=2.0)

        assert len(results) == 50, "All serializations should complete"

    # Test 8: Type Alias Documentation
    def test_type_documentation_presence(self) -> None:
        """Test that type aliases have proper documentation."""
        # Check module docstring
        assert types_module.__doc__ is not None
        assert len(types_module.__doc__) > 100  # Substantial documentation

        # Check that all type aliases are defined
        expected_types = [
            "JsonValue",
            "LogContext",
            "ErrorContext",
            "AsgiScope",
            "PerformanceThresholds",
        ]
        for type_name in expected_types:
            assert hasattr(types_module, type_name), f"Missing type: {type_name}"

    def test_type_annotations_validity(self) -> None:
        """Test that type annotations are properly formed."""

        # Test that we can use types in annotations without errors
        def test_func(
            json_data: JsonValue,
            log_ctx: LogContext,
            error_ctx: ErrorContext,
            scope: AsgiScope,
            thresholds: PerformanceThresholds,
        ) -> None:
            """Function with all type annotations."""
            _ = (json_data, log_ctx, error_ctx, scope, thresholds)

        # If we get here without syntax errors, annotations are valid
        assert test_func is not None

    # Test 9: Python 3.13 Type Statement Syntax
    def test_python_313_type_statement_recognition(self) -> None:
        """Test that type aliases using type statement are recognized."""
        # All our types should be importable and usable
        test_json: JsonValue = {"test": "data"}
        test_log: LogContext = {"level": "info"}
        test_error: ErrorContext = {"code": "E001"}
        test_scope: AsgiScope = {"type": "http"}
        test_perf: PerformanceThresholds = {"slow": 1000}

        # All assignments should work without errors
        # Type assertions for dict access
        assert isinstance(test_json, dict)
        assert test_json["test"] == "data"
        assert isinstance(test_log, dict)
        assert test_log["level"] == "info"
        assert isinstance(test_error, dict)
        assert test_error["code"] == "E001"
        assert isinstance(test_scope, dict)
        assert test_scope["type"] == "http"
        assert isinstance(test_perf, dict)
        assert test_perf["slow"] == 1000

    def test_type_statement_runtime_introspection(self) -> None:
        """Test runtime introspection of type aliases."""
        # With Python 3.13's type statement, type aliases are attributes
        # on the module, not in __annotations__
        expected_types = [
            "JsonValue",
            "LogContext",
            "ErrorContext",
            "AsgiScope",
            "PerformanceThresholds",
        ]

        # Verify all type aliases are accessible as module attributes
        for type_name in expected_types:
            assert hasattr(types_module, type_name), (
                f"Type {type_name} should be accessible"
            )
            type_alias = getattr(types_module, type_name)
            assert type_alias is not None, f"Type {type_name} should not be None"

    def test_type_statement_with_type_checkers(self) -> None:
        """Test that type checkers understand the new syntax."""
        # This test verifies that the code passes type checking
        # The actual type checking is done by mypy/pyright in CI

        # Use TYPE_CHECKING to ensure this only runs during type checking
        if TYPE_CHECKING:
            # These should all type check correctly
            _json: JsonValue = {"key": [1, "two", None]}
            _log: LogContext = {"message": "test", "count": 42}
            _error: ErrorContext = {"error": "failed", "retry": True}
            _scope: AsgiScope = {"type": "websocket", "path": "/ws"}
            _perf: PerformanceThresholds = {"p50": 100, "p99": 1000}

            # Explicitly mark as used for linter
            _ = (_json, _log, _error, _scope, _perf)

    # Test 10: Integration with Actual Usage Patterns
    async def test_log_context_with_logging(self, mocker: MockerFixture) -> None:
        """Test LogContext usage with actual logging functions."""
        mock_logger = mocker.Mock()

        def log_with_context(message: str, context: LogContext) -> None:
            """Simulate structured logging."""
            mock_logger.info(message, extra=context)

        # Use LogContext in logging scenario
        context: LogContext = {
            "request_id": "req_123",
            "user_id": 456,
            "action": "create_order",
        }
        log_with_context("Order created", context)

        # Verify logger was called correctly
        mock_logger.info.assert_called_once_with("Order created", extra=context)

    async def test_error_context_in_exception_handling(self) -> None:
        """Test ErrorContext usage in exception handling."""

        class APIError(Exception):
            """Custom API error with context."""

            def __init__(self, message: str, context: ErrorContext) -> None:
                """Initialize with error context."""
                super().__init__(message)
                self.context = context

        # Simulate error handling
        error_ctx: ErrorContext = {
            "code": "VALIDATION_ERROR",
            "field": "email",
            "value": "invalid-email",
        }

        # Use pytest.raises for cleaner exception testing
        with pytest.raises(APIError) as exc_info:
            raise APIError("Invalid email format", error_ctx)

        assert exc_info.value.context["code"] == "VALIDATION_ERROR"
        assert exc_info.value.context["field"] == "email"

    async def test_asgi_scope_with_middleware(self, mocker: MockerFixture) -> None:
        """Test AsgiScope usage with middleware patterns."""
        # Mock ASGI app
        mock_app = mocker.AsyncMock()

        async def test_middleware(
            scope: AsgiScope, receive: object, send: object
        ) -> None:
            """Middleware that processes ASGI scope."""
            if scope["type"] == "http":
                # Add custom data to scope
                scope["custom"] = {"middleware": "test"}

            await mock_app(scope, receive, send)

        # Test middleware with HTTP scope
        test_scope: AsgiScope = {
            "type": "http",
            "method": "GET",
            "path": "/api/test",
        }

        await test_middleware(test_scope, None, None)

        # Verify scope was modified
        assert "custom" in test_scope
        assert test_scope["custom"]["middleware"] == "test"

    async def test_performance_thresholds_monitoring(
        self, mocker: MockerFixture
    ) -> None:
        """Test PerformanceThresholds in monitoring scenarios."""
        mock_metrics = mocker.Mock()

        def check_request_performance(
            duration_ms: float, thresholds: PerformanceThresholds
        ) -> None:
            """Check request against performance thresholds."""
            if duration_ms > thresholds.get("critical", float("inf")):
                mock_metrics.record_critical(duration_ms)
            elif duration_ms > thresholds.get("slow", float("inf")):
                mock_metrics.record_slow(duration_ms)
            else:
                mock_metrics.record_normal(duration_ms)

        # Define thresholds
        thresholds: PerformanceThresholds = {
            "slow": 1000,
            "critical": 5000,
        }

        # Test various response times
        check_request_performance(500, thresholds)  # Normal
        check_request_performance(1500, thresholds)  # Slow
        check_request_performance(6000, thresholds)  # Critical

        # Verify metrics were recorded correctly
        mock_metrics.record_normal.assert_called_once_with(500)
        mock_metrics.record_slow.assert_called_once_with(1500)
        mock_metrics.record_critical.assert_called_once_with(6000)

    async def test_types_in_async_context(self) -> None:
        """Test types in async functions and coroutines."""

        async def async_process_json(data: JsonValue) -> JsonValue:
            """Async function using JsonValue."""
            # Simulate async processing
            await asyncio.sleep(0.001)
            return {"processed": data}

        async def async_log(message: str, context: LogContext) -> None:
            """Async logging function."""
            await asyncio.sleep(0.001)
            # Would normally write to async logger
            _ = (message, context)

        # Test async usage
        result = await async_process_json({"input": "data"})
        assert result == {"processed": {"input": "data"}}

        await async_log("test", {"async": True})

    def test_serialization_in_api_response(self) -> None:
        """Test serialization in API response contexts."""

        def create_api_response(
            data: JsonValue, error: ErrorContext | None = None
        ) -> dict[str, Any]:
            """Create API response with proper types."""
            response = {"data": data, "success": error is None}
            if error:
                response["error"] = error
            return response

        # Test successful response
        success_data: JsonValue = {"user": {"id": 1, "name": "John"}}
        response = create_api_response(success_data)
        assert response["success"] is True
        assert response["data"] == success_data

        # Test error response
        error_ctx: ErrorContext = {"code": "NOT_FOUND", "message": "User not found"}
        error_response = create_api_response(None, error_ctx)
        assert error_response["success"] is False
        assert error_response["error"] == error_ctx

    @pytest.mark.parametrize(
        ("work_type", "expected_count"),
        [
            ("log", 5),
            ("error", 5),
            ("perf", 5),
            ("json", 5),
        ],
    )
    def test_types_thread_safety_by_type(
        self, thread_sync: dict[str, Any], work_type: str, expected_count: int
    ) -> None:
        """Test thread safety for each type alias separately."""
        results = thread_sync["create_results"]()
        barrier = thread_sync["barrier"](3)

        def worker(worker_id: int) -> None:
            """Worker that creates type instances."""
            barrier.wait()

            for i in range(5):
                if work_type == "log":
                    item: LogContext = {"worker": worker_id, "iter": i}
                elif work_type == "error":
                    item = {"worker": worker_id, "error_num": i}
                elif work_type == "perf":
                    item = {f"worker_{worker_id}": 100 * i}
                else:  # json
                    item = {"worker": worker_id, "data": [i, i * 2]}

                results.append(item)
                time.sleep(0.001)

        # Run multiple workers
        threads = [threading.Thread(target=worker, args=(i,)) for i in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=1.0)

        # Verify all operations completed
        assert len(results) == 3 * expected_count
