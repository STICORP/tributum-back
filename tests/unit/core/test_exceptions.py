"""Tests for core exception classes."""

import pytest

from src.core.exceptions import TributumError


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
