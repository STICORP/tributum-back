"""Structured exception hierarchy for consistent error handling.

This module defines the complete exception system for the Tributum application,
providing a rich error model that supports debugging, monitoring, and client
communication.

Key components:
- **ErrorCode enum**: Standardized error identifiers for programmatic handling
- **Severity enum**: Error classification for monitoring and alerting
- **TributumError**: Base exception with rich context and fingerprinting
- **Specialized exceptions**: Type-specific errors (validation, auth, etc.)

Features:
- **Error fingerprinting**: Automatic grouping of similar errors
- **Stack trace capture**: Full context at error creation time
- **Exception chaining**: Preserves original cause for debugging
- **Rich context**: Structured data for comprehensive error analysis
- **Severity levels**: Enables appropriate alerting and response

The exception hierarchy enables both specific error handling where needed
and generic handling at API boundaries for consistent client responses.
"""

import hashlib
import traceback
from enum import Enum
from typing import Any


class ErrorCode(Enum):
    """Standardized error codes for the Tributum application.

    These error codes provide consistent identification of error types
    across the application, enabling proper error handling and monitoring.
    """

    # System errors
    INTERNAL_ERROR = "INTERNAL_ERROR"
    """An unexpected internal error occurred in the system."""

    # Validation errors
    VALIDATION_ERROR = "VALIDATION_ERROR"
    """Input validation failed due to invalid or malformed data."""

    # Resource errors
    NOT_FOUND = "NOT_FOUND"
    """The requested resource could not be found."""

    # Authentication/Authorization errors
    UNAUTHORIZED = "UNAUTHORIZED"
    """Authentication failed or user is not authorized for this action."""


class Severity(Enum):
    """Severity levels for errors in the Tributum application.

    These severity levels help categorize the impact and urgency of errors,
    enabling appropriate handling, monitoring, and alerting strategies.
    """

    LOW = "LOW"
    """Low severity errors that don't significantly impact functionality."""

    MEDIUM = "MEDIUM"
    """Medium severity errors that may affect some features but not critical ops."""

    HIGH = "HIGH"
    """High severity errors impacting critical functionality or data integrity."""

    CRITICAL = "CRITICAL"
    """Critical errors requiring immediate attention, may cause system failures."""


class TributumError(Exception):
    """Base exception class for all Tributum application exceptions.

    All custom exceptions in the application should inherit from this class
    to ensure consistent error handling and formatting.

    Args:
        error_code: Unique identifier for the error type (string or ErrorCode enum)
        message: Human-readable error message
        severity: Severity level of the error (defaults to MEDIUM)
        context: Additional context information about the error
        cause: The original exception that caused this error
    """

    def __init__(
        self,
        error_code: str | ErrorCode,
        message: str,
        severity: Severity = Severity.MEDIUM,
        context: dict[str, Any] | None = None,
        cause: Exception | None = None,
    ) -> None:
        self.error_code = (
            error_code.value if isinstance(error_code, ErrorCode) else error_code
        )
        self.message = message
        self.severity = severity
        self.context = context or {}
        self.cause = cause

        # Capture stack trace at creation time
        self.stack_trace = traceback.format_stack()[:-1]  # Exclude this frame

        # Generate fingerprint based on error type and location
        self.fingerprint = self._generate_fingerprint()

        # Set up proper exception chaining
        super().__init__(message)
        if cause:
            self.__cause__ = cause

    def _generate_fingerprint(self) -> str:
        """Generate a fingerprint for error grouping.

        Creates a hash based on the error type and the location where it was raised,
        allowing similar errors to be grouped together in monitoring systems.

        Returns:
            str: A hash string for error grouping
        """
        # Use the first few frames from the stack trace to identify location
        max_frames = 5
        relevant_frames = (
            self.stack_trace[-max_frames:]
            if len(self.stack_trace) > max_frames
            else self.stack_trace
        )

        # Create a string combining error type and location
        fingerprint_data = f"{self.__class__.__name__}:{self.error_code}"

        # Add file and line info from relevant frames
        for frame in relevant_frames:
            if "site-packages" not in frame and "src/" in frame:
                # Extract file and line number from the frame
                lines = frame.strip().split("\n")
                if lines:
                    fingerprint_data += f":{lines[0]}"

        # Generate hash
        return hashlib.sha256(fingerprint_data.encode()).hexdigest()[:16]

    @property
    def is_expected(self) -> bool:
        """Determine if this is an expected error based on severity.

        Expected errors are those that occur during normal operation due to
        user input, business rules, or other predictable conditions. These
        should be logged at a lower level and not trigger alerts.

        Returns:
            bool: True if the error is expected (LOW or MEDIUM severity)
        """
        return self.severity in (Severity.LOW, Severity.MEDIUM)

    @property
    def should_alert(self) -> bool:
        """Determine if this error should trigger alerts.

        High severity errors indicate problems that need immediate attention,
        such as security issues, data integrity problems, or system failures.

        Returns:
            bool: True if the error should trigger alerts (HIGH or CRITICAL severity)
        """
        return self.severity in (Severity.HIGH, Severity.CRITICAL)

    def __str__(self) -> str:
        """Return a string representation of the exception.

        Returns:
            str: A formatted string containing the error code and message
        """
        return f"[{self.error_code}] {self.message}"

    def __repr__(self) -> str:
        """Return a detailed representation of the exception.

        Returns:
            str: A string showing the class name, error code, message, severity,
                and context
        """
        class_name = self.__class__.__name__
        context_str = f", context={self.context}" if self.context else ""
        return (
            f"{class_name}(error_code='{self.error_code}', "
            f"message='{self.message}', severity={self.severity.value}{context_str})"
        )


