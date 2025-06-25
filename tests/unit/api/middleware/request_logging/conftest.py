"""Shared fixtures and helpers for RequestLoggingMiddleware tests."""

from typing import Any

import pytest
from fastapi import FastAPI, File, Form, HTTPException, Request
from fastapi.testclient import TestClient
from pydantic import BaseModel

from src.api.middleware.request_context import RequestContextMiddleware
from src.api.middleware.request_logging import RequestLoggingMiddleware
from src.core.constants import MAX_BODY_SIZE


class UserModel(BaseModel):
    """Test model for request/response bodies."""

    username: str
    password: str
    email: str | None = None


def _add_basic_endpoints(app: FastAPI) -> None:
    """Add basic test endpoints to the app."""

    @app.get("/test")
    async def test_endpoint() -> dict[str, str]:
        """Test endpoint that returns success."""
        return {"status": "ok"}

    @app.get("/test-with-params")
    async def test_params_endpoint(name: str, age: int) -> dict[str, Any]:
        """Test endpoint with query parameters."""
        return {"name": name, "age": age}


def _add_error_endpoints(app: FastAPI) -> None:
    """Add error test endpoints to the app."""

    @app.get("/error")
    async def error_endpoint() -> None:
        """Test endpoint that raises an error."""
        raise HTTPException(status_code=500, detail="Test error")

    @app.get("/unhandled-error")
    async def unhandled_error_endpoint() -> None:
        """Test endpoint that raises an unhandled exception."""
        raise ValueError("This is an unhandled error")


def _add_auth_endpoints(app: FastAPI) -> None:
    """Add authentication test endpoints to the app."""

    @app.post("/auth/login")
    async def login_endpoint() -> dict[str, str]:
        """Sensitive endpoint for testing sanitization."""
        return {"token": "secret-token"}

    @app.get("/api/v1/auth/token")
    async def token_endpoint() -> dict[str, str]:
        """Another sensitive endpoint."""
        return {"token": "another-secret"}


def _add_body_endpoints(app: FastAPI) -> None:
    """Add body handling test endpoints to the app."""

    @app.post("/json-endpoint")
    async def json_endpoint(user: UserModel) -> dict[str, Any]:
        """Test endpoint that accepts JSON body."""
        return {"received": user.model_dump()}

    @app.post("/form-endpoint")
    async def form_endpoint(
        username: str = Form(), password: str = Form(), age: int = Form()
    ) -> dict[str, Any]:
        """Test endpoint that accepts form data."""
        # Password is intentionally not returned to test sanitization
        _ = password  # Mark as intentionally unused
        return {"username": username, "age": age}

    @app.post("/raw-text")
    async def raw_text_endpoint(request: Request) -> dict[str, str]:
        """Test endpoint that accepts raw text."""
        body = await request.body()
        return {"received": body.decode("utf-8")}

    @app.post("/binary-upload")
    async def binary_upload_endpoint(file: bytes = File()) -> dict[str, int]:
        """Test endpoint that accepts binary file."""
        return {"size": len(file)}

    @app.post("/echo", response_model=UserModel)
    async def echo_endpoint(user: UserModel) -> UserModel:
        """Test endpoint that echoes back the input."""
        return user


def create_test_app(
    add_logging_middleware: bool = True,
    log_request_body: bool = False,
    log_response_body: bool = False,
    max_body_size: int = MAX_BODY_SIZE,
) -> FastAPI:
    """Create a test FastAPI app."""
    test_app = FastAPI()
    # Note: Middleware is executed in reverse order in FastAPI/Starlette
    # So we add RequestLoggingMiddleware first, then RequestContextMiddleware
    if add_logging_middleware:
        test_app.add_middleware(
            RequestLoggingMiddleware,
            log_request_body=log_request_body,
            log_response_body=log_response_body,
            max_body_size=max_body_size,
        )
    test_app.add_middleware(RequestContextMiddleware)

    # Add all test endpoints
    _add_basic_endpoints(test_app)
    _add_error_endpoints(test_app)
    _add_auth_endpoints(test_app)
    _add_body_endpoints(test_app)

    return test_app


@pytest.fixture
def app() -> FastAPI:
    """Create a test FastAPI app with RequestLoggingMiddleware."""
    return create_test_app()


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Create a test client for the app."""
    return TestClient(app)
