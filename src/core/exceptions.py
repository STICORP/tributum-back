"""Base exception classes and error codes for the Tributum application.

This module provides the foundation for consistent error handling across
the application, with structured error codes and exception hierarchy.
"""


class TributumError(Exception):
    """Base exception class for all Tributum application exceptions.

    All custom exceptions in the application should inherit from this class
    to ensure consistent error handling and formatting.

    Attributes:
        error_code: A unique identifier for the error type
        message: A human-readable error message
    """

    def __init__(self, error_code: str, message: str) -> None:
        """Initialize the exception with an error code and message.

        Args:
            error_code: Unique identifier for the error type
            message: Human-readable error message
        """
        self.error_code = error_code
        self.message = message
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
            A string showing the class name, error code, and message
        """
        class_name = self.__class__.__name__
        return f"{class_name}(error_code='{self.error_code}', message='{self.message}')"
