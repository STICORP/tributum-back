"""Request logging middleware for logging HTTP requests and responses."""

import json
import time
from collections.abc import Awaitable, Callable
from typing import Any
from urllib.parse import parse_qs

from fastapi import Request, Response
from starlette.datastructures import Headers
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from src.core.context import RequestContext
from src.core.error_context import sanitize_context
from src.core.logging import get_logger

# Constants for body logging
MAX_BODY_SIZE = 10 * 1024  # 10KB default limit for body logging
TRUNCATED_SUFFIX = "... [TRUNCATED]"

# Headers to exclude from logging for security
SENSITIVE_HEADERS = {
    "authorization",
    "cookie",
    "x-api-key",
    "x-auth-token",
    "x-csrf-token",
    "set-cookie",
}

# Content types that support body logging
JSON_CONTENT_TYPES = {"application/json", "text/json"}
FORM_CONTENT_TYPES = {"application/x-www-form-urlencoded", "multipart/form-data"}
TEXT_CONTENT_TYPES = {"text/plain", "text/html", "text/xml", "application/xml"}


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
        max_body_size: int = MAX_BODY_SIZE,
    ) -> None:
        """Initialize the request logging middleware.

        Args:
            app: The ASGI application to wrap.
            log_request_body: Whether to log request body content.
            log_response_body: Whether to log response body content.
            max_body_size: Maximum size of body to log (in bytes).
        """
        super().__init__(app)
        self.logger = get_logger(__name__)
        self.log_request_body = log_request_body
        self.log_response_body = log_response_body
        self.max_body_size = max_body_size

    @staticmethod
    def _sanitize_headers(headers: Headers) -> dict[str, str]:
        """Sanitize headers by removing sensitive values.

        Args:
            headers: The headers to sanitize.

        Returns:
            Dictionary of sanitized headers.
        """
        sanitized = {}
        for key, value in headers.items():
            if key.lower() in SENSITIVE_HEADERS:
                sanitized[key] = "[REDACTED]"
            else:
                sanitized[key] = value
        return sanitized

    @staticmethod
    def _get_content_type(headers: Headers) -> str:
        """Extract the content type from headers.

        Args:
            headers: The request/response headers.

        Returns:
            The content type without parameters (e.g., 'application/json').
        """
        content_type = headers.get("content-type", "")
        # Remove parameters like charset
        if ";" in content_type:
            content_type = content_type.split(";")[0].strip()
        return content_type.lower()

    def _truncate_body(self, body: str | bytes) -> str:
        """Truncate body if it exceeds max size.

        Args:
            body: The body content to truncate.

        Returns:
            Truncated body as string.
        """
        if isinstance(body, bytes):
            if len(body) <= self.max_body_size:
                try:
                    return body.decode("utf-8", errors="replace")
                except Exception:
                    return f"<binary data: {len(body)} bytes>"
            else:
                truncated = body[: self.max_body_size]
                try:
                    decoded = truncated.decode("utf-8", errors="replace")
                    return decoded + TRUNCATED_SUFFIX
                except Exception:
                    return f"<binary data: {len(body)} bytes>{TRUNCATED_SUFFIX}"
        else:
            if len(body) <= self.max_body_size:
                return body
            return body[: self.max_body_size] + TRUNCATED_SUFFIX

    async def _parse_request_body(self, request: Request) -> tuple[Any, bytes | None]:
        """Parse request body based on content type.

        Args:
            request: The incoming request.

        Returns:
            Tuple of (parsed_body, raw_body_bytes).
        """
        try:
            # Read the body once
            body_bytes = await request.body()
            if not body_bytes:
                return None, body_bytes

            content_type = RequestLoggingMiddleware._get_content_type(request.headers)

            # Parse JSON
            if content_type in JSON_CONTENT_TYPES:
                try:
                    parsed = json.loads(body_bytes)
                    return parsed, body_bytes
                except json.JSONDecodeError:
                    return self._truncate_body(body_bytes), body_bytes

            # Parse form data
            elif content_type == "application/x-www-form-urlencoded":
                try:
                    parsed = parse_qs(body_bytes.decode("utf-8"))
                    # Convert from list values to single values for logging
                    parsed = {k: v[0] if len(v) == 1 else v for k, v in parsed.items()}
                    return parsed, body_bytes
                except Exception:
                    return self._truncate_body(body_bytes), body_bytes

            # Multipart form data - just log metadata
            elif content_type == "multipart/form-data":
                return {
                    "_type": "multipart/form-data",
                    "_size": len(body_bytes),
                    "_info": "Binary content not logged",
                }, body_bytes

            # Text content
            elif content_type in TEXT_CONTENT_TYPES:
                return self._truncate_body(body_bytes), body_bytes

            # Binary or unknown content
            else:
                return {
                    "_type": content_type or "unknown",
                    "_size": len(body_bytes),
                    "_info": "Binary content not logged",
                }, body_bytes

        except Exception as e:
            self.logger.warning(
                "Failed to read request body",
                error=str(e),
                correlation_id=RequestContext.get_correlation_id(),
            )
            return None, None

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

        # Add request headers if body logging is enabled
        if self.log_request_body:
            log_data["headers"] = RequestLoggingMiddleware._sanitize_headers(
                request.headers
            )

        # Parse and log request body if enabled
        body_for_handler: bytes | None = None
        if self.log_request_body and method in {"POST", "PUT", "PATCH"}:
            parsed_body, body_bytes = await self._parse_request_body(request)
            if parsed_body is not None:
                # Sanitize the parsed body
                if isinstance(parsed_body, dict):
                    log_data["body"] = sanitize_context({"body": parsed_body})["body"]
                else:
                    log_data["body"] = parsed_body
            body_for_handler = body_bytes

        # If we read the body, we need to set it back for the handler
        if body_for_handler is not None:

            async def receive() -> dict[str, Any]:
                return {"type": "http.request", "body": body_for_handler}

            request._receive = receive

        # Log request start
        self.logger.info("request_started", **log_data)

        try:
            # Process the request
            response = await call_next(request)

            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000

            # Build response log data
            response_log_data: dict[str, Any] = {
                "method": method,
                "path": path,
                "status_code": response.status_code,
                "duration_ms": round(duration_ms, 2),
                "correlation_id": correlation_id,
            }

            # Log response body if enabled
            if self.log_response_body:
                # Add response headers
                response_log_data["response_headers"] = (
                    RequestLoggingMiddleware._sanitize_headers(response.headers)
                )

                # Capture response body for logging
                # We need to read the response body and create a new response
                body_bytes = b""

                # The response from middleware is always a streaming response
                # We need to consume the body_iterator
                if hasattr(response, "body_iterator"):
                    async for chunk in response.body_iterator:
                        if isinstance(chunk, bytes):
                            body_bytes += chunk
                        elif isinstance(chunk, str):
                            body_bytes += chunk.encode("utf-8")

                # Parse and log the response body
                content_type = RequestLoggingMiddleware._get_content_type(
                    response.headers
                )
                if body_bytes:
                    if content_type in JSON_CONTENT_TYPES:
                        try:
                            parsed = json.loads(body_bytes)
                            response_log_data["response_body"] = sanitize_context(
                                {"body": parsed}
                            )["body"]
                        except Exception:
                            response_log_data["response_body"] = self._truncate_body(
                                body_bytes
                            )
                    else:
                        response_log_data["response_body"] = self._truncate_body(
                            body_bytes
                        )

                # Create a new response with the same body
                from starlette.responses import Response as StarletteResponse

                response = StarletteResponse(
                    content=body_bytes,
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    media_type=response.media_type,
                )

            # Log response
            self.logger.info("request_completed", **response_log_data)

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
