"""Base exception classes and error codes for the Tributum application.

This module provides the foundation for consistent error handling across
the application, with structured error codes and exception hierarchy.
"""

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

    Attributes:
        error_code: A unique identifier for the error type
        message: A human-readable error message
        severity: The severity level of the error
        context: Additional context information about the error
    """

    def __init__(
        self,
        error_code: str | ErrorCode,
        message: str,
        severity: Severity = Severity.MEDIUM,
        context: dict[str, Any] | None = None,
    ) -> None:
        """Initialize the exception with error details.

        Args:
            error_code: Unique identifier for the error type (string or ErrorCode enum)
            message: Human-readable error message
            severity: Severity level of the error (defaults to MEDIUM)
            context: Additional context information about the error
        """
        self.error_code = (
            error_code.value if isinstance(error_code, ErrorCode) else error_code
        )
        self.message = message
        self.severity = severity
        self.context = context or {}
        super().__init__(message)

    def __str__(self) -> str:
        """Return a string representation of the exception.

        Returns:
            A formatted string containing the error code and message
        """
        return f"[{self.error_code}] {self.message}"

    def __repr__(self) -> str:
        """Return a detailed representation of the exception.

        Returns:
            A string showing the class name, error code, message, severity, and context
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
    """

    def __init__(
        self,
        message: str,
        error_code: str | ErrorCode = ErrorCode.VALIDATION_ERROR,
        context: dict[str, Any] | None = None,
    ) -> None:
        """Initialize validation error with message and optional error code.

        Args:
            message: Description of the validation failure
            error_code: Error code (defaults to VALIDATION_ERROR)
            context: Additional context information about the error
        """
        super().__init__(error_code, message, Severity.LOW, context)


class NotFoundError(TributumError):
    """Exception raised when a requested resource cannot be found.

    This exception should be used when attempting to access a resource
    (user, document, configuration, etc.) that doesn't exist.
    """

    def __init__(
        self,
        message: str,
        error_code: str | ErrorCode = ErrorCode.NOT_FOUND,
        context: dict[str, Any] | None = None,
    ) -> None:
        """Initialize not found error with message and optional error code.

        Args:
            message: Description of what resource was not found
            error_code: Error code (defaults to NOT_FOUND)
            context: Additional context information about the error
        """
        super().__init__(error_code, message, Severity.LOW, context)


class UnauthorizedError(TributumError):
    """Exception raised when authentication or authorization fails.

    This exception should be used when a user is not authenticated
    or lacks the necessary permissions to perform an action.
    """

    def __init__(
        self,
        message: str,
        error_code: str | ErrorCode = ErrorCode.UNAUTHORIZED,
        context: dict[str, Any] | None = None,
    ) -> None:
        """Initialize unauthorized error with message and optional error code.

        Args:
            message: Description of the authorization failure
            error_code: Error code (defaults to UNAUTHORIZED)
            context: Additional context information about the error
        """
        super().__init__(error_code, message, Severity.HIGH, context)


class BusinessRuleError(TributumError):
    """Exception raised when a business rule violation occurs.

    This exception should be used when an operation violates business
    logic constraints that aren't simple validation errors.
    """

    def __init__(
        self,
        message: str,
        error_code: str | ErrorCode = ErrorCode.INTERNAL_ERROR,
        context: dict[str, Any] | None = None,
    ) -> None:
        """Initialize business rule error with message and optional error code.

        Args:
            message: Description of the business rule violation
            error_code: Error code (defaults to INTERNAL_ERROR)
            context: Additional context information about the error
        """
        super().__init__(error_code, message, Severity.MEDIUM, context)