class ValidationError(TributumError):
    """Exception raised when input validation fails.

    This exception should be used when user input or data doesn't meet
    the expected format, type, or business validation rules.

    Args:
        message: Description of the validation failure
        error_code: Error code (defaults to VALIDATION_ERROR)
        context: Additional context information about the error
        cause: The original exception that caused this error
    """

    def __init__(
        self,
        message: str,
        error_code: str | ErrorCode = ErrorCode.VALIDATION_ERROR,
        context: dict[str, Any] | None = None,
        cause: Exception | None = None,
    ) -> None:
        super().__init__(error_code, message, Severity.LOW, context, cause)


class NotFoundError(TributumError):
    """Exception raised when a requested resource cannot be found.

    This exception should be used when attempting to access a resource
    (user, document, configuration, etc.) that doesn't exist.

    Args:
        message: Description of what resource was not found
        error_code: Error code (defaults to NOT_FOUND)
        context: Additional context information about the error
        cause: The original exception that caused this error
    """

    def __init__(
        self,
        message: str,
        error_code: str | ErrorCode = ErrorCode.NOT_FOUND,
        context: dict[str, Any] | None = None,
        cause: Exception | None = None,
    ) -> None:
        super().__init__(error_code, message, Severity.LOW, context, cause)


class UnauthorizedError(TributumError):
    """Exception raised when authentication or authorization fails.

    This exception should be used when a user is not authenticated
    or lacks the necessary permissions to perform an action.

    Args:
        message: Description of the authorization failure
        error_code: Error code (defaults to UNAUTHORIZED)
        context: Additional context information about the error
        cause: The original exception that caused this error
    """

    def __init__(
        self,
        message: str,
        error_code: str | ErrorCode = ErrorCode.UNAUTHORIZED,
        context: dict[str, Any] | None = None,
        cause: Exception | None = None,
    ) -> None:
        super().__init__(error_code, message, Severity.HIGH, context, cause)


class BusinessRuleError(TributumError):
    """Exception raised when a business rule violation occurs.

    This exception should be used when an operation violates business
    logic constraints that aren't simple validation errors.

    Args:
        message: Description of the business rule violation
        error_code: Error code (defaults to INTERNAL_ERROR)
        context: Additional context information about the error
        cause: The original exception that caused this error
    """

    def __init__(
        self,
        message: str,
        error_code: str | ErrorCode = ErrorCode.INTERNAL_ERROR,
        context: dict[str, Any] | None = None,
        cause: Exception | None = None,
    ) -> None:
        super().__init__(error_code, message, Severity.MEDIUM, context, cause)
