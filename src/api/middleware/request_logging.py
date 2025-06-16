"""Request logging middleware for logging HTTP requests and responses."""

import time
from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from src.core.context import RequestContext
from src.core.error_context import sanitize_context
from src.core.logging import get_logger


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging HTTP requests and responses.

    This middleware logs:
    - Request method, path, and correlation ID
    - Query parameters (sanitized for sensitive data)
    - Response status code and duration
    - Errors that occur during request processing

    Attributes:
        app: The ASGI application to wrap.
        logger: The structlog logger instance.
        log_request_body: Whether to log request body (default: False).
        log_response_body: Whether to log response body (default: False).
    """

    def __init__(
        self,
        app: ASGIApp,
        *,
        log_request_body: bool = False,
        log_response_body: bool = False,
    ) -> None:
        """Initialize the request logging middleware.

        Args:
            app: The ASGI application to wrap.
            log_request_body: Whether to log request body content.
            log_response_body: Whether to log response body content.
        """
        super().__init__(app)
        self.logger = get_logger(__name__)
        self.log_request_body = log_request_body
        self.log_response_body = log_response_body

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """Log the request and response details.

        Args:
            request: The incoming HTTP request.
            call_next: The next middleware or route handler.

        Returns:
            The HTTP response.
        """
        # Start timing the request
        start_time = time.time()

        # Get correlation ID from context
        correlation_id = RequestContext.get_correlation_id()

        # Extract request details
        method = request.method
        path = request.url.path
        query_params = dict(request.query_params)

        # Build log data
        log_data: dict[str, Any] = {
            "method": method,
            "path": path,
            "correlation_id": correlation_id,
        }

        # Add sanitized query params if present
        if query_params:
            # Sanitize query params to remove sensitive data
            sanitized_params = sanitize_context({"params": query_params})["params"]
            log_data["query_params"] = sanitized_params

        # Log request start
        self.logger.info("request_started", **log_data)

        try:
            # Process the request
            response = await call_next(request)

            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000

            # Log response
            self.logger.info(
                "request_completed",
                method=method,
                path=path,
                status_code=response.status_code,
                duration_ms=round(duration_ms, 2),
                correlation_id=correlation_id,
            )

            return response

        except Exception as exc:
            # Calculate duration even for errors
            duration_ms = (time.time() - start_time) * 1000

            # Log the error
            self.logger.error(
                "request_failed",
                method=method,
                path=path,
                duration_ms=round(duration_ms, 2),
                correlation_id=correlation_id,
                error_type=type(exc).__name__,
                exc_info=exc,
            )

            # Re-raise the exception to be handled by error handlers
            raise
