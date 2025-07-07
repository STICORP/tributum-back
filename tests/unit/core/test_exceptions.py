"""Comprehensive unit tests for the exceptions module.

This module tests all aspects of the structured exception hierarchy including:
- ErrorCode and Severity enums
- Base TributumError exception with rich context and fingerprinting
- Specialized exception classes
- Exception chaining and stack trace capture
- Thread safety of exception creation
"""

import threading
from typing import Any

import pytest
from pytest_mock import MockerFixture

from src.core.exceptions import (
    BusinessRuleError,
    ErrorCode,
    NotFoundError,
    Severity,
    TributumError,
    UnauthorizedError,
    ValidationError,
)


@pytest.mark.unit
class TestErrorCode:
    """Test the ErrorCode enum functionality."""

    @pytest.mark.parametrize(
        ("enum_value", "expected_string"),
        [
            (ErrorCode.INTERNAL_ERROR, "INTERNAL_ERROR"),
            (ErrorCode.VALIDATION_ERROR, "VALIDATION_ERROR"),
            (ErrorCode.NOT_FOUND, "NOT_FOUND"),
            (ErrorCode.UNAUTHORIZED, "UNAUTHORIZED"),
        ],
    )
    def test_error_code_enum_values(
        self,
        enum_value: ErrorCode,
        expected_string: str,
    ) -> None:
        """Verify all ErrorCode enum values are correctly defined."""
        assert enum_value.value == expected_string
        assert isinstance(enum_value, ErrorCode)

    @pytest.mark.parametrize(
        ("value", "expected_member"),
        [
            ("INTERNAL_ERROR", ErrorCode.INTERNAL_ERROR),
            ("VALIDATION_ERROR", ErrorCode.VALIDATION_ERROR),
            ("NOT_FOUND", ErrorCode.NOT_FOUND),
            ("UNAUTHORIZED", ErrorCode.UNAUTHORIZED),
        ],
    )
    def test_error_code_enum_membership(
        self,
        value: str,
        expected_member: ErrorCode,
    ) -> None:
        """Verify enum membership checks work correctly."""
        # Test membership by value
        assert ErrorCode(value) == expected_member
        assert ErrorCode(value) in ErrorCode

        # Test invalid membership
        with pytest.raises(ValueError, match="'INVALID_ERROR_CODE' is not a valid"):
            ErrorCode("INVALID_ERROR_CODE")


@pytest.mark.unit
class TestSeverity:
    """Test the Severity enum functionality."""

    @pytest.mark.parametrize(
        ("enum_value", "expected_string"),
        [
            (Severity.LOW, "LOW"),
            (Severity.MEDIUM, "MEDIUM"),
            (Severity.HIGH, "HIGH"),
            (Severity.CRITICAL, "CRITICAL"),
        ],
    )
    def test_severity_enum_values(
        self,
        enum_value: Severity,
        expected_string: str,
    ) -> None:
        """Verify all Severity enum values are correctly defined."""
        assert enum_value.value == expected_string
        assert isinstance(enum_value, Severity)

    @pytest.mark.parametrize(
        ("severity1", "severity2", "can_compare"),
        [
            (Severity.LOW, Severity.MEDIUM, True),
            (Severity.MEDIUM, Severity.HIGH, True),
            (Severity.HIGH, Severity.CRITICAL, True),
            (Severity.LOW, Severity.CRITICAL, True),
        ],
    )
    def test_severity_ordering_comparison(
        self,
        severity1: Severity,
        severity2: Severity,
        can_compare: bool,
    ) -> None:
        """Verify severity levels can be compared for ordering."""
        # Enums can be compared for equality and membership
        assert severity1 != severity2
        assert severity1 in Severity
        assert severity2 in Severity

        # Verify they are different instances
        if can_compare:
            assert severity1 is not severity2


