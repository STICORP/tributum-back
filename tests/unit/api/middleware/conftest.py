"""Fixtures for API middleware error handler tests."""

from typing import Any, cast

import pytest
from fastapi import HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from pytest_mock import MockerFixture, MockType
from starlette.datastructures import URL
from starlette.middleware.base import RequestResponseEndpoint
from starlette.requests import Request as StarletteRequest
from starlette.responses import Response as StarletteResponse

from src.api.middleware.request_context import RequestContextMiddleware
from src.core.config import Settings
from src.core.exceptions import (
    BusinessRuleError,
    ErrorCode,
    NotFoundError,
    Severity,
    TributumError,
    UnauthorizedError,
    ValidationError,
)


@pytest.fixture
def mock_request(mocker: MockerFixture) -> MockType:
    """Create mock FastAPI Request with configurable attributes.

    Returns:
        MockType: Mock request object with standard HTTP request attributes.
    """
    request = mocker.Mock(spec=Request)
    request.method = "GET"
    request.url = mocker.Mock(spec=URL)
    request.url.path = "/api/test"
    request.url.query = ""
    request.url.scheme = "http"
    request.url.hostname = "localhost"
    request.url.port = 8000
    request.headers = {"user-agent": "test-client/1.0"}
    request.client = mocker.Mock()
    request.client.host = "127.0.0.1"
    request.client.port = 50000

    return cast("MockType", request)


@pytest.fixture
def mock_starlette_request(mocker: MockerFixture) -> MockType:
    """Create mock Starlette Request with configurable headers.

    Args:
        mocker: Pytest mocker fixture.

    Returns:
        MockType: Mock request object.
    """
    request = mocker.Mock(spec=StarletteRequest)
    request.headers = {}
    return cast("MockType", request)


@pytest.fixture
def mock_starlette_response(mocker: MockerFixture) -> MockType:
    """Create mock Starlette Response.

    Args:
        mocker: Pytest mocker fixture.

    Returns:
        MockType: Mock response object.
    """
    response = mocker.Mock(spec=StarletteResponse)
    response.headers = {}
    return cast("MockType", response)


@pytest.fixture
def mock_starlette_call_next(
    mocker: MockerFixture, mock_starlette_response: MockType
) -> MockType:
    """Create mock RequestResponseEndpoint callable.

    Args:
        mocker: Pytest mocker fixture.
        mock_starlette_response: Mock response fixture.

    Returns:
        MockType: Mock call_next function.
    """
    call_next = mocker.AsyncMock(spec=RequestResponseEndpoint)
    call_next.return_value = mock_starlette_response
    return cast("MockType", call_next)


@pytest.fixture
def request_context_middleware(mocker: MockerFixture) -> RequestContextMiddleware:
    """Create RequestContextMiddleware instance.

    Args:
        mocker: Pytest mocker fixture.

    Returns:
        RequestContextMiddleware: New middleware instance.
    """
    # BaseHTTPMiddleware requires an app parameter
    mock_app = mocker.Mock()
    return RequestContextMiddleware(mock_app)


@pytest.fixture
def mock_tributum_errors() -> dict[str, TributumError]:
    """Provide various TributumError instances for testing.

    Returns:
        dict[str, TributumError]: Dictionary of error types with test instances.
    """
    return {
        "basic": TributumError(
            error_code=ErrorCode.INTERNAL_ERROR,
            message="Test error message",
            severity=Severity.MEDIUM,
            context={"test_key": "test_value"},
        ),
        "validation": ValidationError(
            message="Invalid input data",
            context={"field": "email", "value": "invalid-email"},
        ),
        "not_found": NotFoundError(
            message="Resource not found",
            context={"resource_id": "123", "resource_type": "user"},
        ),
        "unauthorized": UnauthorizedError(
            message="Invalid credentials",
            context={"user_id": "456", "attempted_action": "delete"},
        ),
        "business_rule": BusinessRuleError(
            message="Business rule violation",
            context={"rule": "max_items_exceeded", "limit": 100},
        ),
        "with_cause": TributumError(
            error_code=ErrorCode.INTERNAL_ERROR,
            message="Error with cause",
            severity=Severity.HIGH,
            context={"operation": "database_query"},
            cause=ValueError("Original database error"),
        ),
        "critical": TributumError(
            error_code="CRITICAL_ERROR",
            message="Critical system failure",
            severity=Severity.CRITICAL,
            context={"system": "payment_processor", "error_code": "PX500"},
        ),
        "with_sensitive_data": TributumError(
            error_code=ErrorCode.INTERNAL_ERROR,
            message="Error with sensitive context",
            severity=Severity.MEDIUM,
            context={
                "username": "john_doe",
                "password": "secret123",
                "api_key": "sk-1234567890",
                "credit_card": "4111111111111111",
                "normal_field": "visible_value",
            },
        ),
    }


