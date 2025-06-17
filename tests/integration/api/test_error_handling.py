"""Integration tests for global error handling.

Tests that the error handlers properly handle various exception types,
return correct HTTP status codes, and format error responses consistently.
"""

import pytest
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.testclient import TestClient

from src.api.main import create_app
from src.api.schemas.errors import ErrorResponse
from src.core.exceptions import (
    BusinessRuleError,
    ErrorCode,
    NotFoundError,
    Severity,
    UnauthorizedError,
    ValidationError,
)
from src.core.logging import configure_structlog

# Configure logging for tests
configure_structlog()


@pytest.fixture
def app_with_handlers() -> FastAPI:
    """Create an app with exception handlers and test endpoints."""
    app = create_app()  # Exception handlers are already registered in create_app

    # Add test endpoints that raise various exceptions
    @app.get("/test/validation-error")
    async def raise_validation_error() -> None:
        raise ValidationError(
            "Email format is invalid",
            context={"field": "email", "value": "not-an-email"},
        )

    @app.get("/test/not-found")
    async def raise_not_found() -> None:
        raise NotFoundError(
            "User not found",
            context={"user_id": 123},
        )

    @app.get("/test/unauthorized")
    async def raise_unauthorized() -> None:
        raise UnauthorizedError("Invalid API key")

    @app.get("/test/business-rule")
    async def raise_business_rule() -> None:
        raise BusinessRuleError(
            "Insufficient balance",
            context={"required": 100, "available": 50},
        )

    @app.get("/test/http-exception")
    async def raise_http_exception() -> None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden",
        )

    @app.get("/test/generic-exception")
    async def raise_generic_exception() -> None:
        raise RuntimeError("Something went wrong")

    from pydantic import BaseModel

    class ValidationData(BaseModel):
        data: dict[str, int]

    @app.post("/test/request-validation")
    async def request_validation(body: ValidationData) -> dict[str, int]:
        """Endpoint that requires specific data structure."""
        return {"result": sum(body.data.values())}

    @app.get("/test/custom-severity")
    async def raise_custom_severity() -> None:
        raise ValidationError(
            "Critical validation failure",
            context={"severity_override": True},
        )

    return app


@pytest.fixture
def client(app_with_handlers: FastAPI) -> TestClient:
    """Create a test client."""
    return TestClient(app_with_handlers)


class TestTributumErrorHandling:
    """Test handling of TributumError and its subclasses."""

    def test_validation_error(self, client: TestClient) -> None:
        """Test ValidationError returns 400 with proper format."""
        response = client.get("/test/validation-error")

        assert response.status_code == 400

        data = response.json()
        assert data["error_code"] == ErrorCode.VALIDATION_ERROR.value
        assert data["message"] == "Email format is invalid"
        assert data["details"]["field"] == "email"
        assert data["details"]["value"] == "not-an-email"
        assert data["severity"] == Severity.LOW.value
        assert "correlation_id" in data
        assert "request_id" in data
        assert data["request_id"].startswith("req-")
        assert "timestamp" in data
        assert "service_info" in data

    def test_not_found_error(self, client: TestClient) -> None:
        """Test NotFoundError returns 404 with proper format."""
        response = client.get("/test/not-found")

        assert response.status_code == 404

        data = response.json()
        assert data["error_code"] == ErrorCode.NOT_FOUND.value
        assert data["message"] == "User not found"
        assert data["details"]["user_id"] == 123
        assert data["severity"] == Severity.LOW.value

    def test_unauthorized_error(self, client: TestClient) -> None:
        """Test UnauthorizedError returns 401 with proper format."""
        response = client.get("/test/unauthorized")

        assert response.status_code == 401

        data = response.json()
        assert data["error_code"] == ErrorCode.UNAUTHORIZED.value
        assert data["message"] == "Invalid API key"
        assert data["severity"] == Severity.HIGH.value

    def test_business_rule_error(self, client: TestClient) -> None:
        """Test BusinessRuleError returns 422 with proper format."""
        response = client.get("/test/business-rule")

        assert response.status_code == 422

        data = response.json()
        assert data["error_code"] == ErrorCode.INTERNAL_ERROR.value
        assert data["message"] == "Insufficient balance"
        assert data["details"]["required"] == 100
        assert data["details"]["available"] == 50
        assert data["severity"] == Severity.MEDIUM.value