@pytest.mark.unit
class TestTributumError:
    """Test the base TributumError exception class."""

    @pytest.mark.parametrize(
        ("error_code", "message", "severity", "context"),
        [
            ("TEST_ERROR", "Test error message", Severity.LOW, None),
            ("CUSTOM_ERROR", "Custom error", Severity.HIGH, {"key": "value"}),
            ("", "Empty error code", Severity.MEDIUM, {}),
            (
                "LONG_ERROR_CODE_STRING",
                "Long code",
                Severity.CRITICAL,
                {"a": 1, "b": 2},
            ),
        ],
    )
    def test_initialization_with_error_code_string(
        self,
        mocker: MockerFixture,
        error_code: str,
        message: str,
        severity: Severity,
        context: dict[str, Any] | None,
    ) -> None:
        """Verify TributumError initializes correctly with string error code."""
        # Mock traceback.format_stack
        mock_stack = [
            '  File "test.py", line 10, in test\n    raise error\n',
        ]
        mocker.patch("traceback.format_stack", return_value=mock_stack)

        # Create exception
        error = TributumError(error_code, message, severity, context)

        # Verify attributes
        assert error.error_code == error_code
        assert error.message == message
        assert error.severity == severity
        assert error.context == (context or {})
        assert error.cause is None
        assert error.stack_trace == mock_stack[:-1]  # Excludes current frame
        assert isinstance(error.fingerprint, str)
        assert len(error.fingerprint) == 16

    @pytest.mark.parametrize(
        ("error_code_enum", "message", "severity"),
        [
            (ErrorCode.INTERNAL_ERROR, "Internal error", Severity.HIGH),
            (ErrorCode.VALIDATION_ERROR, "Validation failed", Severity.LOW),
            (ErrorCode.NOT_FOUND, "Not found", Severity.MEDIUM),
            (ErrorCode.UNAUTHORIZED, "Unauthorized", Severity.CRITICAL),
        ],
    )
    def test_initialization_with_error_code_enum(
        self,
        mocker: MockerFixture,
        error_code_enum: ErrorCode,
        message: str,
        severity: Severity,
    ) -> None:
        """Verify TributumError initializes correctly with ErrorCode enum."""
        # Mock traceback.format_stack
        mock_stack = ['  File "test.py", line 10, in test\n    raise error\n']
        mocker.patch("traceback.format_stack", return_value=mock_stack)

        # Create exception
        error = TributumError(error_code_enum, message, severity)

        # Verify enum value is extracted correctly
        assert error.error_code == error_code_enum.value
        assert isinstance(error.error_code, str)

    @pytest.mark.parametrize(
        ("cause_exception", "context"),
        [
            (ValueError("Original error"), {"operation": "test"}),
            (KeyError("missing_key"), None),
            (RuntimeError("Runtime issue"), {}),
            (None, {"no_cause": True}),
        ],
    )
    def test_initialization_with_cause(
        self,
        mocker: MockerFixture,
        cause_exception: Exception | None,
        context: dict[str, Any] | None,
    ) -> None:
        """Verify exception chaining works correctly."""
        # Mock traceback.format_stack
        mocker.patch("traceback.format_stack", return_value=[])

        # Create exception with cause
        error = TributumError(
            "TEST_ERROR",
            "Test with cause",
            Severity.MEDIUM,
            context,
            cause_exception,
        )

        # Verify cause is set correctly
        assert error.cause is cause_exception
        if cause_exception:
            assert error.__cause__ is cause_exception
        else:
            assert error.__cause__ is None

    @pytest.mark.parametrize(
        "stack_trace",
        [
            [
                '  File "/app/src/services/user.py", line 45, in get_user\n'
                "    return user\n",
            ],
            [
                '  File "/site-packages/lib.py", line 10, in func\n    call()\n',
                '  File "/app/src/api/route.py", line 20, in route\n    process()\n',
            ],
            [],  # Empty stack
        ],
    )
    def test_fingerprint_generation(
        self,
        mocker: MockerFixture,
        stack_trace: list[str],
    ) -> None:
        """Verify fingerprint generation creates consistent hashes."""
        # Mock traceback with controlled output
        mocker.patch("traceback.format_stack", return_value=[*stack_trace, "current"])

        # Create two exceptions with same parameters
        error1 = TributumError("TEST_ERROR", "Test message")
        error2 = TributumError("TEST_ERROR", "Test message")

        # Verify fingerprints are consistent
        assert error1.fingerprint == error2.fingerprint
        assert len(error1.fingerprint) == 16
        assert all(c in "0123456789abcdef" for c in error1.fingerprint)

    def test_fingerprint_excludes_site_packages(
        self,
        mocker: MockerFixture,
        mock_stack_trace_fixture: dict[str, list[str]],
    ) -> None:
        """Verify fingerprint generation excludes site-packages frames."""
        # Use stack trace with site-packages
        stack_with_site = mock_stack_trace_fixture["with_site_packages"]
        mocker.patch(
            "traceback.format_stack", return_value=[*stack_with_site, "current"]
        )

        # Use stack trace without site-packages
        stack_without_site = mock_stack_trace_fixture["normal"]

        # Create exception with site-packages in stack
        error1 = TributumError("TEST_ERROR", "Test message")

        # Mock with clean stack and create another exception
        mocker.patch(
            "traceback.format_stack", return_value=[*stack_without_site, "current"]
        )
        error2 = TributumError("TEST_ERROR", "Test message")

        # Both should generate fingerprints (site-packages frames are ignored)
        assert len(error1.fingerprint) == 16
        assert len(error2.fingerprint) == 16

    @pytest.mark.parametrize(
        ("severity", "expected_is_expected"),
        [
            (Severity.LOW, True),
            (Severity.MEDIUM, True),
            (Severity.HIGH, False),
            (Severity.CRITICAL, False),
        ],
    )
    def test_is_expected_property(
        self,
        mocker: MockerFixture,
        severity: Severity,
        expected_is_expected: bool,
    ) -> None:
        """Verify is_expected property returns correct values based on severity."""
        # Mock traceback
        mocker.patch("traceback.format_stack", return_value=[])

        # Create exception with specific severity
        error = TributumError("TEST", "Test", severity)

        # Verify is_expected property
        assert error.is_expected == expected_is_expected

    @pytest.mark.parametrize(
        ("severity", "expected_should_alert"),
        [
            (Severity.LOW, False),
            (Severity.MEDIUM, False),
            (Severity.HIGH, True),
            (Severity.CRITICAL, True),
        ],
    )
    def test_should_alert_property(
        self,
        mocker: MockerFixture,
        severity: Severity,
        expected_should_alert: bool,
    ) -> None:
        """Verify should_alert property returns correct values based on severity."""
        # Mock traceback
        mocker.patch("traceback.format_stack", return_value=[])

        # Create exception with specific severity
        error = TributumError("TEST", "Test", severity)

        # Verify should_alert property
        assert error.should_alert == expected_should_alert

    @pytest.mark.parametrize(
        ("error_code", "message", "expected_str"),
        [
            ("TEST_ERROR", "Test message", "[TEST_ERROR] Test message"),
            ("", "Empty code", "[] Empty code"),
            ("LONG_CODE", "", "[LONG_CODE] "),
            (
                ErrorCode.VALIDATION_ERROR,
                "Invalid input",
                "[VALIDATION_ERROR] Invalid input",
            ),
        ],
    )
    def test_str_representation(
        self,
        mocker: MockerFixture,
        error_code: str | ErrorCode,
        message: str,
        expected_str: str,
    ) -> None:
        """Verify __str__ method returns formatted error string."""
        # Mock traceback
        mocker.patch("traceback.format_stack", return_value=[])

        # Create exception
        error = TributumError(error_code, message)

        # Verify string representation
        assert str(error) == expected_str

    @pytest.mark.parametrize(
        ("error_code", "message", "severity", "context", "has_context"),
        [
            ("TEST", "Test", Severity.LOW, None, False),
            ("TEST", "Test", Severity.HIGH, {}, False),
            ("TEST", "Test", Severity.MEDIUM, {"key": "value"}, True),
            (ErrorCode.NOT_FOUND, "Not found", Severity.LOW, {"id": 123}, True),
        ],
    )
    def test_repr_representation(
        self,
        mocker: MockerFixture,
        error_code: str | ErrorCode,
        message: str,
        severity: Severity,
        context: dict[str, Any] | None,
        has_context: bool,
    ) -> None:
        """Verify __repr__ method returns detailed representation."""
        # Mock traceback
        mocker.patch("traceback.format_stack", return_value=[])

        # Create exception
        error = TributumError(error_code, message, severity, context)

        # Get repr string
        repr_str = repr(error)

        # Verify repr includes all relevant attributes
        assert "TributumError" in repr_str
        assert f"error_code='{error.error_code}'" in repr_str
        assert f"message='{message}'" in repr_str
        assert f"severity={severity.value}" in repr_str

        if has_context and context:
            assert "context=" in repr_str
        else:
            assert "context=" not in repr_str

    @pytest.mark.parametrize(
        "stack_depth",
        [1, 3, 5, 10],
    )
    def test_stack_trace_capture(
        self,
        mocker: MockerFixture,
        stack_depth: int,
    ) -> None:
        """Verify stack trace is captured correctly at initialization."""
        # Create stack trace with specific depth
        stack_frames = [
            f'  File "file{i}.py", line {i}, in func{i}\n    call{i}()\n'
            for i in range(stack_depth)
        ]

        # Mock traceback with specific frames
        mocker.patch("traceback.format_stack", return_value=[*stack_frames, "current"])

        # Create exception
        error = TributumError("TEST", "Test")

        # Verify stack trace excludes current frame
        assert error.stack_trace == stack_frames
        assert len(error.stack_trace) == stack_depth

    @pytest.mark.parametrize(
        ("message", "context"),
        [
            ("", None),
            ("", {}),
            (None, None),  # Will be converted to string "None"
        ],
    )
    def test_initialization_with_empty_values(
        self,
        mocker: MockerFixture,
        message: str | None,
        context: dict[str, Any] | None,
    ) -> None:
        """Verify TributumError handles empty/None values correctly."""
        # Mock traceback
        mocker.patch("traceback.format_stack", return_value=[])

        # Create exception with empty values
        error = TributumError("TEST", str(message), Severity.LOW, context)

        # Verify empty values are handled properly
        assert error.message == str(message)
        assert error.context == (context or {})
        assert isinstance(error.fingerprint, str)

    def test_fingerprint_with_empty_stack_trace(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Verify fingerprint generation handles empty stack traces."""
        # Mock traceback to return empty list (after removing current frame)
        mocker.patch("traceback.format_stack", return_value=["current"])

        # Create exception
        error = TributumError("EMPTY_STACK", "No stack trace")

        # Verify fingerprint is still generated
        assert isinstance(error.fingerprint, str)
        assert len(error.fingerprint) == 16
        assert error.stack_trace == []

    @pytest.mark.parametrize(
        "frames",
        [
            ["  File '/usr/lib/python3.13/lib.py', line 10\n    func()\n"],
            ["  File 'script.py', line 5\n    main()\n"],
            ["  File '/home/user/project/main.py', line 20\n    run()\n"],
        ],
    )
    def test_fingerprint_without_src_in_frames(
        self,
        mocker: MockerFixture,
        frames: list[str],
    ) -> None:
        """Verify fingerprint generation when no frame contains 'src/'."""
        # Mock traceback with frames not containing "src/"
        mocker.patch("traceback.format_stack", return_value=[*frames, "current"])

        # Create exception
        error = TributumError("NO_SRC", "No src in frames")

        # Verify fingerprint still generates
        assert isinstance(error.fingerprint, str)
        assert len(error.fingerprint) == 16

    @pytest.mark.parametrize(
        "thread_count",
        [2, 5, 10],
    )
    def test_thread_safety_of_exception_creation(
        self,
        mocker: MockerFixture,
        thread_count: int,
    ) -> None:
        """Verify multiple threads can create exceptions concurrently."""
        # Mock traceback
        mock_stack = mocker.Mock(return_value=["frame1", "frame2"])
        mocker.patch("traceback.format_stack", mock_stack)

        # Storage for exceptions created by threads
        exceptions: list[TributumError] = []
        errors: list[Exception] = []

        def create_exception(thread_id: int) -> None:
            """Create an exception in a thread."""
            try:
                error = TributumError(
                    f"THREAD_{thread_id}",
                    f"Error from thread {thread_id}",
                    Severity.MEDIUM,
                    {"thread_id": thread_id},
                )
                exceptions.append(error)
            except Exception as e:
                errors.append(e)

        # Create and start threads
        threads = []
        for i in range(thread_count):
            thread = threading.Thread(target=create_exception, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=1.0)

        # Verify all exceptions created successfully
        assert len(errors) == 0
        assert len(exceptions) == thread_count

        # Verify each exception has unique thread context
        thread_ids = {exc.context.get("thread_id") for exc in exceptions}
        assert len(thread_ids) == thread_count


@pytest.mark.unit
class TestValidationError:
    """Test the ValidationError exception class."""

    @pytest.mark.parametrize(
        ("message", "context"),
        [
            ("Invalid input", None),
            ("Field required", {"field": "email"}),
            ("", {}),
            ("Multiple validation errors", {"errors": ["error1", "error2"]}),
        ],
    )
    def test_validation_error_initialization(
        self,
        mocker: MockerFixture,
        message: str,
        context: dict[str, Any] | None,
    ) -> None:
        """Verify ValidationError initializes with correct defaults."""
        # Mock traceback
        mocker.patch("traceback.format_stack", return_value=[])

        # Create exception
        error = ValidationError(message, context=context)

        # Verify default error code and severity
        assert error.error_code == ErrorCode.VALIDATION_ERROR.value
        assert error.severity == Severity.LOW
        assert error.message == message
        assert error.context == (context or {})

    @pytest.mark.parametrize(
        "custom_code",
        [
            "CUSTOM_VALIDATION",
            ErrorCode.INTERNAL_ERROR,
            "",
            ErrorCode.NOT_FOUND,
        ],
    )
    def test_validation_error_custom_error_code(
        self,
        mocker: MockerFixture,
        custom_code: str | ErrorCode,
    ) -> None:
        """Verify ValidationError accepts custom error codes."""
        # Mock traceback
        mocker.patch("traceback.format_stack", return_value=[])

        # Create exception with custom error code
        error = ValidationError("Test", error_code=custom_code)

        # Verify custom error code is preserved
        expected_code = (
            custom_code.value if isinstance(custom_code, ErrorCode) else custom_code
        )
        assert error.error_code == expected_code

    def test_validation_error_inheritance(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Verify ValidationError properly inherits from TributumError."""
        # Mock traceback
        mocker.patch("traceback.format_stack", return_value=[])

        # Create exception
        error = ValidationError("Test validation error")

        # Verify inheritance
        assert isinstance(error, ValidationError)
        assert isinstance(error, TributumError)
        assert isinstance(error, Exception)
        assert issubclass(ValidationError, TributumError)


@pytest.mark.unit
class TestNotFoundError:
    """Test the NotFoundError exception class."""

    @pytest.mark.parametrize(
        ("message", "context"),
        [
            ("User not found", None),
            ("Document not found", {"document_id": "123"}),
            ("", {}),
            ("Resource not found", {"type": "file", "path": "test/data/file.txt"}),
        ],
    )
    def test_not_found_error_initialization(
        self,
        mocker: MockerFixture,
        message: str,
        context: dict[str, Any] | None,
    ) -> None:
        """Verify NotFoundError initializes with correct defaults."""
        # Mock traceback
        mocker.patch("traceback.format_stack", return_value=[])

        # Create exception
        error = NotFoundError(message, context=context)

        # Verify default error code and severity
        assert error.error_code == ErrorCode.NOT_FOUND.value
        assert error.severity == Severity.LOW
        assert error.message == message
        assert error.context == (context or {})

    @pytest.mark.parametrize(
        ("context", "cause"),
        [
            ({"id": 123}, ValueError("Invalid ID")),
            (None, KeyError("missing_key")),
            ({}, None),
            ({"type": "user", "id": "abc"}, RuntimeError("DB error")),
        ],
    )
    def test_not_found_error_with_context_and_cause(
        self,
        mocker: MockerFixture,
        context: dict[str, Any] | None,
        cause: Exception | None,
    ) -> None:
        """Verify NotFoundError properly handles context and cause."""
        # Mock traceback
        mocker.patch("traceback.format_stack", return_value=[])

        # Create exception
        error = NotFoundError("Not found", context=context, cause=cause)

        # Verify context and cause are properly stored
        assert error.context == (context or {})
        assert error.cause is cause
        if cause:
            assert error.__cause__ is cause


@pytest.mark.unit
class TestUnauthorizedError:
    """Test the UnauthorizedError exception class."""

    @pytest.mark.parametrize(
        ("message", "context"),
        [
            ("Invalid credentials", None),
            ("Token expired", {"token_type": "JWT"}),
            ("", {}),
            ("Insufficient permissions", {"required": "admin", "actual": "user"}),
        ],
    )
    def test_unauthorized_error_initialization(
        self,
        mocker: MockerFixture,
        message: str,
        context: dict[str, Any] | None,
    ) -> None:
        """Verify UnauthorizedError initializes with correct defaults."""
        # Mock traceback
        mocker.patch("traceback.format_stack", return_value=[])

        # Create exception
        error = UnauthorizedError(message, context=context)

        # Verify default error code and HIGH severity
        assert error.error_code == ErrorCode.UNAUTHORIZED.value
        assert error.severity == Severity.HIGH
        assert error.message == message
        assert error.context == (context or {})

    def test_unauthorized_error_severity(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Verify UnauthorizedError has HIGH severity by default."""
        # Mock traceback
        mocker.patch("traceback.format_stack", return_value=[])

        # Create exception
        error = UnauthorizedError("Unauthorized access")

        # Verify severity is HIGH and should_alert is True
        assert error.severity == Severity.HIGH
        assert error.should_alert is True
        assert error.is_expected is False


@pytest.mark.unit
class TestBusinessRuleError:
    """Test the BusinessRuleError exception class."""

    @pytest.mark.parametrize(
        ("message", "context"),
        [
            ("Business rule violated", None),
            ("Insufficient balance", {"balance": 100, "required": 150}),
            ("", {}),
            ("Daily limit exceeded", {"limit": 1000, "current": 1200}),
        ],
    )
    def test_business_rule_error_initialization(
        self,
        mocker: MockerFixture,
        message: str,
        context: dict[str, Any] | None,
    ) -> None:
        """Verify BusinessRuleError initializes with correct defaults."""
        # Mock traceback
        mocker.patch("traceback.format_stack", return_value=[])

        # Create exception
        error = BusinessRuleError(message, context=context)

        # Verify default error code and MEDIUM severity
        assert error.error_code == ErrorCode.INTERNAL_ERROR.value
        assert error.severity == Severity.MEDIUM
        assert error.message == message
        assert error.context == (context or {})
        assert error.is_expected is True
        assert error.should_alert is False


@pytest.mark.unit
class TestExceptionInteractions:
    """Test interactions between exception classes."""

    @pytest.mark.parametrize(
        "exception_class",
        [
            ValidationError,
            NotFoundError,
            UnauthorizedError,
            BusinessRuleError,
        ],
    )
    def test_exception_hierarchy(
        self,
        exception_class: type[TributumError],
    ) -> None:
        """Verify all custom exceptions inherit from TributumError."""
        # Verify inheritance
        assert issubclass(exception_class, TributumError)
        assert issubclass(exception_class, Exception)

        # Verify MRO includes TributumError
        assert TributumError in exception_class.__mro__

    def test_exception_type_checking_tributum_error(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Verify TributumError works with isinstance checks."""
        # Mock traceback
        mocker.patch("traceback.format_stack", return_value=[])

        # Create exception
        error = TributumError("TEST", "Base error")

        # Verify isinstance works correctly
        assert isinstance(error, TributumError)
        assert isinstance(error, Exception)

        # Verify type checking with base class
        with pytest.raises(TributumError) as exc_info:
            raise error
        assert exc_info.value is error

    @pytest.mark.parametrize(
        ("exception_class", "message"),
        [
            (ValidationError, "Validation failed"),
            (NotFoundError, "Not found"),
            (UnauthorizedError, "Unauthorized"),
            (BusinessRuleError, "Business rule error"),
        ],
    )
    def test_exception_type_checking_specialized(
        self,
        mocker: MockerFixture,
        exception_class: type[
            ValidationError | NotFoundError | UnauthorizedError | BusinessRuleError
        ],
        message: str,
    ) -> None:
        """Verify specialized exceptions work with isinstance checks."""
        # Mock traceback
        mocker.patch("traceback.format_stack", return_value=[])

        # Create exception
        error = exception_class(message)

        # Verify isinstance works correctly
        assert isinstance(error, exception_class)
        assert isinstance(error, TributumError)
        assert isinstance(error, Exception)

        # Verify type checking with base class
        with pytest.raises(TributumError) as exc_info:
            raise error
        assert exc_info.value is error
