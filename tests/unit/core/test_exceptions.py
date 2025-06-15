"""Tests for core exception classes."""

import pytest

from src.core.exceptions import (
    BusinessRuleError,
    ErrorCode,
    NotFoundError,
    Severity,
    TributumError,
    UnauthorizedError,
    ValidationError,
)


class TestErrorCode:
    """Test cases for the ErrorCode enum."""

    def test_all_error_codes_have_unique_values(self) -> None:
        """Test that all error codes have unique values."""
        error_values = [code.value for code in ErrorCode]
        unique_values = set(error_values)

        assert len(error_values) == len(unique_values), (
            "Error codes must have unique values"
        )

    def test_error_codes_follow_consistent_naming_pattern(self) -> None:
        """Test that error codes follow UPPER_SNAKE_CASE naming pattern."""
        for code in ErrorCode:
            assert code.value.isupper(), f"{code.value} should be uppercase"
            assert "_" in code.value or code.value.isalpha(), (
                f"{code.value} should use snake_case"
            )
            assert code.value == code.value.replace(" ", ""), (
                f"{code.value} should not contain spaces"
            )

    def test_error_code_can_be_used_with_tributum_error(self) -> None:
        """Test that ErrorCode enum can be used with TributumError."""
        error_code = ErrorCode.VALIDATION_ERROR
        message = "Test validation error"

        exception = TributumError(error_code, message)

        assert exception.error_code == error_code.value
        assert exception.message == message

    def test_error_code_string_conversion(self) -> None:
        """Test that ErrorCode enum values are strings."""
        for code in ErrorCode:
            # Verify that the value is a string
            assert isinstance(code.value, str)
            # Verify that we can get the string value
            assert code.value == code.value

    def test_error_code_enum_has_expected_members(self) -> None:
        """Test that ErrorCode enum has all expected members."""
        expected_codes = {
            "INTERNAL_ERROR",
            "VALIDATION_ERROR",
            "NOT_FOUND",
            "UNAUTHORIZED",
        }

        actual_codes = {code.value for code in ErrorCode}

        assert actual_codes == expected_codes, (
            f"Expected codes {expected_codes}, got {actual_codes}"
        )


class TestSeverity:
    """Test cases for the Severity enum."""

    def test_all_severities_have_unique_values(self) -> None:
        """Test that all severity levels have unique values."""
        severity_values = [severity.value for severity in Severity]
        unique_values = set(severity_values)

        assert len(severity_values) == len(unique_values), (
            "Severity levels must have unique values"
        )

    def test_severities_follow_consistent_naming_pattern(self) -> None:
        """Test that severity levels follow UPPER_CASE naming pattern."""
        for severity in Severity:
            assert severity.value.isupper(), f"{severity.value} should be uppercase"
            assert severity.value.isalpha(), (
                f"{severity.value} should contain only letters"
            )

    def test_severity_enum_has_expected_members(self) -> None:
        """Test that Severity enum has all expected members."""
        expected_severities = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
        actual_severities = {severity.value for severity in Severity}

        assert actual_severities == expected_severities, (
            f"Expected severities {expected_severities}, got {actual_severities}"
        )

    def test_severity_ordering_makes_sense(self) -> None:
        """Test that severity levels have logical ordering."""
        # This test documents the expected severity hierarchy
        severity_order = [
            Severity.LOW,
            Severity.MEDIUM,
            Severity.HIGH,
            Severity.CRITICAL,
        ]

        # Verify all severities are included
        assert len(severity_order) == len(Severity)
        assert set(severity_order) == set(Severity)


