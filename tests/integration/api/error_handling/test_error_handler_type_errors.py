"""Integration tests for error handler type error handling."""

import pytest
from fastapi import Request

from src.api.middleware.error_handler import (
    http_exception_handler,
    tributum_error_handler,
    validation_error_handler,
)


@pytest.mark.integration
class TestErrorHandlerTypeErrors:
    """Test TypeError handling in error handlers."""

    async def test_tributum_error_handler_type_error(self) -> None:
        """Test that tributum_error_handler raises TypeError for non-TributumError."""
        # Create a mock request
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
        request = Request(scope)

        # Pass a non-TributumError exception
        regular_exception = ValueError("Not a TributumError")

        with pytest.raises(TypeError) as exc_info:
            await tributum_error_handler(request, regular_exception)

        assert "Expected TributumError, got ValueError" in str(exc_info.value)

    async def test_validation_error_handler_type_error(self) -> None:
        """Test validation_error_handler TypeError for non-RequestValidationError."""
        # Create a mock request
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
        request = Request(scope)

        # Pass a non-RequestValidationError exception
        regular_exception = ValueError("Not a RequestValidationError")

        with pytest.raises(TypeError) as exc_info:
            await validation_error_handler(request, regular_exception)

        assert "Expected RequestValidationError, got ValueError" in str(exc_info.value)

    async def test_http_exception_handler_type_error(self) -> None:
        """Test that http_exception_handler raises TypeError for non-HTTPException."""
        # Create a mock request
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
        request = Request(scope)

        # Pass a non-HTTPException
        regular_exception = ValueError("Not an HTTPException")

        with pytest.raises(TypeError) as exc_info:
            await http_exception_handler(request, regular_exception)

        assert "Expected HTTPException, got ValueError" in str(exc_info.value)
