"""Integration tests for generic exception handling and debug info."""

import json

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from src.api.middleware.error_handler import generic_exception_handler
from src.core.config import get_settings
from src.core.exceptions import ErrorCode


@pytest.mark.integration
class TestGenericException:
    """Test handling of unhandled exceptions."""

    async def test_generic_exception_development(
        self, app_with_handlers: FastAPI
    ) -> None:
        """Test generic exception in development shows details."""
        # Due to a known issue with TestClient and ASGI middleware,
        # we need to test the exception handler directly

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
            "app": app_with_handlers,
        }
        request = Request(scope)

        # Test the handler directly

        test_exception = RuntimeError("Something went wrong")
        response = await generic_exception_handler(request, test_exception)

        assert response.status_code == 500

        if isinstance(response.body, bytes):
            body_str = response.body.decode()
        else:
            body_str = str(response.body)
        data = json.loads(body_str)
        assert data["error_code"] == ErrorCode.INTERNAL_ERROR.value
        assert "RuntimeError" in data["message"]
        assert data["details"]["error"] == "Something went wrong"
        assert data["severity"] == "CRITICAL"

    async def test_generic_exception_production(self, production_env: None) -> None:
        """Test generic exception in production hides details."""
        # Note: production_env fixture sets up production environment
        # clear_settings_cache fixture automatically handles cache clearing
        _ = production_env  # Fixture used for its side effects

        # Test the handler directly in production mode

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

        test_exception = RuntimeError("Internal details should be hidden")
        response = await generic_exception_handler(request, test_exception)

        assert response.status_code == 500

        if isinstance(response.body, bytes):
            body_str = response.body.decode()
        else:
            body_str = str(response.body)
        data = json.loads(body_str)
        assert data["error_code"] == ErrorCode.INTERNAL_ERROR.value
        assert data["message"] == "An internal server error occurred"
        assert data["details"] is None
        assert data["severity"] == "CRITICAL"


@pytest.mark.integration
class TestDebugInfoInDevelopment:
    """Test that debug info is included in development mode."""

    def test_tributum_error_includes_debug_info(self, client: TestClient) -> None:
        """Test that TributumError includes debug info in development."""
        # Check current environment
        settings = get_settings()

        response = client.get("/test/validation-error")
        data = response.json()

        # In development mode, debug_info should be present
        assert "debug_info" in data

        if settings.environment == "development":
            # In development, debug_info should be populated
            debug_info = data["debug_info"]
            assert debug_info is not None, (
                "debug_info should not be None in development mode"
            )

            # Check debug info structure
            assert "stack_trace" in debug_info
            assert "error_context" in debug_info
            assert "exception_type" in debug_info

            # Verify content
            assert isinstance(debug_info["stack_trace"], list)
            assert len(debug_info["stack_trace"]) > 0
            assert debug_info["exception_type"] == "ValidationError"
            assert debug_info["error_context"]["field"] == "email"
            assert debug_info["error_context"]["value"] == "not-an-email"
        else:
            # In production, debug_info should be None
            assert data["debug_info"] is None, (
                "debug_info should be None in production mode"
            )

    async def test_generic_exception_includes_debug_info(
        self, app_with_handlers: FastAPI
    ) -> None:
        """Test that generic exceptions include debug info in development."""
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
            "app": app_with_handlers,
        }
        request = Request(scope)

        # Test the handler directly

        test_exception = RuntimeError("Test error with context")
        response = await generic_exception_handler(request, test_exception)

        if isinstance(response.body, bytes):
            body_str = response.body.decode()
        else:
            body_str = str(response.body)
        data = json.loads(body_str)

        # Check based on environment

        settings = get_settings()

        assert "debug_info" in data

        if settings.environment == "development":
            # Should have debug_info in development
            debug_info = data["debug_info"]
            assert debug_info is not None

            assert "stack_trace" in debug_info
            assert "error_context" in debug_info
            assert "exception_type" in debug_info

            assert debug_info["exception_type"] == "RuntimeError"
            assert (
                debug_info["error_context"]["error_message"]
                == "Test error with context"
            )
        else:
            # Should be None in production
            assert data["debug_info"] is None

    async def test_no_debug_info_in_production(self, production_env: None) -> None:
        """Test that debug info is NOT included in production."""
        # Note: production_env fixture sets up production environment
        # clear_settings_cache fixture automatically handles cache clearing
        _ = production_env  # Fixture used for its side effects

        # Test the handler directly in production mode

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

        test_exception = RuntimeError("Internal details")
        response = await generic_exception_handler(request, test_exception)

        if isinstance(response.body, bytes):
            body_str = response.body.decode()
        else:
            body_str = str(response.body)
        data = json.loads(body_str)

        # Should NOT have debug_info in production
        assert data["debug_info"] is None