class TestTributumError:
    """Test cases for the base TributumError class."""

    def test_exception_creation_with_code_and_message(self) -> None:
        """Test that exception can be created with error code and message."""
        error_code = "TEST_ERROR"
        message = "This is a test error"

        exception = TributumError(error_code, message)

        assert exception.error_code == error_code
        assert exception.message == message
        assert exception.severity == Severity.MEDIUM  # Default severity
        assert exception.context == {}  # Default empty context

    def test_exception_can_be_raised_and_caught(self) -> None:
        """Test that exception can be raised and caught properly."""
        error_code = "RAISE_TEST"
        message = "Testing raise functionality"

        with pytest.raises(TributumError) as exc_info:
            raise TributumError(error_code, message)

        assert exc_info.value.error_code == error_code
        assert exc_info.value.message == message

    def test_string_representation_includes_code_and_message(self) -> None:
        """Test that string representation includes both error code and message."""
        error_code = "STR_TEST"
        message = "Testing string representation"
        exception = TributumError(error_code, message)

        str_repr = str(exception)

        assert error_code in str_repr
        assert message in str_repr
        assert str_repr == f"[{error_code}] {message}"

    def test_repr_shows_class_name_and_attributes(self) -> None:
        """Test that repr shows class name, error code, and message."""
        error_code = "REPR_TEST"
        message = "Testing repr representation"
        exception = TributumError(error_code, message)

        repr_str = repr(exception)

        assert "TributumError" in repr_str
        assert f"error_code='{error_code}'" in repr_str
        assert f"message='{message}'" in repr_str
        assert "severity=MEDIUM" in repr_str  # Default severity

    def test_inherits_from_exception(self) -> None:
        """Test that TributumError inherits from built-in Exception."""
        exception = TributumError("TEST", "test")

        assert isinstance(exception, Exception)
        assert isinstance(exception, TributumError)

    def test_exception_with_empty_strings(self) -> None:
        """Test that exception handles empty strings correctly."""
        exception = TributumError("", "")

        assert exception.error_code == ""
        assert exception.message == ""
        assert str(exception) == "[] "

    def test_exception_with_special_characters(self) -> None:
        """Test that exception handles special characters in code and message."""
        error_code = "ERROR_WITH_UNDERSCORE_123"
        message = "Error with special chars: !@#$%^&*()"
        exception = TributumError(error_code, message)

        assert exception.error_code == error_code
        assert exception.message == message
        assert str(exception) == f"[{error_code}] {message}"

    def test_exception_creation_with_error_code_enum(self) -> None:
        """Test that exception can be created with ErrorCode enum."""
        error_code = ErrorCode.NOT_FOUND
        message = "Resource not found"

        exception = TributumError(error_code, message)

        assert exception.error_code == error_code.value
        assert exception.message == message
        assert str(exception) == f"[{error_code.value}] {message}"

    def test_exception_creation_with_severity(self) -> None:
        """Test that exception can be created with custom severity."""
        error_code = "SEVERITY_TEST"
        message = "Testing severity"
        severity = Severity.CRITICAL

        exception = TributumError(error_code, message, severity=severity)

        assert exception.severity == severity

    def test_exception_creation_with_context(self) -> None:
        """Test that exception can be created with context information."""
        error_code = "CONTEXT_TEST"
        message = "Testing context"
        context = {"user_id": 123, "operation": "update", "resource": "profile"}

        exception = TributumError(error_code, message, context=context)

        assert exception.context == context

    def test_exception_with_full_parameters(self) -> None:
        """Test exception creation with all parameters."""
        error_code = ErrorCode.VALIDATION_ERROR
        message = "Full parameter test"
        severity = Severity.HIGH
        context = {"field": "email", "value": "invalid@"}

        exception = TributumError(error_code, message, severity, context)

        assert exception.error_code == error_code.value
        assert exception.message == message
        assert exception.severity == severity
        assert exception.context == context

    def test_repr_with_context(self) -> None:
        """Test repr includes context when present."""
        context = {"key": "value"}
        exception = TributumError("TEST", "message", context=context)

        repr_str = repr(exception)

        assert "context={'key': 'value'}" in repr_str

    def test_repr_without_context(self) -> None:
        """Test repr doesn't include context when empty."""
        exception = TributumError("TEST", "message")

        repr_str = repr(exception)

        assert "context" not in repr_str


