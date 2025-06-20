"""Tests for error context utilities."""

from typing import cast

import pytest
from pytest_mock import MockerFixture

from src.core.error_context import (
    REDACTED,
    SENSITIVE_HEADERS,
    capture_request_context,
    enrich_error,
    is_sensitive_field,
    sanitize_context,
)
from src.core.exceptions import TributumError, ValidationError


@pytest.mark.unit
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


@pytest.mark.unit
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


@pytest.mark.unit
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


@pytest.mark.unit
class TestCaptureRequestContext:
    """Test cases for HTTP request context capture."""

    def test_captures_basic_request_info(self, mocker: MockerFixture) -> None:
        """Test capturing basic request information."""
        # Create a mock request
        request = mocker.Mock()
        request.method = "POST"
        request.url.path = "/api/users"
        request.url.scheme = "https"
        request.url.hostname = "api.example.com"
        request.url.port = 443
        request.headers = {"content-type": "application/json", "user-agent": "test"}
        request.query_params = {}
        request.client = mocker.Mock(host="192.168.1.1", port=12345)

        context = capture_request_context(request)

        assert context["method"] == "POST"
        assert context["path"] == "/api/users"
        assert context["headers"]["content-type"] == "application/json"
        assert context["headers"]["user-agent"] == "test"
        assert context["client"]["host"] == "192.168.1.1"
        assert context["client"]["port"] == 12345
        assert context["url"]["scheme"] == "https"
        assert context["url"]["hostname"] == "api.example.com"
        assert context["url"]["port"] == 443
        assert context["url"]["path"] == "/api/users"

    def test_filters_sensitive_headers(self, mocker: MockerFixture) -> None:
        """Test that sensitive headers are redacted."""
        request = mocker.Mock()
        request.method = "GET"
        request.url.path = "/api/data"
        request.url.scheme = "http"
        request.url.hostname = "localhost"
        request.url.port = 8000
        request.headers = {
            "authorization": "Bearer secret-token",
            "cookie": "session=12345",
            "x-api-key": "sk_test_123",
            "content-type": "application/json",
            "user-agent": "test-client",
        }
        request.query_params = {}
        request.client = None

        context = capture_request_context(request)

        # Sensitive headers should be redacted
        assert context["headers"]["authorization"] == REDACTED
        assert context["headers"]["cookie"] == REDACTED
        assert context["headers"]["x-api-key"] == REDACTED
        # Non-sensitive headers should be preserved
        assert context["headers"]["content-type"] == "application/json"
        assert context["headers"]["user-agent"] == "test-client"

    def test_sanitizes_query_parameters(self, mocker: MockerFixture) -> None:
        """Test that query parameters are sanitized."""
        request = mocker.Mock()
        request.method = "GET"
        request.url.path = "/api/search"
        request.url.scheme = "http"
        request.url.hostname = "localhost"
        request.url.port = 8000
        request.headers = {}
        request.query_params = {
            "q": "search term",
            "api_key": "secret_key_123",
            "page": "1",
            "password": "should_be_hidden",
        }
        request.client = None

        context = capture_request_context(request)

        assert "query_params" in context
        assert context["query_params"]["q"] == "search term"
        assert context["query_params"]["api_key"] == REDACTED
        assert context["query_params"]["page"] == "1"
        assert context["query_params"]["password"] == REDACTED

    def test_handles_none_request(self) -> None:
        """Test handling of None request (not in HTTP context)."""
        context = capture_request_context(None)
        assert context == {}

    def test_handles_missing_client_info(self, mocker: MockerFixture) -> None:
        """Test handling when client info is not available."""
        request = mocker.Mock()
        request.method = "GET"
        request.url.path = "/health"
        request.url.scheme = "http"
        request.url.hostname = "localhost"
        request.url.port = 8000
        request.headers = {}
        request.query_params = {}
        request.client = None  # No client info

        context = capture_request_context(request)

        assert "client" not in context

    def test_handles_empty_query_params(self, mocker: MockerFixture) -> None:
        """Test handling when there are no query parameters."""
        request = mocker.Mock()
        request.method = "GET"
        request.url.path = "/api/users"
        request.url.scheme = "http"
        request.url.hostname = "localhost"
        request.url.port = 8000
        request.headers = {"accept": "application/json"}
        request.query_params = {}
        request.client = mocker.Mock(host="127.0.0.1", port=54321)

        context = capture_request_context(request)

        assert "query_params" not in context

    def test_case_insensitive_header_filtering(self, mocker: MockerFixture) -> None:
        """Test that header filtering is case-insensitive."""
        request = mocker.Mock()
        request.method = "POST"
        request.url.path = "/api/login"
        request.url.scheme = "https"
        request.url.hostname = "api.example.com"
        request.url.port = 443
        request.headers = {
            "Authorization": "Bearer token",  # Title case
            "COOKIE": "session=abc",  # Upper case
            "X-Api-Key": "key123",  # Mixed case
            "Content-Type": "application/json",
        }
        request.query_params = {}
        request.client = None

        context = capture_request_context(request)

        # All variations should be redacted
        assert context["headers"]["Authorization"] == REDACTED
        assert context["headers"]["COOKIE"] == REDACTED
        assert context["headers"]["X-Api-Key"] == REDACTED
        assert context["headers"]["Content-Type"] == "application/json"

    def test_handles_request_attribute_errors(self, mocker: MockerFixture) -> None:
        """Test graceful handling when request attributes raise errors."""
        request = mocker.Mock()
        # Make some attributes raise exceptions
        request.method = "GET"
        request.url.path = "/api/test"
        request.url.scheme = "http"
        request.url.hostname = "localhost"
        request.url.port = 8000
        request.headers = mocker.Mock(side_effect=AttributeError("No headers"))
        request.query_params = {}
        request.client = None

        # Should not raise, but return partial context
        context = capture_request_context(request)

        assert context["method"] == "GET"
        assert context["path"] == "/api/test"
        # Headers extraction failed, so it won't be in context

    def test_validates_all_sensitive_headers_defined(self) -> None:
        """Test that SENSITIVE_HEADERS contains expected values."""
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
        assert expected_headers == SENSITIVE_HEADERS

    def test_complex_query_params_sanitization(self, mocker: MockerFixture) -> None:
        """Test sanitization of nested query parameters."""
        request = mocker.Mock()
        request.method = "POST"
        request.url.path = "/api/complex"
        request.url.scheme = "http"
        request.url.hostname = "localhost"
        request.url.port = 8000
        request.headers = {}
        request.query_params = {
            "filter[name]": "John",
            "filter[password]": "secret123",
            "sort": "created_at",
            "auth_token": "bearer_123",
        }
        request.client = None

        context = capture_request_context(request)

        assert context["query_params"]["filter[name]"] == "John"
        assert context["query_params"]["filter[password]"] == REDACTED
        assert context["query_params"]["sort"] == "created_at"
        assert context["query_params"]["auth_token"] == REDACTED
