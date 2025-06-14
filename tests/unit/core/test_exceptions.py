"""Tests for core exception classes."""

import pytest

from src.core.exceptions import ErrorCode, TributumError


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


class TestTributumError:
    """Test cases for the base TributumError class."""

    def test_exception_creation_with_code_and_message(self) -> None:
        """Test that exception can be created with error code and message."""
        error_code = "TEST_ERROR"
        message = "This is a test error"

        exception = TributumError(error_code, message)

        assert exception.error_code == error_code
        assert exception.message == message

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
