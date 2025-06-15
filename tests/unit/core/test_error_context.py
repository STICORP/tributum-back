"""Tests for error context utilities."""

from typing import cast

import pytest

from src.core.error_context import (
    REDACTED,
    enrich_error,
    is_sensitive_field,
    sanitize_context,
)
from src.core.exceptions import TributumError, ValidationError


class TestSensitiveFieldDetection:
    """Test cases for sensitive field detection."""

    def test_detects_password_fields(self) -> None:
        """Test that various password field names are detected."""
        password_fields = [
            "password",
            "PASSWORD",
            "user_password",
            "userPassword",
            "password_hash",
            "passwd",
            "pwd",
        ]

        for field in password_fields:
            assert is_sensitive_field(field), f"{field} should be sensitive"

    def test_detects_token_fields(self) -> None:
        """Test that various token field names are detected."""
        token_fields = [
            "token",
            "access_token",
            "refresh_token",
            "api_token",
            "auth_token",
            "bearer_token",
        ]

        for field in token_fields:
            assert is_sensitive_field(field), f"{field} should be sensitive"

    def test_detects_key_fields(self) -> None:
        """Test that various key field names are detected."""
        key_fields = [
            "key",
            "api_key",
            "apiKey",
            "private_key",
            "secret_key",
            "encryption_key",
        ]

        for field in key_fields:
            assert is_sensitive_field(field), f"{field} should be sensitive"

    def test_detects_auth_fields(self) -> None:
        """Test that various auth field names are detected."""
        auth_fields = [
            "auth",
            "authorization",
            "authentication",
            "auth_header",
            "credential",
            "credentials",
        ]

        for field in auth_fields:
            assert is_sensitive_field(field), f"{field} should be sensitive"

    def test_detects_financial_fields(self) -> None:
        """Test that financial field names are detected."""
        financial_fields = [
            "credit_card",
            "creditCard",
            "cvv",
            "pin",
            "ssn",
            "social_security",
        ]

        for field in financial_fields:
            assert is_sensitive_field(field), f"{field} should be sensitive"

    def test_non_sensitive_fields(self) -> None:
        """Test that normal fields are not marked as sensitive."""
        normal_fields = [
            "username",
            "email",
            "name",
            "id",
            "status",
            "message",
            "error",
            "data",
        ]

        for field in normal_fields:
            assert not is_sensitive_field(field), f"{field} should not be sensitive"

    def test_case_insensitive_detection(self) -> None:
        """Test that detection is case-insensitive."""
        assert is_sensitive_field("PASSWORD")
        assert is_sensitive_field("Password")
        assert is_sensitive_field("pAsSwOrD")


class TestSanitizeContext:
    """Test cases for context sanitization."""

    def test_sanitizes_flat_context(self) -> None:
        """Test sanitization of a flat dictionary."""
        context = {
            "username": "john_doe",
            "password": "secret123",
            "email": "john@example.com",
            "api_key": "sk_test_123",
        }

        sanitized = sanitize_context(context)

        assert sanitized["username"] == "john_doe"
        assert sanitized["password"] == REDACTED
        assert sanitized["email"] == "john@example.com"
        assert sanitized["api_key"] == REDACTED

    def test_sanitizes_nested_context(self) -> None:
        """Test sanitization of nested dictionaries."""
        context = {
            "user": {
                "name": "John",
                "credentials": {
                    "username": "john_doe",
                    "password": "secret123",
                },
            },
            "metadata": {"timestamp": "2024-01-01", "auth_token": "bearer_123"},
        }

        sanitized = sanitize_context(context)

        assert sanitized["user"]["name"] == "John"
        # The entire credentials object is redacted (key matches sensitive pattern)
        assert sanitized["user"]["credentials"] == REDACTED
        assert sanitized["metadata"]["timestamp"] == "2024-01-01"
        assert sanitized["metadata"]["auth_token"] == REDACTED

    def test_sanitizes_lists_with_dicts(self) -> None:
        """Test sanitization of lists containing dictionaries."""
        context = {
            "users": [
                {"username": "user1", "password": "pass1"},
                {"username": "user2", "api_key": "key2"},
            ],
            "tokens": ["public_token", "another_token"],
        }

        sanitized = sanitize_context(context)

        assert sanitized["users"][0]["username"] == "user1"
        assert sanitized["users"][0]["password"] == REDACTED
        assert sanitized["users"][1]["username"] == "user2"
        assert sanitized["users"][1]["api_key"] == REDACTED
        # The entire tokens list is redacted because the key matches sensitive pattern
        assert sanitized["tokens"] == REDACTED

    def test_original_context_not_modified(self) -> None:
        """Test that original context is not modified."""
        original = {
            "username": "john",
            "password": "secret",
            "nested": {"token": "abc123"},
        }

        # Keep a copy to verify immutability
        original_copy = {
            "username": "john",
            "password": "secret",
            "nested": {"token": "abc123"},
        }

        sanitized = sanitize_context(original)

        # Original should remain unchanged
        assert original == original_copy
        # Sanitized should be different
        assert sanitized != original
        assert sanitized["password"] == REDACTED
        assert sanitized["nested"]["token"] == REDACTED

    def test_handles_empty_context(self) -> None:
        """Test handling of empty context."""
        assert sanitize_context({}) == {}

    def test_handles_non_dict_input(self) -> None:
        """Test handling of non-dictionary input."""
        assert sanitize_context(None) is None
        assert sanitize_context("string") == "string"
        assert sanitize_context(123) == 123

    def test_sensitive_key_redacts_entire_value(self) -> None:
        """Test that sensitive keys redact their entire value."""
        context = {
            "user_data": {
                "name": "John",
                "email": "john@example.com",
            },
            "credentials": {
                "username": "john_doe",
                "permissions": ["read", "write"],
            },
            "api_key": "sk_test_12345",
            "session": {"id": "sess_123", "expires": "2024-01-01"},
        }

        sanitized = sanitize_context(context)

        # Non-sensitive keys preserve their structure
        assert sanitized["user_data"]["name"] == "John"
        assert sanitized["user_data"]["email"] == "john@example.com"

        # Sensitive keys have their entire value redacted
        assert sanitized["credentials"] == REDACTED
        assert sanitized["api_key"] == REDACTED
        assert sanitized["session"] == REDACTED

    def test_deeply_nested_sanitization(self) -> None:
        """Test sanitization of deeply nested structures."""
        context = {
            "level1": {
                "level2": {
                    "level3": {
                        "public_data": "visible",
                        "secret_key": "hidden",
                        "level4": [{"password": "nested_secret"}],
                    }
                }
            }
        }

        sanitized = sanitize_context(context)

        assert sanitized["level1"]["level2"]["level3"]["public_data"] == "visible"
        assert sanitized["level1"]["level2"]["level3"]["secret_key"] == REDACTED
        assert (
            sanitized["level1"]["level2"]["level3"]["level4"][0]["password"] == REDACTED
        )

    def test_sanitizes_nested_lists(self) -> None:
        """Test sanitization of lists containing lists."""
        context = {
            "matrix_data": [
                ["public", "data", "here"],
                [{"username": "user1"}, {"password": "secret123"}],
                [
                    ["nested", "list"],
                    [{"api_key": "hidden_key"}, {"public": "visible"}],
                ],
            ],
            "mixed_array": [
                "string_value",
                123,
                ["inner_list", {"token": "secret_token"}],
                [[["deeply", "nested"], {"credentials": "hidden"}]],
            ],
        }

        sanitized = sanitize_context(context)

        # First level list items
        assert sanitized["matrix_data"][0] == ["public", "data", "here"]
        assert sanitized["matrix_data"][1][0]["username"] == "user1"
        assert sanitized["matrix_data"][1][1]["password"] == REDACTED

        # Nested lists within lists
        assert sanitized["matrix_data"][2][0] == ["nested", "list"]
        assert sanitized["matrix_data"][2][1][0]["api_key"] == REDACTED
        assert sanitized["matrix_data"][2][1][1]["public"] == "visible"

        # Mixed array with deep nesting
        assert sanitized["mixed_array"][0] == "string_value"
        assert sanitized["mixed_array"][1] == 123
        assert sanitized["mixed_array"][2][0] == "inner_list"
        assert sanitized["mixed_array"][2][1]["token"] == REDACTED

        # Triple nested lists
        assert sanitized["mixed_array"][3][0][0] == ["deeply", "nested"]
        assert sanitized["mixed_array"][3][0][1]["credentials"] == REDACTED


