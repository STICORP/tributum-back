"""Request logging middleware with performance tracking."""

import time
import uuid
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from src.core.config import LogConfig


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging HTTP requests and responses.

    This simplified middleware:
    - Logs request start/completion with timing
    - Tracks basic performance metrics
    - Excludes configured paths
    - Integrates with correlation IDs

    Args:
        app: The ASGI application.
        log_config: Logging configuration.
    """

    def __init__(self, app: ASGIApp, *, log_config: LogConfig) -> None:
        super().__init__(app)
        self.log_config = log_config
        self.excluded_paths = set(log_config.excluded_paths)

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """Process the request and log details.

        Args:
            request: The incoming request.
            call_next: The next middleware/endpoint.

        Returns:
            Response: The response from the application.

        Raises:
            Exception: Any exception raised by the application is re-raised
                after logging.
        """
        # Skip logging for excluded paths
        if request.url.path in self.excluded_paths:
            return await call_next(request)

        # Generate or extract request ID
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))

        # Bind request context for this request
        with logger.contextualize(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            client_host=request.client.host if request.client else None,
        ):
            # Log request start
            logger.info(
                "Request started",
                query_params=(
                    dict(request.query_params) if request.query_params else None
                ),
            )

            # Track timing
            start_time = time.perf_counter()

            try:
                # Process request
                response = await call_next(request)

            except Exception as exc:
                # Calculate duration even for errors
                duration_ms = (time.perf_counter() - start_time) * 1000

                # Log the error
                logger.error(
                    "Request failed",
                    duration_ms=round(duration_ms, 2),
                    error_type=type(exc).__name__,
                    error_message=str(exc),
                )

                # Re-raise the exception
                raise
            else:
                # Calculate duration
                duration_ms = (time.perf_counter() - start_time) * 1000

                # Log completion with metrics
                logger.info(
                    "Request completed",
                    status_code=response.status_code,
                    duration_ms=round(duration_ms, 2),
                )

                # Add request ID to response
                response.headers["X-Request-ID"] = request_id

                # Log slow requests
                if duration_ms > self.log_config.slow_request_threshold_ms:
                    logger.warning(
                        "Slow request detected",
                        duration_ms=round(duration_ms, 2),
                        threshold_ms=self.log_config.slow_request_threshold_ms,
                    )

                return response
