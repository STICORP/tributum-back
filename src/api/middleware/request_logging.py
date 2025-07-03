"""HTTP request/response logging with performance monitoring.

This module implements comprehensive request logging middleware that captures
detailed information about every HTTP transaction for observability and debugging.

Features:
- **Structured logging**: JSON-formatted logs with consistent fields
- **Performance tracking**: Request duration and slow request detection
- **Client identification**: IP extraction with proxy header support
- **Request/response metrics**: Size tracking for bandwidth monitoring
- **Exclusion patterns**: Configurable path exclusion (e.g., health checks)
- **Error handling**: Logs failures while preserving exception propagation

The middleware integrates with the correlation ID system to ensure all logs
for a single request can be easily aggregated and analyzed.
"""

import time
import uuid
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from src.core.config import LogConfig, get_settings


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
        self.settings = get_settings()

    def _get_client_ip(self, request: Request) -> str:
        """Extract real client IP considering proxy headers.

        Args:
            request: The incoming request.

        Returns:
            str: The client IP address.
        """
        # Only trust proxy headers in production environments
        if self.settings.environment == "production":
            # Try X-Forwarded-For first (standard proxy header)
            forwarded_for = request.headers.get("x-forwarded-for")
            if forwarded_for:
                # Take the first IP (original client)
                ips = forwarded_for.split(",")
                return ips[0].strip()

            # Try X-Real-IP (nginx)
            real_ip = request.headers.get("x-real-ip")
            if real_ip:
                return real_ip.strip()

        # Fall back to direct connection
        if request.client:
            return request.client.host
        return "unknown"

    def _get_user_agent(self, request: Request) -> str:
        """Extract and sanitize user agent.

        Args:
            request: The incoming request.

        Returns:
            str: The user agent string, truncated if necessary.
        """
        ua = request.headers.get("user-agent", "")
        # Truncate extremely long user agents to prevent log pollution
        return ua[:200] if ua else "unknown"

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

        # Extract request metadata
        client_ip = self._get_client_ip(request)
        user_agent = self._get_user_agent(request)
        request_size = int(request.headers.get("content-length", 0))

        # Bind request context for this request
        with logger.contextualize(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            client_host=client_ip,
            user_agent=user_agent,
            request_size=request_size,
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

                # Try to get response size
                response_size = 0
                if "content-length" in response.headers:
                    response_size = int(response.headers["content-length"])

                # Log completion with metrics
                logger.info(
                    "Request completed",
                    status_code=response.status_code,
                    duration_ms=round(duration_ms, 2),
                    response_size=response_size,
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