class TestEnrichError:
    """Test cases for error enrichment."""

    def test_enriches_error_with_context(self) -> None:
        """Test adding context to an error."""
        error = TributumError("TEST_ERROR", "Test message")
        additional_context = {"user_id": 123, "operation": "update"}

        enriched = enrich_error(error, additional_context)

        assert enriched is error  # Same instance
        assert enriched.context["user_id"] == 123
        assert enriched.context["operation"] == "update"

    def test_enriches_error_with_existing_context(self) -> None:
        """Test enriching an error that already has context."""
        error = TributumError(
            "TEST_ERROR", "Test message", context={"existing": "value"}
        )
        additional_context = {"new_field": "new_value", "another": "data"}

        enriched = enrich_error(error, additional_context)

        assert enriched.context["existing"] == "value"
        assert enriched.context["new_field"] == "new_value"
        assert enriched.context["another"] == "data"

    def test_overwrites_duplicate_keys(self) -> None:
        """Test that additional context overwrites existing keys."""
        error = TributumError(
            "TEST_ERROR", "Test message", context={"key": "old_value", "keep": "this"}
        )
        additional_context = {"key": "new_value", "extra": "data"}

        enriched = enrich_error(error, additional_context)

        assert enriched.context["key"] == "new_value"  # Overwritten
        assert enriched.context["keep"] == "this"  # Preserved
        assert enriched.context["extra"] == "data"  # Added

    def test_handles_empty_additional_context(self) -> None:
        """Test enriching with empty context."""
        error = TributumError(
            "TEST_ERROR", "Test message", context={"existing": "value"}
        )

        enriched = enrich_error(error, {})

        assert enriched.context == {"existing": "value"}

    def test_works_with_specialized_exceptions(self) -> None:
        """Test enrichment works with specialized exception types."""
        error = ValidationError("Invalid input", context={"field": "email"})
        additional_context = {"value": "bad@", "line": 42}

        enriched = enrich_error(error, additional_context)

        assert enriched.context["field"] == "email"
        assert enriched.context["value"] == "bad@"
        assert enriched.context["line"] == 42

    def test_raises_for_non_tributum_error(self) -> None:
        """Test that non-TributumError raises TypeError."""
        regular_error = ValueError("Not a TributumError")

        with pytest.raises(TypeError) as exc_info:
            # Cast to bypass type checker - we're testing runtime type validation
            enrich_error(cast("TributumError", regular_error), {"context": "data"})

        assert "Error must be an instance of TributumError" in str(exc_info.value)

    def test_enrichment_preserves_other_attributes(self) -> None:
        """Test that enrichment doesn't affect other error attributes."""
        error = TributumError(
            "TEST_ERROR",
            "Test message",
            context={"original": "context"},
        )
        original_code = error.error_code
        original_message = error.message
        original_severity = error.severity

        enrich_error(error, {"new": "data"})

        assert error.error_code == original_code
        assert error.message == original_message
        assert error.severity == original_severity
