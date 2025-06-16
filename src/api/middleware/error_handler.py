"""Global exception handlers for the FastAPI application.

This module provides centralized exception handling for all API endpoints,
ensuring consistent error responses and proper logging of exceptions.
"""

from typing import Any

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import Response
from starlette.exceptions import HTTPException

from src.api.schemas.errors import ErrorResponse, ServiceInfo
from src.api.utils.responses import ORJSONResponse
from src.core.config import Settings, get_settings
from src.core.context import RequestContext
from src.core.error_context import sanitize_context
from src.core.exceptions import (
    BusinessRuleError,
    ErrorCode,
    NotFoundError,
    TributumError,
    UnauthorizedError,
    ValidationError,
)
from src.core.logging import get_logger, log_exception

logger = get_logger(__name__)


def get_service_info(settings: Settings) -> ServiceInfo:
    """Create ServiceInfo from application settings.

    Args:
        settings: Application settings

    Returns:
        ServiceInfo instance with current service metadata
    """
    return ServiceInfo(
        name=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
    )


async def tributum_error_handler(request: Request, exc: TributumError) -> Response:
    """Handle TributumError exceptions.

    Converts TributumError instances to ErrorResponse with full context,
    ensuring sensitive data is sanitized before sending to client.

    Args:
        request: The FastAPI request that caused the exception
        exc: The TributumError exception to handle

    Returns:
        ORJSONResponse with error details
    """
    settings = get_settings()
    correlation_id = RequestContext.get_correlation_id()

    # Log the exception with full context
    log_exception(
        logger,
        exc,
        f"Handling {type(exc).__name__}",
        request_method=request.method,
        request_path=str(request.url.path),
        query_params=sanitize_context(dict(request.query_params)),
    )

    # Map exception types to HTTP status codes
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    if isinstance(exc, ValidationError):
        status_code = status.HTTP_400_BAD_REQUEST
    elif isinstance(exc, NotFoundError):
        status_code = status.HTTP_404_NOT_FOUND
    elif isinstance(exc, UnauthorizedError):
        status_code = status.HTTP_401_UNAUTHORIZED
    elif isinstance(exc, BusinessRuleError):
        status_code = status.HTTP_422_UNPROCESSABLE_ENTITY

    # Prepare error details (sanitized)
    details = None
    if exc.context:
        details = sanitize_context(exc.context)

    # Create error response
    error_response = ErrorResponse(
        error_code=exc.error_code,
        message=exc.message,
        details=details,
        correlation_id=correlation_id,
        severity=exc.severity.value,
        service_info=get_service_info(settings),
    )

    return ORJSONResponse(
        status_code=status_code,
        content=error_response.model_dump(mode="json"),
    )


async def validation_error_handler(
    request: Request, exc: RequestValidationError
) -> Response:
    """Handle FastAPI RequestValidationError exceptions.

    Converts validation errors to ErrorResponse with field-level details,
    making it easier for clients to understand what went wrong.

    Args:
        request: The FastAPI request that caused the exception
        exc: The RequestValidationError exception to handle

    Returns:
        ORJSONResponse with validation error details
    """
    settings = get_settings()
    correlation_id = RequestContext.get_correlation_id()

    # Extract field-level validation errors
    field_errors: dict[str, list[str]] = {}
    for error in exc.errors():
        # Get the field path (e.g., ['body', 'email'] -> 'email')
        field_path = error.get("loc", ())
        field_name = ".".join(str(loc) for loc in field_path[1:] if loc != "__root__")
        if not field_name:
            field_name = "root"

        # Get the error message
        error_msg = error.get("msg", "Invalid value")

        # Group errors by field
        if field_name not in field_errors:
            field_errors[field_name] = []
        field_errors[field_name].append(error_msg)

    # Log the validation error
    logger.warning(
        "Request validation failed",
        request_method=request.method,
        request_path=str(request.url.path),
        validation_errors=field_errors,
        correlation_id=correlation_id,
    )

    # Create error response
    error_response = ErrorResponse(
        error_code=ErrorCode.VALIDATION_ERROR.value,
        message="Request validation failed",
        details={"validation_errors": field_errors},
        correlation_id=correlation_id,
        severity="LOW",
        service_info=get_service_info(settings),
    )

    return ORJSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error_response.model_dump(mode="json"),
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> Response:
    """Handle Starlette HTTPException.

    Converts HTTPException to our standard ErrorResponse format.

    Args:
        request: The FastAPI request that caused the exception
        exc: The HTTPException to handle

    Returns:
        ORJSONResponse with error details
    """
    settings = get_settings()
    correlation_id = RequestContext.get_correlation_id()

    # Map status codes to error codes
    error_code = ErrorCode.INTERNAL_ERROR.value
    severity = "MEDIUM"

    if exc.status_code == status.HTTP_400_BAD_REQUEST:
        error_code = ErrorCode.VALIDATION_ERROR.value
        severity = "LOW"
    elif exc.status_code == status.HTTP_401_UNAUTHORIZED:
        error_code = ErrorCode.UNAUTHORIZED.value
        severity = "HIGH"
    elif exc.status_code == status.HTTP_404_NOT_FOUND:
        error_code = ErrorCode.NOT_FOUND.value
        severity = "LOW"
    elif exc.status_code >= 500:
        severity = "HIGH"

    # Log the exception
    logger.warning(
        f"HTTP exception: {exc.status_code}",
        request_method=request.method,
        request_path=str(request.url.path),
        status_code=exc.status_code,
        detail=exc.detail,
        correlation_id=correlation_id,
    )

    # Create error response
    error_response = ErrorResponse(
        error_code=error_code,
        message=str(exc.detail),
        correlation_id=correlation_id,
        severity=severity,
        service_info=get_service_info(settings),
    )

    return ORJSONResponse(
        status_code=exc.status_code,
        content=error_response.model_dump(mode="json"),
    )


async def generic_exception_handler(request: Request, exc: Exception) -> Response:
    """Handle generic exceptions.

    Catches all unhandled exceptions and converts them to a safe error response.
    In production, hides internal error details from clients.

    Args:
        request: The FastAPI request that caused the exception
        exc: The unhandled exception

    Returns:
        ORJSONResponse with generic error message
    """
    settings = get_settings()
    correlation_id = RequestContext.get_correlation_id()

    # Log the full exception with stack trace
    log_exception(
        logger,
        exc,
        "Unhandled exception",
        request_method=request.method,
        request_path=str(request.url.path),
        query_params=sanitize_context(dict(request.query_params)),
    )

    # In production, hide internal error details
    if settings.environment == "production":
        message = "An internal server error occurred"
        details = None
    else:
        message = f"Internal server error: {type(exc).__name__}"
        details = {"error": str(exc), "type": type(exc).__name__}

    # Create error response
    error_response = ErrorResponse(
        error_code=ErrorCode.INTERNAL_ERROR.value,
        message=message,
        details=details,
        correlation_id=correlation_id,
        severity="CRITICAL",
        service_info=get_service_info(settings),
    )

    return ORJSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response.model_dump(mode="json"),
    )


def register_exception_handlers(app: Any) -> None:
    """Register all exception handlers with the FastAPI application.

    This function should be called during application initialization to
    set up global exception handling.

    Args:
        app: The FastAPI application instance
    """
    # Register handlers for specific exception types
    app.add_exception_handler(TributumError, tributum_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)

    logger.info("Exception handlers registered")