class TestRequestValidationError:
    """Test handling of FastAPI RequestValidationError."""

    def test_request_validation_error(self, client: TestClient) -> None:
        """Test request validation error returns 422 with field details."""
        response = client.post(
            "/test/request-validation",
            json={"data": "not-a-dict"},  # Should be dict[str, int]
        )

        assert response.status_code == 422

        data = response.json()
        assert data["error_code"] == ErrorCode.VALIDATION_ERROR.value
        assert data["message"] == "Request validation failed"
        assert "validation_errors" in data["details"]
        assert data["severity"] == "LOW"

    def test_missing_required_field(self, client: TestClient) -> None:
        """Test missing required field in request."""
        response = client.post("/test/request-validation", json={})

        assert response.status_code == 422

        data = response.json()
        assert "validation_errors" in data["details"]
        # Field errors should be grouped
        assert isinstance(data["details"]["validation_errors"], dict)

    def test_root_validation_error(
        self, app_with_handlers: FastAPI, client: TestClient
    ) -> None:
        """Test validation error at root level (no specific field)."""
        # Create an endpoint that has root-level validation
        from pydantic import BaseModel, model_validator

        class RootValidationModel(BaseModel):
            value1: int
            value2: int

            @model_validator(mode="after")
            def check_sum(self) -> "RootValidationModel":
                if self.value1 + self.value2 > 100:
                    raise ValueError("Sum must not exceed 100")
                return self

        @app_with_handlers.post("/test/root-validation")
        async def root_validation_endpoint(body: RootValidationModel) -> dict[str, int]:
            return {"sum": body.value1 + body.value2}

        # Send request that triggers root validation error
        response = client.post(
            "/test/root-validation",
            json={"value1": 60, "value2": 50},  # Sum = 110, exceeds limit
        )

        assert response.status_code == 422

        data = response.json()
        assert data["error_code"] == ErrorCode.VALIDATION_ERROR.value
        assert "validation_errors" in data["details"]
        # Root validation errors should be under "root" field
        assert "root" in data["details"]["validation_errors"]


