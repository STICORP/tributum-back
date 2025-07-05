"""Shared fixtures and test endpoints for error handling tests."""

from collections.abc import AsyncGenerator

import pytest
from fastapi import FastAPI, HTTPException, status
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from pydantic import BaseModel, model_validator

from src.api.main import create_app
from src.core.exceptions import (
    BusinessRuleError,
    NotFoundError,
    UnauthorizedError,
    ValidationError,
)


def _add_tributum_error_endpoints(app: FastAPI) -> None:
    """Add Tributum-specific error test endpoints."""

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

    @app.get("/test/custom-severity")
    async def raise_custom_severity() -> None:
        raise ValidationError(
            "Critical validation failure",
            context={"severity_override": True},
        )

    @app.get("/test/error-with-cause")
    async def raise_error_with_cause() -> None:
        """Endpoint that raises an error with a cause."""
        try:
            # This will raise a ValueError
            int("not-a-number")
        except ValueError as e:
            # Raise a TributumError with the ValueError as cause
            raise ValidationError(
                "Failed to process input",
                context={"input": "not-a-number"},
                cause=e,  # Pass the cause explicitly to the constructor
            ) from e

    @app.get("/test/sensitive-context")
    async def raise_error_with_sensitive_context() -> None:
        """Endpoint that raises an error with sensitive data in context."""
        raise ValidationError(
            "Authentication failed",
            context={
                "password": "secret123",
                "api_key": "sk-12345-abcdef",
                "token": "jwt.token.here",
                "username": "john_doe",  # Not sensitive
                "error": "Invalid credentials",  # Not sensitive
            },
        )

    @app.get("/test/nested-sensitive-context")
    async def raise_error_with_nested_sensitive() -> None:
        """Endpoint that raises an error with nested sensitive data."""
        raise BusinessRuleError(
            "Payment processing failed",
            context={
                "user": {
                    "id": 123,
                    "email": "test@example.com",
                    "password": "hashed_password_here",
                    "api_key": "user_api_key_123",
                },
                "payment": {
                    "amount": 100.50,
                    "card_number": "4111111111111111",
                    "cvv": "123",
                    "currency": "USD",
                },
                "merchant": {"id": "merchant_123", "secret_key": "merchant_secret_key"},
            },
        )


def _add_http_exception_endpoints(app: FastAPI) -> None:
    """Add HTTP exception test endpoints."""

    @app.get("/test/http-exception")
    async def raise_http_exception() -> None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden",
        )

    @app.get("/test/http-400")
    async def raise_http_400() -> None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bad request data",
        )

    @app.get("/test/http-401")
    async def raise_http_401() -> None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    @app.get("/test/http-404")
    async def raise_http_404() -> None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resource not found",
        )

    @app.get("/test/http-500")
    async def raise_http_500() -> None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server error occurred",
        )

    @app.get("/test/http-503")
    async def raise_http_503() -> None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service temporarily unavailable",
        )


def _add_generic_error_endpoints(app: FastAPI) -> None:
    """Add generic error test endpoints."""

    @app.get("/test/generic-exception")
    async def raise_generic_exception() -> None:
        raise RuntimeError("Something went wrong")


def _add_validation_test_endpoints(app: FastAPI) -> None:
    """Add test endpoints for validation testing to the app."""

    class ValidationData(BaseModel):
        data: dict[str, int]

    @app.post("/test/request-validation")
    async def request_validation(body: ValidationData) -> dict[str, int]:
        """Endpoint that requires specific data structure."""
        return {"result": sum(body.data.values())}

    class RootValidationModel(BaseModel):
        value1: int
        value2: int

        @model_validator(mode="after")
        def check_sum(self) -> "RootValidationModel":
            if self.value1 + self.value2 > 100:
                raise ValueError("Sum must not exceed 100")
            return self

    @app.post("/test/root-validation")
    async def root_validation_endpoint(body: RootValidationModel) -> dict[str, int]:
        """Endpoint that has root-level validation."""
        return {"sum": body.value1 + body.value2}


@pytest.fixture
def app_with_handlers() -> FastAPI:
    """Create an app with exception handlers and test endpoints."""
    app = create_app()  # Exception handlers are already registered in create_app

    # Add test endpoints
    _add_tributum_error_endpoints(app)
    _add_http_exception_endpoints(app)
    _add_generic_error_endpoints(app)
    _add_validation_test_endpoints(app)

    return app


@pytest.fixture
def client(app_with_handlers: FastAPI) -> TestClient:
    """Create a test client (sync version for backward compatibility)."""
    return TestClient(app_with_handlers)


@pytest.fixture
async def async_client(app_with_handlers: FastAPI) -> AsyncGenerator[AsyncClient]:
    """Create an async test client with test endpoints."""
    transport = ASGITransport(app=app_with_handlers)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def async_client_production(production_env: None) -> AsyncGenerator[AsyncClient]:
    """Create an async test client with production settings and test endpoints."""
    _ = production_env  # Ensure production environment is set
    app = create_app()  # Create app with production settings

    # Add test endpoints
    _add_tributum_error_endpoints(app)
    _add_http_exception_endpoints(app)
    _add_generic_error_endpoints(app)
    _add_validation_test_endpoints(app)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