class TestSpecializedExceptions:
    """Test cases for specialized exception classes."""

    def test_validation_error_default_error_code(self) -> None:
        """Test that ValidationError has correct default error code."""
        message = "Invalid email format"
        exception = ValidationError(message)

        assert exception.error_code == ErrorCode.VALIDATION_ERROR.value
        assert exception.message == message
        assert isinstance(exception, TributumError)

    def test_validation_error_custom_error_code(self) -> None:
        """Test that ValidationError accepts custom error code."""
        message = "Custom validation error"
        custom_code = "CUSTOM_VALIDATION"
        exception = ValidationError(message, custom_code)

        assert exception.error_code == custom_code
        assert exception.message == message

    def test_not_found_error_default_error_code(self) -> None:
        """Test that NotFoundError has correct default error code."""
        message = "User not found"
        exception = NotFoundError(message)

        assert exception.error_code == ErrorCode.NOT_FOUND.value
        assert exception.message == message
        assert isinstance(exception, TributumError)

    def test_not_found_error_custom_error_code(self) -> None:
        """Test that NotFoundError accepts custom error code."""
        message = "Custom resource not found"
        custom_code = "CUSTOM_NOT_FOUND"
        exception = NotFoundError(message, custom_code)

        assert exception.error_code == custom_code
        assert exception.message == message

    def test_unauthorized_error_default_error_code(self) -> None:
        """Test that UnauthorizedError has correct default error code."""
        message = "Invalid credentials"
        exception = UnauthorizedError(message)

        assert exception.error_code == ErrorCode.UNAUTHORIZED.value
        assert exception.message == message
        assert isinstance(exception, TributumError)

    def test_unauthorized_error_custom_error_code(self) -> None:
        """Test that UnauthorizedError accepts custom error code."""
        message = "Custom auth error"
        custom_code = "CUSTOM_AUTH"
        exception = UnauthorizedError(message, custom_code)

        assert exception.error_code == custom_code
        assert exception.message == message

    def test_business_rule_error_default_error_code(self) -> None:
        """Test that BusinessRuleError has correct default error code."""
        message = "Cannot process order with zero items"
        exception = BusinessRuleError(message)

        assert exception.error_code == ErrorCode.INTERNAL_ERROR.value
        assert exception.message == message
        assert isinstance(exception, TributumError)

    def test_business_rule_error_custom_error_code(self) -> None:
        """Test that BusinessRuleError accepts custom error code."""
        message = "Custom business rule violation"
        custom_code = "BUSINESS_RULE_VIOLATION"
        exception = BusinessRuleError(message, custom_code)

        assert exception.error_code == custom_code
        assert exception.message == message

    def test_all_exceptions_inherit_from_tributum_error(self) -> None:
        """Test that all specialized exceptions inherit from TributumError."""
        exceptions = [
            ValidationError("test"),
            NotFoundError("test"),
            UnauthorizedError("test"),
            BusinessRuleError("test"),
        ]

        for exception in exceptions:
            assert isinstance(exception, TributumError)
            assert isinstance(exception, Exception)

    def test_specialized_exceptions_can_be_raised_and_caught(self) -> None:
        """Test that specialized exceptions can be raised and caught."""
        test_cases = [
            (ValidationError, "Validation failed"),
            (NotFoundError, "Resource not found"),
            (UnauthorizedError, "Access denied"),
            (BusinessRuleError, "Business rule violated"),
        ]

        for exception_class, message in test_cases:
            with pytest.raises(exception_class) as exc_info:
                raise exception_class(message)

            assert exc_info.value.message == message

    def test_specialized_exceptions_string_representation(self) -> None:
        """Test string representation of specialized exceptions."""
        test_cases = [
            (
                ValidationError("Invalid"),
                (
                    "ValidationError(error_code='VALIDATION_ERROR', "
                    "message='Invalid', severity=LOW)"
                ),
            ),
            (
                NotFoundError("Missing"),
                (
                    "NotFoundError(error_code='NOT_FOUND', "
                    "message='Missing', severity=LOW)"
                ),
            ),
            (
                UnauthorizedError("Denied"),
                (
                    "UnauthorizedError(error_code='UNAUTHORIZED', "
                    "message='Denied', severity=HIGH)"
                ),
            ),
            (
                BusinessRuleError("Rule"),
                (
                    "BusinessRuleError(error_code='INTERNAL_ERROR', "
                    "message='Rule', severity=MEDIUM)"
                ),
            ),
        ]

        for exception, expected_repr in test_cases:
            assert repr(exception) == expected_repr

    def test_specialized_exceptions_with_context(self) -> None:
        """Test that specialized exceptions can accept context."""
        context = {"field": "email", "value": "test@"}

        validation_error = ValidationError("Invalid email", context=context)
        assert validation_error.context == context
        assert validation_error.severity == Severity.LOW

        not_found_error = NotFoundError("User not found", context={"user_id": 123})
        assert not_found_error.context == {"user_id": 123}
        assert not_found_error.severity == Severity.LOW

        unauthorized_error = UnauthorizedError(
            "Access denied", context={"role": "guest"}
        )
        assert unauthorized_error.context == {"role": "guest"}
        assert unauthorized_error.severity == Severity.HIGH

        business_error = BusinessRuleError(
            "Insufficient funds", context={"balance": 100}
        )
        assert business_error.context == {"balance": 100}
        assert business_error.severity == Severity.MEDIUM

    def test_specialized_exceptions_default_severities(self) -> None:
        """Test that specialized exceptions have appropriate default severities."""
        assert ValidationError("test").severity == Severity.LOW
        assert NotFoundError("test").severity == Severity.LOW
        assert UnauthorizedError("test").severity == Severity.HIGH
        assert BusinessRuleError("test").severity == Severity.MEDIUM