class TestHTTPException:
    """Test handling of Starlette HTTPException."""

    def test_http_exception(self, client: TestClient) -> None:
        """Test HTTPException is converted to our error format."""
        response = client.get("/test/http-exception")

        assert response.status_code == 403

        data = response.json()
        assert data["error_code"] == ErrorCode.INTERNAL_ERROR.value
        assert data["message"] == "Access forbidden"
        assert "correlation_id" in data
        assert "timestamp" in data
        assert "service_info" in data

    def test_http_400_bad_request(self, app_with_handlers: FastAPI) -> None:
        """Test HTTPException with 400 status maps to VALIDATION_ERROR."""

        @app_with_handlers.get("/test/http-400")
        async def raise_http_400() -> None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Bad request data"
            )

        client = TestClient(app_with_handlers)
        response = client.get("/test/http-400")

        assert response.status_code == 400

        data = response.json()
        assert data["error_code"] == ErrorCode.VALIDATION_ERROR.value
        assert data["message"] == "Bad request data"
        assert data["severity"] == "LOW"

    def test_http_401_unauthorized(self, app_with_handlers: FastAPI) -> None:
        """Test HTTPException with 401 status maps to UNAUTHORIZED."""

        @app_with_handlers.get("/test/http-401")
        async def raise_http_401() -> None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )

        client = TestClient(app_with_handlers)
        response = client.get("/test/http-401")

        assert response.status_code == 401

        data = response.json()
        assert data["error_code"] == ErrorCode.UNAUTHORIZED.value
        assert data["message"] == "Authentication required"
        assert data["severity"] == "HIGH"

    def test_http_404_not_found(self, app_with_handlers: FastAPI) -> None:
        """Test HTTPException with 404 status maps to NOT_FOUND."""

        @app_with_handlers.get("/test/http-404")
        async def raise_http_404() -> None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found"
            )

        client = TestClient(app_with_handlers)
        response = client.get("/test/http-404")

        assert response.status_code == 404

        data = response.json()
        assert data["error_code"] == ErrorCode.NOT_FOUND.value
        assert data["message"] == "Resource not found"
        assert data["severity"] == "LOW"

    def test_http_500_server_error(self, app_with_handlers: FastAPI) -> None:
        """Test HTTPException with 500+ status has HIGH severity."""

        @app_with_handlers.get("/test/http-500")
        async def raise_http_500() -> None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Server error occurred",
            )

        client = TestClient(app_with_handlers)
        response = client.get("/test/http-500")

        assert response.status_code == 500

        data = response.json()
        assert data["error_code"] == ErrorCode.INTERNAL_ERROR.value
        assert data["message"] == "Server error occurred"
        assert data["severity"] == "HIGH"

    def test_http_503_service_unavailable(self, app_with_handlers: FastAPI) -> None:
        """Test HTTPException with 503 status (5xx) has HIGH severity."""

        @app_with_handlers.get("/test/http-503")
        async def raise_http_503() -> None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service temporarily unavailable",
            )

        client = TestClient(app_with_handlers)
        response = client.get("/test/http-503")

        assert response.status_code == 503

        data = response.json()
        assert data["error_code"] == ErrorCode.INTERNAL_ERROR.value
        assert data["message"] == "Service temporarily unavailable"
        assert data["severity"] == "HIGH"


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
        from src.api.middleware.error_handler import generic_exception_handler

        test_exception = RuntimeError("Something went wrong")
        response = await generic_exception_handler(request, test_exception)

        assert response.status_code == 500

        import json

        if isinstance(response.body, bytes):
            body_str = response.body.decode()
        else:
            body_str = str(response.body)
        data = json.loads(body_str)
        assert data["error_code"] == ErrorCode.INTERNAL_ERROR.value
        assert "RuntimeError" in data["message"]
        assert data["details"]["error"] == "Something went wrong"
        assert data["severity"] == "CRITICAL"

    async def test_generic_exception_production(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test generic exception in production hides details."""
        # Set production environment
        monkeypatch.setenv("ENVIRONMENT", "production")

        # Create a new app instance to pick up the environment change
        from src.core.config import get_settings

        get_settings.cache_clear()  # Clear settings cache

        # Test the handler directly in production mode
        from src.api.middleware.error_handler import generic_exception_handler

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

        import json

        if isinstance(response.body, bytes):
            body_str = response.body.decode()
        else:
            body_str = str(response.body)
        data = json.loads(body_str)
        assert data["error_code"] == ErrorCode.INTERNAL_ERROR.value
        assert data["message"] == "An internal server error occurred"
        assert data["details"] is None
        assert data["severity"] == "CRITICAL"


class TestErrorResponseFormat:
    """Test the error response format and fields."""

    def test_all_fields_present(self, client: TestClient) -> None:
        """Test that all expected fields are present in error response."""
        response = client.get("/test/validation-error")

        data = response.json()

        # Required fields
        assert "error_code" in data
        assert "message" in data
        assert "timestamp" in data

        # Optional fields that should be present
        assert "details" in data
        assert "correlation_id" in data
        assert "severity" in data
        assert "service_info" in data

        # Service info structure
        service_info = data["service_info"]
        assert "name" in service_info
        assert "version" in service_info
        assert "environment" in service_info

    def test_timestamp_format(self, client: TestClient) -> None:
        """Test that timestamp is in ISO format with timezone."""
        response = client.get("/test/validation-error")

        data = response.json()
        timestamp = data["timestamp"]

        # Should be ISO format with timezone
        assert "T" in timestamp  # Date-time separator
        assert "+" in timestamp or "Z" in timestamp  # Timezone indicator

    def test_correlation_id_present(self, client: TestClient) -> None:
        """Test that correlation ID is included in error responses."""
        # Send request with correlation ID
        correlation_id = "test-correlation-123"
        response = client.get(
            "/test/validation-error",
            headers={"X-Correlation-ID": correlation_id},
        )

        data = response.json()
        assert data["correlation_id"] == correlation_id

    def test_error_response_model_validation(self) -> None:
        """Test that ErrorResponse model validates correctly."""
        # This ensures our error responses match the schema
        error = ErrorResponse(
            error_code="TEST_ERROR",
            message="Test message",
            details={"key": "value"},
            correlation_id="123",
            severity="HIGH",
        )

        # Should serialize without errors
        data = error.model_dump(mode="json")
        assert data["error_code"] == "TEST_ERROR"
        assert isinstance(data["timestamp"], str)


class TestSensitiveDataSanitization:
    """Test that sensitive data is sanitized in error responses."""

    def test_sensitive_context_sanitized(self, app_with_handlers: FastAPI) -> None:
        """Test that sensitive fields in context are sanitized."""

        @app_with_handlers.get("/test/sensitive-error")
        async def raise_sensitive_error() -> None:
            raise ValidationError(
                "Validation failed",
                context={
                    "username": "john.doe",
                    "password": "secret123",
                    "api_key": "sk-1234567890",
                    "token": "bearer-token",
                    "credit_card": "4111111111111111",
                    "safe_field": "visible_value",
                },
            )

        client = TestClient(app_with_handlers)
        response = client.get("/test/sensitive-error")

        data = response.json()
        details = data["details"]

        # Sensitive fields should be redacted
        assert details["password"] == "[REDACTED]"
        assert details["api_key"] == "[REDACTED]"
        assert details["token"] == "[REDACTED]"
        assert details["credit_card"] == "[REDACTED]"

        # Non-sensitive fields should be preserved
        assert details["username"] == "john.doe"
        assert details["safe_field"] == "visible_value"


class TestDebugInfoInDevelopment:
    """Test that debug info is included in development mode."""

    def test_tributum_error_includes_debug_info(self, client: TestClient) -> None:
        """Test that TributumError includes debug info in development."""
        from src.core.config import get_settings

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
        from src.api.middleware.error_handler import generic_exception_handler

        test_exception = RuntimeError("Test error with context")
        response = await generic_exception_handler(request, test_exception)

        import json

        if isinstance(response.body, bytes):
            body_str = response.body.decode()
        else:
            body_str = str(response.body)
        data = json.loads(body_str)

        # Check based on environment
        from src.core.config import get_settings

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

    async def test_no_debug_info_in_production(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that debug info is NOT included in production."""
        # Set production environment
        monkeypatch.setenv("ENVIRONMENT", "production")

        from src.core.config import get_settings

        get_settings.cache_clear()

        # Test the handler directly in production mode
        from src.api.middleware.error_handler import generic_exception_handler

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

        import json

        if isinstance(response.body, bytes):
            body_str = response.body.decode()
        else:
            body_str = str(response.body)
        data = json.loads(body_str)

        # Should NOT have debug_info in production
        assert "debug_info" not in data or data["debug_info"] is None