@pytest.fixture
def mock_validation_errors() -> dict[str, RequestValidationError]:
    """Create RequestValidationError instances with various patterns.

    Returns:
        dict[str, RequestValidationError]: Dictionary of validation error patterns.
    """
    # Create Pydantic validation errors to wrap
    single_error = [
        {
            "loc": ("body", "email"),
            "msg": "value is not a valid email address",
            "type": "value_error.email",
        }
    ]

    multiple_errors = [
        {
            "loc": ("body", "email"),
            "msg": "value is not a valid email address",
            "type": "value_error.email",
        },
        {
            "loc": ("body", "age"),
            "msg": "ensure this value is greater than 0",
            "type": "value_error.number.not_gt",
        },
        {
            "loc": ("body", "name"),
            "msg": "field required",
            "type": "value_error.missing",
        },
    ]

    nested_errors = [
        {
            "loc": ("body", "address", "street"),
            "msg": "field required",
            "type": "value_error.missing",
        },
        {
            "loc": ("body", "address", "city"),
            "msg": "field required",
            "type": "value_error.missing",
        },
        {
            "loc": ("body", "address", "zip_code"),
            "msg": "value is not a valid integer",
            "type": "type_error.integer",
        },
    ]

    root_error = [
        {
            "loc": ("__root__",),
            "msg": "passwords do not match",
            "type": "value_error",
        }
    ]

    multiple_same_field = [
        {
            "loc": ("body", "password"),
            "msg": "ensure this value has at least 8 characters",
            "type": "value_error.any_str.min_length",
        },
        {
            "loc": ("body", "password"),
            "msg": "password must contain at least one uppercase letter",
            "type": "value_error",
        },
        {
            "loc": ("body", "password"),
            "msg": "password must contain at least one number",
            "type": "value_error",
        },
    ]

    return {
        "single": RequestValidationError(single_error),
        "multiple": RequestValidationError(multiple_errors),
        "nested": RequestValidationError(nested_errors),
        "root": RequestValidationError(root_error),
        "same_field": RequestValidationError(multiple_same_field),
        "empty": RequestValidationError([]),
    }


@pytest.fixture
def mock_http_exceptions() -> dict[str, HTTPException]:
    """Provide HTTPException instances with different status codes.

    Returns:
        dict[str, HTTPException]: Dictionary of HTTP exceptions by status.
    """
    return {
        "400": HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Bad request"
        ),
        "401": HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized access"
        ),
        "403": HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden resource"
        ),
        "404": HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found"
        ),
        "422": HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Unprocessable entity",
        ),
        "500": HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        ),
        "503": HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service temporarily unavailable",
        ),
    }


@pytest.fixture
def mock_generic_exceptions() -> dict[str, Exception]:
    """Create various generic exception types for testing.

    Returns:
        dict[str, Exception]: Dictionary of exception instances.
    """
    return {
        "value_error": ValueError("Invalid value provided"),
        "key_error": KeyError("missing_key"),
        "type_error": TypeError("Expected str, got int"),
        "runtime_error": RuntimeError("Runtime failure occurred"),
        "attribute_error": AttributeError("'NoneType' object has no attribute 'foo'"),
        "zero_division": ZeroDivisionError("division by zero"),
        "index_error": IndexError("list index out of range"),
        "custom": type("CustomError", (Exception,), {})("Custom error message"),
        "with_args": Exception("Error message", {"code": 123}, ["item1", "item2"]),
        "empty_message": ValueError(""),
        "none_message": Exception(None),
    }


