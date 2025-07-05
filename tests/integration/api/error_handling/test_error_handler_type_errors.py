"""Integration tests for error handler type error handling."""

import pytest
from fastapi import Request

from src.api.middleware.error_handler import (
    http_exception_handler,
    tributum_error_handler,
    validation_error_handler,
)


@pytest.fixture
def mock_request() -> Request:
    """Create a mock Request object for testing error handlers."""
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/test",
        "query_string": b"",
        "headers": [],
        "server": ("testserver", 80),
        "client": ("testclient", 12345),
        "asgi": {"version": "3.0"},
        "scheme": "http",
        "root_path": "",
    }
    return Request(scope)


@pytest.mark.integration
class TestErrorHandlerTypeErrors:
    """Test TypeError handling in error handlers.

    These tests verify that error handlers properly validate the exception types
    they receive and raise TypeError when given incorrect exception types.
    This is important for maintaining type safety in the error handling pipeline.
    """

    async def test_tributum_error_handler_type_error(
        self, mock_request: Request
    ) -> None:
        """Test that tributum_error_handler raises TypeError for non-TributumError."""
        # Pass a non-TributumError exception
        regular_exception = ValueError("Not a TributumError")

        with pytest.raises(TypeError, match="Expected TributumError, got ValueError"):
            await tributum_error_handler(mock_request, regular_exception)

    async def test_validation_error_handler_type_error(
        self, mock_request: Request
    ) -> None:
        """Test validation_error_handler TypeError for non-RequestValidationError."""
        # Pass a non-RequestValidationError exception
        regular_exception = ValueError("Not a RequestValidationError")

        with pytest.raises(
            TypeError, match="Expected RequestValidationError, got ValueError"
        ):
            await validation_error_handler(mock_request, regular_exception)

    async def test_http_exception_handler_type_error(
        self, mock_request: Request
    ) -> None:
        """Test that http_exception_handler raises TypeError for non-HTTPException."""
        # Pass a non-HTTPException
        regular_exception = ValueError("Not an HTTPException")

        with pytest.raises(TypeError, match="Expected HTTPException, got ValueError"):
            await http_exception_handler(mock_request, regular_exception)
