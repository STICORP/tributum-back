"""Tests for simplified error context sanitization."""

from typing import Any

import pytest

from src.core.constants import REDACTED
from src.core.error_context import (
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
class TestSensitiveFieldDetection:
    """Test sensitive field detection."""

    @pytest.mark.parametrize(
        ("field_name", "expected"),
        [
            # Sensitive fields
            ("password", True),
            ("PASSWORD", True),
            ("user_password", True),
            ("passwordHash", True),
            ("secret", True),
            ("api_key", True),
            ("apiKey", True),
            ("api-key", True),
            ("authorization", True),
            ("auth_token", True),
            ("private_key", True),
            ("access_key", True),
            ("session_id", True),
            ("ssn", True),
            ("social_security", True),
            ("card_number", True),
            ("cvv", True),
            # Non-sensitive fields
            ("username", False),
            ("email", False),
            ("name", False),
            ("id", False),
            ("timestamp", False),
            ("message", False),
        ],
    )
    def test_field_detection(self, field_name: str, expected: bool) -> None:
        """Test field name detection."""
        assert is_sensitive_field(field_name) == expected

    def test_configured_sensitive_fields(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that configured sensitive fields from settings are detected."""
        # Clear the cache to ensure we get fresh settings
        _get_sensitive_fields.cache_clear()

        # Mock settings to include a custom field not in the regex
        def mock_get_sensitive_fields() -> list[str]:
            return [
                "password",
                "token",
                "secret",
                "api_key",
                "authorization",
                "custom_sensitive_field",
            ]

        # Replace the cached function with our mock
        monkeypatch.setattr(
            "src.core.error_context._get_sensitive_fields", mock_get_sensitive_fields
        )

        # Test that the custom field is detected
        assert is_sensitive_field("custom_sensitive_field") is True
        assert is_sensitive_field("my_custom_sensitive_field_here") is True
        assert is_sensitive_field("CUSTOM_SENSITIVE_FIELD") is True

        # Test that non-sensitive fields are still not detected
        assert is_sensitive_field("username") is False
        assert is_sensitive_field("email") is False

    def test_header_detection(self) -> None:
        """Test header name detection."""
        assert is_sensitive_header("Authorization")
        assert is_sensitive_header("AUTHORIZATION")
        assert is_sensitive_header("cookie")
        assert is_sensitive_header("X-API-Key")
        assert not is_sensitive_header("Content-Type")
        assert not is_sensitive_header("User-Agent")


@pytest.mark.unit
class TestSanitization:
    """Test value sanitization."""

    def test_sanitize_simple_values(self) -> None:
        """Test sanitizing simple values."""
        # Sensitive field names cause redaction
        assert sanitize_value("my-secret-123", "password") == REDACTED
        assert sanitize_value("token123", "api_key") == REDACTED

        # Non-sensitive fields pass through
        assert sanitize_value("john@example.com", "email") == "john@example.com"
        assert sanitize_value(42, "user_id") == 42

    def test_sanitize_dict(self) -> None:
        """Test dictionary sanitization."""
        data = {
            "username": "john",
            "password": "secret123",
            "email": "john@example.com",
            "api_key": "sk-1234567890",
            "metadata": {
                "ip": "192.168.1.1",
                "session_token": "sess-abc123",
            },
        }

        sanitized = sanitize_dict(data)

        assert sanitized["username"] == "john"
        assert sanitized["password"] == REDACTED
        assert sanitized["email"] == "john@example.com"
        assert sanitized["api_key"] == REDACTED
        assert sanitized["metadata"]["ip"] == "192.168.1.1"
        assert sanitized["metadata"]["session_token"] == REDACTED

    def test_sanitize_list(self) -> None:
        """Test list sanitization."""
        data = {
            "users": [
                {"name": "John", "password": "secret1"},
                {"name": "Jane", "password": "secret2"},
            ]
        }

        sanitized = sanitize_dict(data)

        assert sanitized["users"][0]["name"] == "John"
        assert sanitized["users"][0]["password"] == REDACTED
        assert sanitized["users"][1]["name"] == "Jane"
        assert sanitized["users"][1]["password"] == REDACTED

    def test_sanitize_nested_structures(self) -> None:
        """Test deeply nested structure sanitization."""
        data = {
            "level1": {
                "level2": {
                    "level3": {
                        "secret_key": "very-secret",
                        "public_data": "visible",
                    }
                }
            }
        }

        sanitized = sanitize_dict(data)

        assert sanitized["level1"]["level2"]["level3"]["secret_key"] == REDACTED
        assert sanitized["level1"]["level2"]["level3"]["public_data"] == "visible"

    def test_sanitize_tuple(self) -> None:
        """Test tuple sanitization."""
        data = {
            "config": ("user", "password123", "localhost"),
            "safe_tuple": ("one", "two", "three"),
        }

        sanitized = sanitize_dict(data)

        # Tuples are sanitized but remain tuples
        assert isinstance(sanitized["config"], tuple)
        assert isinstance(sanitized["safe_tuple"], tuple)
        assert len(sanitized["config"]) == 3
        assert len(sanitized["safe_tuple"]) == 3

    def test_max_depth_protection(self) -> None:
        """Test maximum depth protection."""
        # Create circular reference
        data: dict[str, Any] = {"name": "test"}
        data["self"] = data

        # Should not crash, should handle gracefully
        sanitized = sanitize_dict(data)
        assert sanitized["name"] == "test"

    def test_sanitize_headers(self) -> None:
        """Test header sanitization."""
        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer token123",
            "X-API-Key": "sk-secret",
            "User-Agent": "Mozilla/5.0",
            "Cookie": "session=abc123",
        }

        sanitized = sanitize_headers(headers)

        assert sanitized["Content-Type"] == "application/json"
        assert sanitized["Authorization"] == REDACTED
        assert sanitized["X-API-Key"] == REDACTED
        assert sanitized["User-Agent"] == "Mozilla/5.0"
        assert sanitized["Cookie"] == REDACTED


@pytest.mark.unit
class TestErrorContext:
    """Test error context sanitization."""

    def test_basic_error_context(self) -> None:
        """Test basic error context creation."""
        error = ValueError("Something went wrong")
        context = sanitize_error_context(error)

        assert context["error_type"] == "ValueError"
        assert context["error_message"] == "Something went wrong"

    def test_error_context_with_additional_context(self) -> None:
        """Test error context with additional data."""
        error = ValueError("Invalid input")
        additional = {
            "user_id": 123,
            "password": "should-be-hidden",
            "action": "login",
        }

        context = sanitize_error_context(error, additional)

        assert context["error_type"] == "ValueError"
        assert context["user_id"] == 123
        assert context["password"] == REDACTED
        assert context["action"] == "login"

    def test_error_with_attributes(self) -> None:
        """Test error with custom attributes."""

        class CustomError(Exception):
            """Custom error for testing."""

            def __init__(self, message: str, code: str, secret_data: str) -> None:
                super().__init__(message)
                self.code = code
                self.secret_data = secret_data

        error = CustomError("Custom error", "ERR001", "sensitive")
        context = sanitize_error_context(error)

        assert context["error_type"] == "CustomError"
        assert context["error_attributes"]["code"] == "ERR001"
        assert context["error_attributes"]["secret_data"] == REDACTED


@pytest.mark.unit
class TestIntegration:
    """Test integration with logging."""

    def test_sanitization_prevents_sensitive_data_exposure(self) -> None:
        """Test that sanitization prevents sensitive data from being exposed."""
        # Create error with sensitive context
        sensitive_data = {
            "username": "john",
            "password": "super-secret-password",
            "api_key": "sk-1234567890",
            "connection_string": "postgresql://user:pass@localhost/db",
            "safe_field": "this-is-safe",
        }

        # Sanitize the data
        sanitized = sanitize_dict(sensitive_data)

        # Convert to string to simulate how it would appear in logs
        log_output = str(sanitized)

        # Verify sensitive data is not exposed
        assert "super-secret-password" not in log_output
        assert "sk-1234567890" not in log_output

        # Verify redacted placeholder is present
        assert REDACTED in log_output

        # Verify safe data is still present
        assert "john" in log_output
        assert "this-is-safe" in log_output

        # Connection string should be redacted due to field name
        assert sanitized["connection_string"] == REDACTED


@pytest.mark.unit
class TestSQLParameterSanitization:
    """Test SQL parameter sanitization functionality."""

    def test_sanitize_dict_params(self) -> None:
        """Test sanitizing dictionary SQL parameters."""
        params = {
            "user_id": 123,
            "username": "john",
            "password": "secret123",
            "api_key": "sk-12345",
            "email": "john@example.com",
        }

        sanitized = sanitize_sql_params(params)

        assert isinstance(sanitized, dict)
        assert sanitized["user_id"] == 123
        assert sanitized["username"] == "john"
        assert sanitized["password"] == REDACTED
        assert sanitized["api_key"] == REDACTED
        assert sanitized["email"] == "john@example.com"

    def test_sanitize_list_params(self) -> None:
        """Test that list parameters are passed through unchanged."""
        params = ["value1", "secret123", 42]

        sanitized = sanitize_sql_params(params)

        assert sanitized is params  # Should be the same object
        assert sanitized == ["value1", "secret123", 42]

    def test_sanitize_tuple_params(self) -> None:
        """Test that tuple parameters are passed through unchanged."""
        params = ("value1", "secret123", 42)

        sanitized = sanitize_sql_params(params)

        assert sanitized is params  # Should be the same object
        assert sanitized == ("value1", "secret123", 42)

    def test_sanitize_none_params(self) -> None:
        """Test that None parameters are handled correctly."""
        assert sanitize_sql_params(None) is None

    def test_sanitize_unknown_type(self) -> None:
        """Test that unknown parameter types are redacted."""

        # Pass an object that's not dict/list/tuple
        class CustomParams:
            pass

        params = CustomParams()

        sanitized = sanitize_sql_params(params)

        assert sanitized == REDACTED