@pytest.fixture
def mock_error_response(mocker: MockerFixture) -> MockType:
    """Mock ErrorResponse class to capture initialization parameters.

    Returns:
        MockType: Mock ErrorResponse class.
    """
    mock_instance = mocker.Mock()
    mock_instance.model_dump = mocker.Mock(
        return_value={
            "error_code": "TEST_ERROR",
            "message": "Test message",
            "correlation_id": "test-correlation-id",
        }
    )

    mock_class = mocker.patch("src.api.middleware.error_handler.ErrorResponse")
    mock_class.return_value = mock_instance

    return mock_class


@pytest.fixture
def mock_orjson_response(mocker: MockerFixture) -> MockType:
    """Mock ORJSONResponse to capture response parameters.

    Returns:
        MockType: Mock ORJSONResponse class.
    """
    mock_instance = mocker.Mock()
    mock_instance.status_code = None
    mock_instance.content = None

    def init_side_effect(
        *,
        status_code: int | None = None,
        content: dict[str, Any] | None = None,
        **_kwargs: object,
    ) -> MockType:
        mock_instance.status_code = status_code
        mock_instance.content = content
        return cast("MockType", mock_instance)

    mock_class = mocker.patch("src.api.middleware.error_handler.ORJSONResponse")
    mock_class.side_effect = init_side_effect
    mock_class.instance = mock_instance  # Store instance for easy access

    return mock_class


@pytest.fixture
def mock_error_handler_dependencies(
    mocker: MockerFixture,
    mock_settings: Settings,
) -> dict[str, MockType]:
    """Mock all common dependencies for error handlers.

    Returns:
        dict[str, MockType]: Dictionary of mocked dependencies.
    """

    def mock_sanitize_error_context(
        _exc: Exception, ctx: dict[str, Any]
    ) -> dict[str, Any]:
        """Mock sanitize_error_context function."""
        return {"sanitized": True, **ctx}

    def mock_sanitize_dict(d: dict[str, Any] | None) -> dict[str, Any]:
        """Mock sanitize_dict function."""
        return {k: "[REDACTED]" if "password" in k else v for k, v in (d or {}).items()}

    mocks = {
        "get_settings": mocker.patch(
            "src.api.middleware.error_handler.get_settings",
            return_value=mock_settings,
        ),
        "get_correlation_id": mocker.patch(
            "src.api.middleware.error_handler.RequestContext.get_correlation_id",
            return_value="test-correlation-123",
        ),
        "generate_request_id": mocker.patch(
            "src.api.middleware.error_handler.generate_request_id",
            return_value="req-test-456",
        ),
        "sanitize_error_context": mocker.patch(
            "src.api.middleware.error_handler.sanitize_error_context",
            side_effect=mock_sanitize_error_context,
        ),
        "sanitize_dict": mocker.patch(
            "src.api.middleware.error_handler.sanitize_dict",
            side_effect=mock_sanitize_dict,
        ),
        "logger": mocker.patch("src.api.middleware.error_handler.logger"),
    }

    # Mock trace module
    mock_span = mocker.Mock()
    mock_span.is_recording.return_value = True
    mock_span.set_status = mocker.Mock()
    mock_span.set_attribute = mocker.Mock()

    mocks["get_current_span"] = mocker.patch(
        "src.api.middleware.error_handler.trace.get_current_span",
        return_value=mock_span,
    )
    mocks["span"] = mock_span

    # Mock Status and StatusCode for OpenTelemetry
    mock_status = mocker.Mock()
    mocks["Status"] = mocker.patch(
        "src.api.middleware.error_handler.Status", return_value=mock_status
    )
    mocks["StatusCode"] = mocker.patch("src.api.middleware.error_handler.StatusCode")
    mocks["StatusCode"].ERROR = "ERROR"

    return mocks
