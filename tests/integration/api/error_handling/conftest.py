"""Shared fixtures and test endpoints for error handling tests."""

import pytest
from fastapi import FastAPI, HTTPException, status
from fastapi.testclient import TestClient
from pydantic import BaseModel

from src.api.main import create_app
from src.core.exceptions import (
    BusinessRuleError,
    NotFoundError,
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
