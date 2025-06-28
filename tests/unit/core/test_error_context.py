"""Tests for error context utilities."""

import time
from typing import cast

import pytest
from pytest_mock import MockerFixture

from src.api.constants import SENSITIVE_HEADERS
from src.core.constants import REDACTED
from src.core.error_context import (
    _luhn_check,
    _sanitize_dict,
    _sanitize_list,
    capture_request_context,
    detect_sensitive_value,
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
        """Test sanitization of a flat dictionary with enhanced detection."""
        context = {
            "username": "john_doe",
            "password": "secret123",
            "email": "john@example.com",  # Now detected as sensitive value
            "api_key": "sk_test_123",
            "safe_field": "normal data",
        }

        sanitized = sanitize_context(context)

        assert sanitized["username"] == "john_doe"
        assert sanitized["password"] == REDACTED  # Field name detection
        assert sanitized["email"] == REDACTED  # Value detection (email pattern)
        assert sanitized["api_key"] == REDACTED  # Field name detection
        assert sanitized["safe_field"] == "normal data"

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

        # Non-sensitive keys preserve their structure, but values are checked
        assert sanitized["user_data"]["name"] == "John"
        assert sanitized["user_data"]["email"] == REDACTED  # Email detected in value

        # Sensitive keys have their entire value redacted
        assert sanitized["credentials"] == REDACTED
        assert sanitized["api_key"] == REDACTED
        assert sanitized["session"] == REDACTED

    def test_legacy_behavior_with_value_detection_disabled(
        self, mocker: MockerFixture
    ) -> None:
        """Test that old behavior works when value detection is disabled."""
        # Mock the configuration with value detection disabled
        mock_log_config = mocker.Mock()
        mock_log_config.excluded_fields_from_sanitization = []
        mock_log_config.sensitive_value_detection = False

        mock_get_settings = mocker.patch("src.core.error_context._get_log_config")
        mock_get_settings.return_value = mock_log_config

        context = {
            "username": "john_doe",
            "password": "secret123",
            "email": "john@example.com",  # Should NOT be redacted (legacy behavior)
            "api_key": "sk_test_123",
        }

        sanitized = sanitize_context(context)

        assert sanitized["username"] == "john_doe"
        assert sanitized["password"] == REDACTED  # Field name detection still works
        assert sanitized["email"] == "john@example.com"  # Value detection disabled
        assert sanitized["api_key"] == REDACTED  # Field name detection still works

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


@pytest.mark.unit
class TestLuhnAlgorithm:
    """Test cases for Luhn algorithm credit card validation."""

    def test_valid_credit_card_numbers(self) -> None:
        """Test Luhn validation with known valid credit card numbers."""
        valid_cards = [
            "4532015112830366",  # Visa
            "5425233430109903",  # Mastercard
            "374245455400126",  # American Express
            "6011000991300009",  # Discover
            "30569309025904",  # Diners Club
        ]

        for card in valid_cards:
            assert _luhn_check(card), f"{card} should pass Luhn validation"

    def test_invalid_credit_card_numbers(self) -> None:
        """Test Luhn validation with invalid credit card numbers."""
        invalid_cards = [
            "4532015112830365",  # Last digit changed
            "5425233430109902",  # Last digit changed
            "374245455400125",  # Last digit changed
            "1234567890123456",  # Random number
            "0000000000000000",  # All zeros
        ]

        for card in invalid_cards:
            assert not _luhn_check(card), f"{card} should fail Luhn validation"

    def test_credit_card_with_spaces_and_dashes(self) -> None:
        """Test Luhn validation with formatted credit card numbers."""
        valid_formatted_cards = [
            "4532 0151 1283 0366",  # Spaces
            "4532-0151-1283-0366",  # Dashes
            "4532 0151-1283 0366",  # Mixed
            " 4532015112830366 ",  # Whitespace
        ]

        for card in valid_formatted_cards:
            assert _luhn_check(card), f"{card} should pass Luhn validation"

    def test_too_short_numbers(self) -> None:
        """Test that numbers with less than 13 digits are rejected."""
        short_numbers = [
            "123456789012",  # 12 digits
            "12345",  # 5 digits
            "",  # Empty
            "abc",  # Non-digits
        ]

        for number in short_numbers:
            assert not _luhn_check(number), f"{number} should be rejected (too short)"

    def test_non_numeric_input(self) -> None:
        """Test handling of non-numeric input."""
        non_numeric = [
            "abcdefghijklmnop",  # All letters
            "45a2-01b1-12c3-0366",  # Mixed alphanumeric
            "45320151128303661234567890",  # Too long but valid start
        ]

        for input_str in non_numeric:
            # Should not raise exception, just return False
            result = _luhn_check(input_str)
            assert isinstance(result, bool)


@pytest.mark.unit
class TestSensitiveValueDetection:
    """Test cases for sensitive value detection patterns."""

    def test_credit_card_detection(self) -> None:
        """Test detection of credit card numbers in values."""
        credit_card_values = [
            "My card is 4532015112830366",
            "Card: 4532-0151-1283-0366",
            "4532 0151 1283 0366",
            "Payment info: 5425233430109903 expires 12/25",
        ]

        for value in credit_card_values:
            assert detect_sensitive_value(value), (
                f"Should detect credit card in: {value[:50]}..."
            )

    def test_invalid_credit_card_not_detected(self) -> None:
        """Test that invalid credit card numbers are not detected."""
        invalid_credit_cards = [
            "1234567890123456",  # Fails Luhn
            "4532015112830365",  # Fails Luhn
            "123 456 789 012",  # Too short
        ]

        for value in invalid_credit_cards:
            assert not detect_sensitive_value(value), (
                f"Should not detect invalid card: {value[:50]}..."
            )

    def test_email_detection(self) -> None:
        """Test detection of email addresses."""
        email_values = [
            "Contact us at support@example.com",
            "user@domain.org",
            "test.email+tag@example.co.uk",
            "My email is john.doe@company.com for work",
        ]

        for value in email_values:
            assert detect_sensitive_value(value), f"Should detect email in: {value}"

    def test_phone_number_detection(self) -> None:
        """Test detection of phone numbers."""
        phone_values = [
            "Call me at (555) 123-4567",
            "555-123-4567",
            "555.123.4567",
            "1-555-123-4567",
            "+1 555 123 4567",
            "Phone: 5551234567",
        ]

        for value in phone_values:
            assert detect_sensitive_value(value), f"Should detect phone in: {value}"

    def test_uuid_detection(self) -> None:
        """Test detection of UUID values."""
        uuid_values = [
            "Session ID: 550e8400-e29b-41d4-a716-446655440000",
            "550e8400-e29b-41d4-a716-446655440000",
            "User UUID is 6ba7b810-9dad-11d1-80b4-00c04fd430c8",
        ]

        for value in uuid_values:
            assert detect_sensitive_value(value), f"Should detect UUID in: {value}"

    def test_jwt_detection(self) -> None:
        """Test detection of JWT tokens."""
        jwt_values = [
            (
                "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
                "eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ."
                "SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
            ),
            (
                "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
                "eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ."
                "SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
            ),
            "Token: abc.def.ghi",  # Simple JWT format
        ]

        for value in jwt_values:
            assert detect_sensitive_value(value), f"Should detect JWT in: {value}"

    def test_non_sensitive_values(self) -> None:
        """Test that normal values are not detected as sensitive."""
        normal_values = [
            "Hello world",
            "The quick brown fox",
            "This is a normal sentence with numbers 123 456",
            "website.com",  # Domain without @ symbol
            "123-45-6789",  # Could be SSN but not in our patterns
            "Meeting at 3pm on Monday",
            "Order #12345 is ready",
        ]

        for value in normal_values:
            assert not detect_sensitive_value(value), (
                f"Should not detect as sensitive: {value[:50]}..."
            )

    def test_empty_and_invalid_input(self) -> None:
        """Test handling of empty and invalid input."""
        invalid_inputs = [
            "",
            "   ",  # Whitespace only
            None,  # This will fail isinstance check
            123,  # Non-string
        ]

        for input_val in invalid_inputs:
            result = detect_sensitive_value(input_val)  # type: ignore[arg-type]
            assert not result, f"Should return False for invalid input: {input_val}"


@pytest.mark.unit
class TestEnhancedSanitization:
    """Test cases for enhanced sanitization with value detection."""

    def test_value_based_sanitization_enabled(self, mocker: MockerFixture) -> None:
        """Test that value-based detection works when enabled."""
        # Mock the configuration
        mock_log_config = mocker.Mock()
        mock_log_config.excluded_fields_from_sanitization = []
        mock_log_config.sensitive_value_detection = True

        mock_get_settings = mocker.patch("src.core.error_context._get_log_config")
        mock_get_settings.return_value = mock_log_config

        context = {
            "username": "john_doe",
            "message": "My card is 4532015112830366",
            "email_field": "contact@example.com",
            "safe_data": "This is safe",
        }

        sanitized = sanitize_context(context)

        assert sanitized["username"] == "john_doe"
        assert sanitized["message"] == REDACTED  # Credit card detected
        assert sanitized["email_field"] == REDACTED  # Email detected
        assert sanitized["safe_data"] == "This is safe"

    def test_value_based_sanitization_disabled(self, mocker: MockerFixture) -> None:
        """Test that value-based detection is skipped when disabled."""
        # Mock the configuration with value detection disabled
        mock_log_config = mocker.Mock()
        mock_log_config.excluded_fields_from_sanitization = []
        mock_log_config.sensitive_value_detection = False

        mock_get_settings = mocker.patch("src.core.error_context._get_log_config")
        mock_get_settings.return_value = mock_log_config

        context = {
            "username": "john_doe",
            "message": "My card is 4532015112830366",
            "email_field": "contact@example.com",
        }

        sanitized = sanitize_context(context)

        assert sanitized["username"] == "john_doe"
        assert sanitized["message"] == "My card is 4532015112830366"  # Not redacted
        assert sanitized["email_field"] == "contact@example.com"  # Not redacted

    def test_excluded_fields_not_sanitized(self, mocker: MockerFixture) -> None:
        """Test that excluded fields are not sanitized."""
        # Mock the configuration with excluded fields
        mock_log_config = mocker.Mock()
        mock_log_config.excluded_fields_from_sanitization = [
            "safe_password",
            "safe_token",
        ]
        mock_log_config.sensitive_value_detection = True

        mock_get_settings = mocker.patch("src.core.error_context._get_log_config")
        mock_get_settings.return_value = mock_log_config

        context = {
            "password": "secret123",  # Should be redacted (field name)
            "safe_password": "should_not_be_redacted",  # Excluded field
            "token": "abc123",  # Should be redacted (field name)
            "safe_token": "4532015112830366",  # Excluded even with sensitive value
            "message": "My email is test@example.com",  # Should be redacted (value)
        }

        sanitized = sanitize_context(context)

        assert sanitized["password"] == REDACTED
        assert sanitized["safe_password"] == "should_not_be_redacted"
        assert sanitized["token"] == REDACTED
        # Not redacted despite credit card
        assert sanitized["safe_token"] == "4532015112830366"
        assert sanitized["message"] == REDACTED

    def test_field_name_detection_takes_precedence(self, mocker: MockerFixture) -> None:
        """Test that field name detection takes precedence over value detection."""
        # Mock the configuration
        mock_log_config = mocker.Mock()
        mock_log_config.excluded_fields_from_sanitization = []
        mock_log_config.sensitive_value_detection = True

        mock_get_settings = mocker.patch("src.core.error_context._get_log_config")
        mock_get_settings.return_value = mock_log_config

        context = {
            "password": "just a normal value",  # Should be redacted due to field name
            # Should be redacted due to value
            "normal_field": "My card is 4532015112830366",
        }

        sanitized = sanitize_context(context)

        assert sanitized["password"] == REDACTED  # Field name detection
        assert sanitized["normal_field"] == REDACTED  # Value detection

    def test_nested_value_detection(self, mocker: MockerFixture) -> None:
        """Test value detection in nested structures."""
        # Mock the configuration
        mock_log_config = mocker.Mock()
        mock_log_config.excluded_fields_from_sanitization = []
        mock_log_config.sensitive_value_detection = True

        mock_get_settings = mocker.patch("src.core.error_context._get_log_config")
        mock_get_settings.return_value = mock_log_config

        context = {
            "user": {
                "name": "John",
                "contact": "john@example.com",  # Email in value
                "notes": "Credit card: 4532015112830366",  # Credit card in value
            },
            "items": [
                {"description": "Item 1", "contact": "supplier@company.com"},
                {"description": "Item 2", "safe_field": "normal data"},
            ],
        }

        sanitized = sanitize_context(context)

        assert sanitized["user"]["name"] == "John"
        assert sanitized["user"]["contact"] == REDACTED
        assert sanitized["user"]["notes"] == REDACTED
        assert sanitized["items"][0]["description"] == "Item 1"
        assert sanitized["items"][0]["contact"] == REDACTED
        assert sanitized["items"][1]["description"] == "Item 2"
        assert sanitized["items"][1]["safe_field"] == "normal data"

    def test_sanitize_dict_with_none_log_config(self, mocker: MockerFixture) -> None:
        """Test _sanitize_dict when log_config is None."""
        # Mock _get_log_config to ensure it's called
        mock_log_config = mocker.Mock()
        mock_log_config.excluded_fields_from_sanitization = []
        mock_log_config.sensitive_value_detection = True
        mock_get_log_config = mocker.patch("src.core.error_context._get_log_config")
        mock_get_log_config.return_value = mock_log_config

        # Create test data
        data = {
            "username": "john",
            "password": "secret",
            "email": "john@example.com",
        }

        # Call with None log_config to test line 147
        _sanitize_dict(data, log_config=None)

        # Verify _get_log_config was called
        mock_get_log_config.assert_called_once()
        # Verify sanitization happened
        assert data["password"] == REDACTED
        assert data["email"] == REDACTED

    def test_sanitize_list_with_none_log_config(self, mocker: MockerFixture) -> None:
        """Test _sanitize_list when log_config is None."""
        # Mock _get_log_config to ensure it's called
        mock_log_config = mocker.Mock()
        mock_log_config.excluded_fields_from_sanitization = []
        mock_log_config.sensitive_value_detection = True
        mock_get_log_config = mocker.patch("src.core.error_context._get_log_config")
        mock_get_log_config.return_value = mock_log_config

        # Create test data
        data = [
            {"password": "secret"},
            {"email": "test@example.com"},
        ]

        # Call with None log_config to test line 180
        _sanitize_list(data, log_config=None)

        # Verify _get_log_config was called
        mock_get_log_config.assert_called_once()
        # Verify sanitization happened
        assert data[0]["password"] == REDACTED
        assert data[1]["email"] == REDACTED

    def test_luhn_check_all_same_digit(self) -> None:
        """Test Luhn check with all same digit."""
        # Test line 77 - all same digit check
        assert not _luhn_check("1111111111111111")
        assert not _luhn_check("2222222222222222")
        assert not _luhn_check("9999999999999999")

    def test_performance_impact_under_threshold(self, mocker: MockerFixture) -> None:
        """Test that enhanced sanitization performance impact is under 3ms threshold."""
        # Mock the configuration with value detection enabled
        mock_log_config = mocker.Mock()
        mock_log_config.excluded_fields_from_sanitization = []
        mock_log_config.sensitive_value_detection = True
        mock_get_settings = mocker.patch("src.core.error_context._get_log_config")
        mock_get_settings.return_value = mock_log_config

        # Create a realistic test payload
        large_context = {
            "user_info": {
                "id": 12345,
                "username": "john_doe",
                "email": "john@example.com",  # Will be detected
                "profile": {
                    "name": "John Doe",
                    "phone": "+1 555-123-4567",  # Will be detected
                    "address": "123 Main St, City, State",
                    "preferences": {"theme": "dark", "notifications": True},
                },
            },
            "transaction_data": {
                "id": "txn_123456",
                "amount": 100.50,
                "currency": "USD",
                "card_info": "Card ending in 4532015112830366",  # Will be detected
                "metadata": {
                    "source": "web",
                    "user_agent": "Mozilla/5.0 Firefox/91.0",
                    # UUID will be detected
                    "session_id": "550e8400-e29b-41d4-a716-446655440000",
                },
            },
            "logs": [
                {
                    "timestamp": "2024-01-01T12:00:00Z",
                    "level": "INFO",
                    "message": "User logged in",
                },
                {
                    "timestamp": "2024-01-01T12:01:00Z",
                    "level": "DEBUG",
                    "message": "Processing request",
                },
                {
                    "timestamp": "2024-01-01T12:02:00Z",
                    "level": "INFO",
                    "message": "Transaction completed",
                },
            ],
            "api_response": {
                "status": "success",
                "data": {"result": "processed", "reference": "ref_789"},
                # JWT will be detected
                "jwt_token": (
                    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
                    "eyJzdWIiOiIxMjM0NTY3ODkwIn0."
                    "SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
                ),
            },
        }

        # Warm up the function (compile patterns, etc.)
        for _ in range(3):
            sanitize_context(large_context)

        # Measure performance over multiple runs
        total_time = 0.0
        runs = 10

        for _ in range(runs):
            start_time = time.perf_counter()
            result = sanitize_context(large_context)
            end_time = time.perf_counter()

            duration_ms = (end_time - start_time) * 1000
            total_time += duration_ms

            # Verify sanitization worked
            assert result["user_info"]["email"] == "[REDACTED]"
            assert result["user_info"]["profile"]["phone"] == "[REDACTED]"
            assert result["transaction_data"]["card_info"] == "[REDACTED]"
            assert result["transaction_data"]["metadata"]["session_id"] == "[REDACTED]"
            assert result["api_response"]["jwt_token"] == "[REDACTED]"

        average_time_ms = total_time / runs

        # Verify performance requirement: < 3ms for typical payloads
        assert average_time_ms < 3.0, (
            f"Average sanitization time {average_time_ms:.2f}ms exceeds 3ms threshold"
        )
