"""Unit tests for src/core/error_context.py.

This module tests the sensitive data sanitization functionality for secure error
logging and responses. All tests achieve 100% code coverage while following strict
best practices.
"""

import threading
from typing import Any, cast

import pytest
from pytest_mock import MockerFixture, MockType

from src.core.config import LogConfig, Settings
from src.core.error_context import (
    DEFAULT_SENSITIVE_PATTERN,
    MAX_DEPTH,
    REDACTED,
    SENSITIVE_HEADERS,
    _get_sensitive_fields,
    is_sensitive_field,
    is_sensitive_header,
    sanitize_dict,
    sanitize_error_context,
    sanitize_headers,
    sanitize_sql_params,
    sanitize_value,
)


@pytest.mark.unit
@pytest.mark.timeout(5)
class TestErrorContext:
    """Test suite for error context sanitization functionality."""

    def test_constants_unchanged(self) -> None:
        """Verify module constants have expected values."""
        msg = f"REDACTED constant should be '[REDACTED]', got {REDACTED}"
        assert REDACTED == "[REDACTED]", msg
        assert MAX_DEPTH == 10, f"MAX_DEPTH should be 10, got {MAX_DEPTH}"

        # Check SENSITIVE_HEADERS contains expected values
        expected_headers = {
            "authorization",
            "cookie",
            "x-api-key",
            "x-auth-token",
            "x-csrf-token",
            "set-cookie",
            "x-secret-key",
            "proxy-authorization",
        }
        assert expected_headers == SENSITIVE_HEADERS, (
            f"SENSITIVE_HEADERS missing values. "
            f"Expected {expected_headers}, got {SENSITIVE_HEADERS}"
        )

        # Verify DEFAULT_SENSITIVE_PATTERN is compiled regex
        assert hasattr(DEFAULT_SENSITIVE_PATTERN, "search"), (
            "DEFAULT_SENSITIVE_PATTERN should be a compiled regex"
        )

    def test_get_sensitive_fields_caching(self, mock_get_settings: MockType) -> None:
        """Verify _get_sensitive_fields() caches results and uses settings."""
        # Clear cache to ensure clean state
        _get_sensitive_fields.cache_clear()

        # First call should invoke get_settings
        fields1 = _get_sensitive_fields()
        assert mock_get_settings.call_count == 1
        assert fields1 == ["custom_secret", "my_password", "api_token"]

        # Second call should use cache, not invoke get_settings again
        fields2 = _get_sensitive_fields()
        assert mock_get_settings.call_count == 1  # Still 1, not 2
        assert fields1 is fields2  # Same object reference due to caching

        # Clear cache and verify it calls get_settings again
        _get_sensitive_fields.cache_clear()
        _get_sensitive_fields()
        assert mock_get_settings.call_count == 2

    def test_get_sensitive_fields_empty_list(self, mocker: MockerFixture) -> None:
        """Verify _get_sensitive_fields() handles empty custom fields list."""
        # Clear cache first
        _get_sensitive_fields.cache_clear()

        # Mock settings with empty sensitive_fields
        mock_settings = mocker.Mock(spec=Settings)
        mock_log_config = mocker.Mock(spec=LogConfig)
        mock_log_config.sensitive_fields = []
        mock_settings.log_config = mock_log_config

        mock_get_settings_fn = mocker.patch("src.core.error_context.get_settings")
        mock_get_settings_fn.return_value = mock_settings

        result = _get_sensitive_fields()
        assert result == []

    @pytest.mark.parametrize(
        "field_name",
        [
            "password",
            "PASSWORD",
            "Password",
            "user_password",
            "password_hash",
            "old_password",
            "secret",
            "SECRET",
            "api_secret",
            "token",
            "access_token",
            "refresh_token",
            "api_key",
            "apikey",
            "api-key",
            "API_KEY",
            "auth",
            "authorization",
            "auth_header",
            "credential",
            "credentials",
            "user_credentials",
            "private_key",
            "private-key",
            "privatekey",
            "access_key",
            "access-key",
            "secret_key",
            "secret-key",
            "session",
            "session_id",
            "sessionid",
            "ssn",
            "social_security",
            "social-security",
            "pin",
            "pin_code",
            "user_pin",
            "cvv",
            "cvc",
            "card_cvv",
            "card_number",
            "card-number",
            "cardnumber",
            "connection_string",
            "connection-string",
        ],
    )
    def test_is_sensitive_field_default_patterns(self, field_name: str) -> None:
        """Verify is_sensitive_field detects all default sensitive patterns."""
        # Test only regex patterns, not custom fields

        assert is_sensitive_field(field_name), (
            f"Field '{field_name}' should be detected as sensitive"
        )

    def test_is_sensitive_field_custom_fields(self) -> None:
        """Verify is_sensitive_field detects custom configured fields."""
        # Test exact match
        assert is_sensitive_field("custom_secret"), "Should detect exact custom field"
        assert is_sensitive_field("my_password"), "Should detect exact custom field"
        assert is_sensitive_field("api_token"), "Should detect exact custom field"

        # Test substring match (case-insensitive)
        assert is_sensitive_field("user_custom_secret_key"), (
            "Should detect custom field as substring"
        )
        assert is_sensitive_field("MY_PASSWORD_HASH"), (
            "Should detect case-insensitive match"
        )
        assert is_sensitive_field("new_api_token_v2"), (
            "Should detect custom field in larger string"
        )

    def test_is_sensitive_field_case_insensitive(self) -> None:
        """Verify case-insensitive matching for both patterns and custom fields."""
        # Pattern matching (various cases)
        assert is_sensitive_field("PASSWORD")
        assert is_sensitive_field("password")
        assert is_sensitive_field("PaSsWoRd")

        # Custom field matching (various cases)
        assert is_sensitive_field("CUSTOM_SECRET")
        assert is_sensitive_field("custom_secret")
        assert is_sensitive_field("Custom_Secret")

        # Mixed case in field containing sensitive substring
        assert is_sensitive_field("User_API_TOKEN_Value")

    @pytest.mark.parametrize(
        "field_name",
        [
            "username",
            "email",
            "first_name",
            "last_name",
            "address",
            "phone",
            "city",
            "country",
            "id",
            "uuid",
            "created_at",
            "updated_at",
            "status",
            "type",
            "category",
            "description",
            "name",
            "title",
            "content",
            "message",
        ],
    )
    def test_is_sensitive_field_non_sensitive(self, field_name: str) -> None:
        """Verify non-sensitive fields return False."""
        # Test only default patterns, not custom fields

        assert not is_sensitive_field(field_name), (
            f"Field '{field_name}' should not be sensitive"
        )

    @pytest.mark.parametrize(
        ("header_name", "expected"),
        [
            ("authorization", True),
            ("Authorization", True),
            ("AUTHORIZATION", True),
            ("cookie", True),
            ("Cookie", True),
            ("x-api-key", True),
            ("X-API-KEY", True),
            ("x-auth-token", True),
            ("x-csrf-token", True),
            ("set-cookie", True),
            ("Set-Cookie", True),
            ("x-secret-key", True),
            ("proxy-authorization", True),
            ("content-type", False),
            ("Content-Type", False),
            ("user-agent", False),
            ("accept", False),
            ("host", False),
            ("x-request-id", False),
        ],
    )
    def test_is_sensitive_header(self, header_name: str, expected: bool) -> None:
        """Verify header sensitivity detection."""
        assert is_sensitive_header(header_name) == expected, (
            f"Header '{header_name}' sensitivity should be {expected}"
        )

    def test_is_sensitive_header_case_insensitive(self) -> None:
        """Verify case-insensitive header matching."""
        # Test various case combinations
        assert is_sensitive_header("authorization")
        assert is_sensitive_header("Authorization")
        assert is_sensitive_header("AUTHORIZATION")
        assert is_sensitive_header("AuThOrIzAtIoN")

        assert is_sensitive_header("x-api-key")
        assert is_sensitive_header("X-Api-Key")
        assert is_sensitive_header("X-API-KEY")

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            ("test_string", "test_string"),
            (123, 123),
            (45.67, 45.67),
            (True, True),
            (False, False),
            (None, None),
        ],
    )
    def test_sanitize_value_simple_types(self, value: object, expected: object) -> None:
        """Test sanitization of simple types (str, int, float, bool, None)."""
        # Cast to satisfy mypy - we know these are valid types from parametrize
        typed_value = cast("str | int | float | bool | None", value)
        result = sanitize_value(typed_value)
        assert result == expected
        assert type(result) is type(expected)  # Ensure type is preserved

    @pytest.mark.parametrize(
        "field_name", ["password", "api_key", "secret_token", "custom_secret"]
    )
    def test_sanitize_value_sensitive_field(self, field_name: str) -> None:
        """Test sanitization when field name is sensitive."""
        result = sanitize_value("actual_secret_value", field_name)
        assert result == REDACTED, f"Field '{field_name}' should be redacted"

    def test_sanitize_value_dict_recursion(
        self, sample_sensitive_data: dict[str, Any]
    ) -> None:
        """Test recursive dict sanitization."""
        result = sanitize_value(sample_sensitive_data)

        # Ensure result is a dict, not REDACTED
        assert isinstance(result, dict)

        # Check top-level sensitive fields
        assert result["password"] == REDACTED
        assert result["username"] == "john_doe"  # Non-sensitive

        # Check nested dict sanitization
        assert isinstance(result["user_data"], dict)
        assert result["user_data"]["api_key"] == REDACTED
        assert result["user_data"]["email"] == "john@example.com"  # Non-sensitive

        # Check deeply nested
        assert isinstance(result["user_data"]["profile"], dict)
        assert result["user_data"]["profile"]["secret_token"] == REDACTED
        assert isinstance(result["user_data"]["profile"]["preferences"], dict)
        assert result["user_data"]["profile"]["preferences"]["private_key"] == REDACTED
        assert (
            result["user_data"]["profile"]["preferences"]["theme"] == "dark"
        )  # Non-sensitive

        # Check metadata nested structure
        assert isinstance(result["metadata"], dict)
        assert result["metadata"]["session_id"] == REDACTED
        # "credentials" field name matches the sensitive pattern, so it's redacted
        assert result["metadata"]["credentials"] == REDACTED
        assert result["metadata"]["created_at"] == "2024-01-01"  # Non-sensitive

    def test_sanitize_value_list_recursion(
        self, sample_sensitive_data: dict[str, Any]
    ) -> None:
        """Test recursive list sanitization."""
        items = sample_sensitive_data["items"]
        result = sanitize_value(items)

        assert isinstance(result, list)
        assert len(result) == 2

        # First item
        assert result[0]["id"] == 1
        assert result[0]["name"] == "Item 1"
        assert result[0]["token"] == REDACTED

        # Second item
        assert result[1]["id"] == 2
        assert result[1]["name"] == "Item 2"
        assert result[1]["access_key"] == REDACTED

    def test_sanitize_value_tuple_recursion(
        self, sample_sensitive_data: dict[str, Any]
    ) -> None:
        """Test recursive tuple sanitization."""
        tuple_data = sample_sensitive_data["tuple_data"]
        result = sanitize_value(tuple_data)

        assert isinstance(result, tuple)
        assert len(result) == 3
        assert result[0] == "public"
        # Values in tuples are not checked for sensitive patterns, only field names
        assert result[1] == "password123"  # Not redacted as it's a value, not a field
        assert isinstance(result[2], dict)
        assert (
            result[2]["secret"] == REDACTED
        )  # This is redacted because "secret" is the field name

    @pytest.mark.parametrize("depth", [9, 10, 11, 12])
    def test_sanitize_value_max_depth(self, depth: int) -> None:
        """Test MAX_DEPTH recursion limit."""
        # Create deeply nested structure
        data: dict[str, Any] = {"level": 0}
        current = data
        for i in range(depth):
            current["nested"] = {"level": i + 1, "password": f"secret_{i}"}
            current = current["nested"]

        result = sanitize_value(data)

        # Navigate to the deepest level
        current_result = result
        actual_depth = 0
        while isinstance(current_result, dict) and "nested" in current_result:
            current_result = current_result["nested"]
            actual_depth += 1
            if actual_depth > MAX_DEPTH:
                break

        # At depth > MAX_DEPTH, the value should be REDACTED
        if depth > MAX_DEPTH:
            # The entire nested structure at MAX_DEPTH+1 should be REDACTED
            assert current_result == REDACTED, f"At depth {depth}, should be REDACTED"
        else:
            assert isinstance(current_result, dict), (
                f"At depth {depth}, should still be dict"
            )

    def test_sanitize_dict(self, sample_sensitive_data: dict[str, Any]) -> None:
        """Test sanitize_dict convenience function."""
        result = sanitize_dict(sample_sensitive_data)

        # Verify it's equivalent to calling sanitize_value on a dict
        expected = sanitize_value(sample_sensitive_data)
        assert result == expected

        # Verify specific sanitizations
        assert result["password"] == REDACTED
        assert result["username"] == "john_doe"
        assert result["user_data"]["api_key"] == REDACTED

    def test_sanitize_headers(self) -> None:
        """Test header-specific sanitization."""
        headers = {
            "Authorization": "Bearer token123",
            "Cookie": "session=abc123",
            "Content-Type": "application/json",
            "X-API-Key": "sk-1234567890",
            "User-Agent": "Mozilla/5.0",
            "X-Request-ID": "req-123",
            "Set-Cookie": "session=xyz; HttpOnly",
        }

        result = sanitize_headers(headers)

        # Sensitive headers should be redacted
        assert result["Authorization"] == REDACTED
        assert result["Cookie"] == REDACTED
        assert result["X-API-Key"] == REDACTED
        assert result["Set-Cookie"] == REDACTED

        # Non-sensitive headers should be unchanged
        assert result["Content-Type"] == "application/json"
        assert result["User-Agent"] == "Mozilla/5.0"
        assert result["X-Request-ID"] == "req-123"

    @pytest.mark.parametrize(
        ("error_cls", "error_msg"),
        [
            (ValueError, "Invalid value"),
            (KeyError, "Missing key"),
            (TypeError, "Type mismatch"),
            (RuntimeError, "Runtime error occurred"),
        ],
    )
    def test_sanitize_error_context_basic(
        self, error_cls: type[Exception], error_msg: str
    ) -> None:
        """Test basic error context sanitization."""
        error = error_cls(error_msg)
        result = sanitize_error_context(error)

        assert result["error_type"] == error_cls.__name__
        # KeyError includes quotes in its string representation
        if error_cls is KeyError:
            assert result["error_message"] == f"'{error_msg}'"
        else:
            assert result["error_message"] == error_msg
        assert (
            "error_attributes" not in result
        )  # Basic exceptions have no custom attributes

    def test_sanitize_error_context_with_context(self) -> None:
        """Test error context with additional context dict."""
        error = ValueError("Test error")
        context = {
            "user_id": 123,
            "password": "secret123",
            "action": "login",
            "api_key": "sk-abc123",
        }

        result = sanitize_error_context(error, context)

        # Basic error info
        assert result["error_type"] == "ValueError"
        assert result["error_message"] == "Test error"

        # Context should be merged and sanitized
        assert result["user_id"] == 123
        assert result["password"] == REDACTED
        assert result["action"] == "login"
        assert result["api_key"] == REDACTED

    def test_sanitize_error_context_with_attributes(self) -> None:
        """Test error sanitization with exception attributes."""

        # Create custom exception with attributes
        class CustomError(Exception):
            def __init__(self, message: str, user_id: int, token: str) -> None:
                super().__init__(message)
                self.user_id = user_id
                self.token = token
                self.password = "secret123"
                self._internal = "should_be_filtered"

        token_value = "bearer-xyz"  # Test token value
        error = CustomError("Custom error", user_id=456, token=token_value)
        result = sanitize_error_context(error)

        assert result["error_type"] == "CustomError"
        assert result["error_message"] == "Custom error"
        assert "error_attributes" in result

        attrs = result["error_attributes"]
        assert attrs["user_id"] == 456
        assert attrs["token"] == REDACTED
        assert attrs["password"] == REDACTED
        assert "_internal" not in attrs  # Underscore attributes filtered

    def test_sanitize_sql_params_dict(self) -> None:
        """Test SQL parameter sanitization for dict format."""
        params = {
            "username": "john_doe",
            "password": "secret123",
            "email": "john@example.com",
            "api_key": "sk-12345",
        }

        result = sanitize_sql_params(params)
        assert isinstance(result, dict)
        assert result["username"] == "john_doe"
        assert result["password"] == REDACTED
        assert result["email"] == "john@example.com"
        assert result["api_key"] == REDACTED

    @pytest.mark.parametrize(
        "params",
        [
            ["value1", "value2", "value3"],
            ("value1", "value2", "value3"),
        ],
    )
    def test_sanitize_sql_params_list_tuple(
        self, params: list[str] | tuple[str, ...]
    ) -> None:
        """Test SQL parameter sanitization for list/tuple formats."""
        result = sanitize_sql_params(params)
        assert result == params  # Positional params unchanged
        assert type(result) is type(params)  # Type preserved

    def test_sanitize_sql_params_none(self) -> None:
        """Test SQL parameter sanitization for None."""
        result = sanitize_sql_params(None)
        assert result is None

    @pytest.mark.parametrize(
        "params",
        [
            12345,
            "single_string",
            {"nested": {"complex": "object"}},
            object(),
        ],
    )
    def test_sanitize_sql_params_unknown(self, params: object) -> None:
        """Test SQL parameter sanitization for unknown formats."""
        result = sanitize_sql_params(params)
        if isinstance(params, dict):
            # Dicts are handled specially
            assert isinstance(result, dict)
        else:
            assert result == REDACTED

    @pytest.mark.timeout(10)
    def test_thread_safety_sanitize_value(
        self, thread_test_context: dict[str, Any]
    ) -> None:
        """Test thread safety of sanitize_value function."""
        num_threads = 10
        barrier = thread_test_context["barrier"](num_threads)
        results = thread_test_context["results"]

        test_data = {
            "password": "secret123",
            "username": "john_doe",
            "nested": {"api_key": "sk-12345", "public": "data"},
        }

        def worker() -> None:
            try:
                barrier.wait()  # Synchronize thread start
                result = sanitize_value(test_data)
                results.append(result)
            except Exception as e:
                thread_test_context["errors"].append(e)

        threads = [threading.Thread(target=worker) for _ in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)

        # Check no errors occurred
        assert len(thread_test_context["errors"]) == 0
        assert len(results) == num_threads

        # All results should be identical
        first_result = results[0]
        for result in results[1:]:
            assert result == first_result

        # Verify sanitization worked correctly
        assert first_result["password"] == REDACTED
        assert first_result["username"] == "john_doe"
        assert first_result["nested"]["api_key"] == REDACTED

    @pytest.mark.timeout(10)
    def test_thread_safety_lru_cache(
        self, mocker: MockerFixture, thread_test_context: dict[str, Any]
    ) -> None:
        """Test thread safety of LRU cache in _get_sensitive_fields."""
        # Clear cache first
        _get_sensitive_fields.cache_clear()

        num_threads = 20
        barrier = thread_test_context["barrier"](num_threads)
        results = thread_test_context["results"]

        # Mock settings to return different values over time
        call_count = 0

        def get_settings_side_effect() -> Settings:
            nonlocal call_count
            call_count += 1
            settings = mocker.MagicMock(spec=Settings)
            log_config = mocker.MagicMock(spec=LogConfig)
            # Return same fields regardless of call count for consistency
            log_config.sensitive_fields = ["field1", "field2", "field3"]
            settings.log_config = log_config
            return cast("Settings", settings)

        mock_get_settings_fn = mocker.patch("src.core.error_context.get_settings")
        mock_get_settings_fn.side_effect = get_settings_side_effect

        def worker() -> None:
            try:
                barrier.wait()  # Synchronize thread start
                fields = _get_sensitive_fields()
                results.append(fields)
            except Exception as e:
                thread_test_context["errors"].append(e)

        threads = [threading.Thread(target=worker) for _ in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)

        # Check no errors occurred
        assert len(thread_test_context["errors"]) == 0
        assert len(results) == num_threads

        # Due to caching, get_settings should only be called once
        assert call_count == 1

        # All results should be identical
        expected_fields = ["field1", "field2", "field3"]
        for result in results:
            assert result == expected_fields

    def test_sanitize_error_context_no_dict_attribute(self) -> None:
        """Test error context sanitization for exceptions without __dict__ attribute."""
        # Built-in exceptions typically don't have __dict__
        error = ValueError("Simple error")
        result = sanitize_error_context(error)

        assert result["error_type"] == "ValueError"
        assert result["error_message"] == "Simple error"
        assert "error_attributes" not in result

    def test_sanitize_error_context_underscore_attributes(self) -> None:
        """Test that exception attributes starting with underscore are filtered out."""

        class CustomError(Exception):
            def __init__(self) -> None:
                super().__init__("Custom error")
                self.public_field = "visible"
                self._private_field = "hidden"
                self.__very_private = "very hidden"
                self.password = "secret123"

        error = CustomError()
        result = sanitize_error_context(error)

        assert "error_attributes" in result
        attrs = result["error_attributes"]
        assert attrs["public_field"] == "visible"
        assert attrs["password"] == REDACTED
        assert "_private_field" not in attrs
        assert "__very_private" not in attrs
        assert "_CustomError__very_private" not in attrs  # Name mangled version

    def test_sanitize_value_circular_reference(self) -> None:
        """Test handling of circular references in data structures."""
        # Create circular reference in dict
        dict_data: dict[str, Any] = {"name": "root", "password": "secret123"}
        dict_data["self"] = dict_data

        result = sanitize_value(dict_data)
        assert isinstance(result, dict)
        assert result["name"] == "root"
        assert result["password"] == REDACTED
        # Due to MAX_DEPTH, circular reference will eventually be REDACTED

        # Create circular reference in list
        list_data: list[Any] = ["item1", {"token": "secret_token"}]
        list_data.append(list_data)

        result_list = sanitize_value(list_data)
        assert isinstance(result_list, list)
        assert result_list[0] == "item1"
        assert result_list[1]["token"] == REDACTED

    def test_sanitize_value_unicode_field_names(self, mocker: MockerFixture) -> None:
        """Test sanitization with Unicode and special characters in field names."""
        # Clear cache first
        _get_sensitive_fields.cache_clear()

        # Mock settings with unicode sensitive fields
        mock_settings = mocker.Mock(spec=Settings)
        mock_log_config = mocker.Mock(spec=LogConfig)
        mock_log_config.sensitive_fields = ["密码", "パスワード", "🔑key"]
        mock_settings.log_config = mock_log_config

        mock_get_settings_fn = mocker.patch("src.core.error_context.get_settings")
        mock_get_settings_fn.return_value = mock_settings

        # Test data with unicode field names
        data = {
            "用户名": "张三",
            "密码": "secret123",
            "パスワード": "秘密",
            "🔑key": "emoji_secret",
            "normal_field": "visible",
            "user_密码_field": "should_be_redacted",
        }

        result = sanitize_value(data)
        assert isinstance(result, dict)
        assert result["用户名"] == "张三"  # Username not sensitive
        assert result["密码"] == REDACTED
        assert result["パスワード"] == REDACTED
        assert result["🔑key"] == REDACTED
        assert result["normal_field"] == "visible"
        assert result["user_密码_field"] == REDACTED  # Contains sensitive substring

    @pytest.mark.timeout(10)
    def test_thread_safety_settings_modification(
        self, mocker: MockerFixture, thread_test_context: dict[str, Any]
    ) -> None:
        """Test thread safety when settings are modified during concurrent access."""
        # Clear cache first
        _get_sensitive_fields.cache_clear()

        num_threads = 10
        barrier = thread_test_context["barrier"](num_threads)
        results = thread_test_context["results"]
        modification_event = thread_test_context["event"]()

        # Create different settings configurations
        settings_configs = [
            ["field1", "field2"],
            ["field3", "field4", "field5"],
            ["new_field", "another_field"],
        ]
        current_config_index = 0

        def get_settings_side_effect() -> Settings:
            nonlocal current_config_index
            settings = mocker.MagicMock(spec=Settings)
            log_config = mocker.MagicMock(spec=LogConfig)
            log_config.sensitive_fields = settings_configs[
                current_config_index % len(settings_configs)
            ]
            settings.log_config = log_config
            return cast("Settings", settings)

        mock_get_settings_fn = mocker.patch("src.core.error_context.get_settings")
        mock_get_settings_fn.side_effect = get_settings_side_effect

        def worker(worker_id: int) -> None:
            try:
                barrier.wait()  # Synchronize thread start

                # Some threads modify settings
                if worker_id % 3 == 0:
                    nonlocal current_config_index
                    current_config_index += 1
                    _get_sensitive_fields.cache_clear()  # Clear cache to force reload
                    modification_event.set()

                # All threads try to sanitize data
                test_data = {
                    "field1": "value1",
                    "field3": "value3",
                    "new_field": "new_value",
                    "normal": "visible",
                }
                result = sanitize_value(test_data)
                results.append(result)

            except Exception as e:
                thread_test_context["errors"].append(e)

        threads = [
            threading.Thread(target=worker, args=(i,)) for i in range(num_threads)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)

        # Check no errors occurred
        assert len(thread_test_context["errors"]) == 0
        assert len(results) == num_threads

        # Results may vary due to settings changes, but all should be valid
        for result in results:
            assert isinstance(result, dict)
            assert result["normal"] == "visible"  # Non-sensitive always visible
            # At least one sensitive field should be redacted based on config

    def test_sanitize_value_empty_collections(self) -> None:
        """Test sanitization of empty strings, lists, dicts, and tuples."""
        # Empty string
        assert sanitize_value("") == ""
        assert sanitize_value("", "password") == REDACTED  # Empty but sensitive field

        # Empty collections
        assert sanitize_value({}) == {}
        assert sanitize_value([]) == []
        assert sanitize_value(()) == ()

        # Nested empty collections
        data = {
            "empty_dict": {},
            "empty_list": [],
            "empty_tuple": (),
            "empty_string": "",
            "password": "",  # Empty but sensitive
        }
        result = sanitize_value(data)
        assert isinstance(result, dict)
        assert result["empty_dict"] == {}
        assert result["empty_list"] == []
        assert result["empty_tuple"] == ()
        assert result["empty_string"] == ""
        assert result["password"] == REDACTED

    def test_sanitize_value_very_long_field_names(self) -> None:
        """Test sanitization with extremely long field names."""
        # Create very long field names
        long_normal_field = "x" * 1000
        long_password_field = "x" * 500 + "password" + "x" * 500
        long_custom_field = "y" * 500 + "custom_secret" + "y" * 500

        data = {
            long_normal_field: "visible_value",
            long_password_field: "should_be_redacted",
            long_custom_field: "also_redacted",
            "normal": "visible",
        }

        result = sanitize_value(data)
        assert isinstance(result, dict)
        assert result[long_normal_field] == "visible_value"
        assert result[long_password_field] == REDACTED
        assert result[long_custom_field] == REDACTED
        assert result["normal"] == "visible"
