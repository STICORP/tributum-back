"""Request logging middleware for logging HTTP requests and responses."""

import json
import time
from collections.abc import Awaitable, Callable
from typing import Any
from urllib.parse import parse_qs

from fastapi import Request, Response
from starlette.datastructures import Headers
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response as StarletteResponse
from starlette.types import ASGIApp

from src.api.constants import (
    FORM_CONTENT_TYPES,
    JSON_CONTENT_TYPES,
    REQUEST_BODY_METHODS,
    SENSITIVE_HEADERS,
    TEXT_CONTENT_TYPES,
)
from src.core.config import LogConfig
from src.core.constants import MILLISECONDS_PER_SECOND, TRUNCATED_SUFFIX
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

    It uses the application's LogConfig for its settings.

    Args:
        app: The ASGI application to wrap.
        log_config: Logging configuration object.
    """

    def __init__(
        self,
        app: ASGIApp,
        *,
        log_config: LogConfig,
    ) -> None:
        super().__init__(app)
        self.logger = get_logger(__name__)
        self.log_config = log_config

    @property
    def max_body_size(self) -> int:
        """Return max body size from config."""
        return self.log_config.max_body_log_size

    @property
    def log_request_body(self) -> bool:
        """Return whether to log request body from config."""
        return self.log_config.log_request_body

    @property
    def log_response_body(self) -> bool:
        """Return whether to log response body from config."""
        return self.log_config.log_response_body

    @staticmethod
    def _sanitize_headers(headers: Headers) -> dict[str, str]:
        """Sanitize headers by removing sensitive values.

        Args:
            headers: The headers to sanitize.

        Returns:
            dict[str, str]: Dictionary of sanitized headers.
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
            str: The content type without parameters (e.g., 'application/json').
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
            str: Truncated body as string.
        """
        if isinstance(body, bytes):
            if len(body) <= self.max_body_size:
                try:
                    return body.decode("utf-8", errors="replace")
                except (UnicodeDecodeError, AttributeError):
                    return f"<binary data: {len(body)} bytes>"
            else:
                truncated = body[: self.max_body_size]
                try:
                    decoded = truncated.decode("utf-8", errors="replace")
                    return decoded + TRUNCATED_SUFFIX
                except (UnicodeDecodeError, AttributeError):
                    return f"<binary data: {len(body)} bytes>{TRUNCATED_SUFFIX}"
        else:
            if len(body) <= self.max_body_size:
                return body
            return body[: self.max_body_size] + TRUNCATED_SUFFIX

    def _parse_json_body(self, body_bytes: bytes) -> Any:  # noqa: ANN401 - returns JSON-compatible types
        """Parse JSON body content.

        Args:
            body_bytes: Raw bytes of the request body.

        Returns:
            Any: Parsed JSON object if valid, otherwise truncated string representation.
        """
        try:
            return json.loads(body_bytes)
        except json.JSONDecodeError:
            return self._truncate_body(body_bytes)

    def _parse_form_body(self, body_bytes: bytes) -> Any:  # noqa: ANN401 - returns form data as dict
        """Parse form-encoded body content.

        Args:
            body_bytes: Raw bytes of the form-encoded request body.

        Returns:
            Any: Dictionary with parsed form data if valid, otherwise truncated string.
            Single-value lists are unwrapped for cleaner logging.
        """
        try:
            parsed = parse_qs(body_bytes.decode("utf-8"))
            # Convert from list values to single values for logging
            return {k: v[0] if len(v) == 1 else v for k, v in parsed.items()}
        except (UnicodeDecodeError, ValueError):
            return self._truncate_body(body_bytes)

    def _get_body_metadata(
        self, body_bytes: bytes, content_type: str
    ) -> dict[str, Any]:
        """Get metadata for binary content.

        Args:
            body_bytes: Raw bytes of the binary content.
            content_type: Content-Type header value.

        Returns:
            dict[str, Any]: Dictionary containing metadata about the binary content,
            including type, size, and an info message.
        """
        return {
            "_type": content_type or "unknown",
            "_size": len(body_bytes),
            "_info": "Binary content not logged",
        }

    async def _parse_request_body(self, request: Request) -> tuple[Any, bytes | None]:
        """Parse request body based on content type.

        Args:
            request: The incoming request.

        Returns:
            tuple[Any, bytes | None]: Tuple of (parsed_body, raw_body_bytes).
        """
        try:
            # Read the body once
            body_bytes = await request.body()
            if not body_bytes:
                return None, body_bytes

            content_type = RequestLoggingMiddleware._get_content_type(request.headers)

            # Use a mapping to handle different content types
            if content_type in JSON_CONTENT_TYPES:
                parsed = self._parse_json_body(body_bytes)
            elif content_type in FORM_CONTENT_TYPES:
                if content_type == "application/x-www-form-urlencoded":
                    parsed = self._parse_form_body(body_bytes)
                else:  # multipart/form-data
                    parsed = self._get_body_metadata(body_bytes, content_type)
            elif content_type in TEXT_CONTENT_TYPES:
                parsed = self._truncate_body(body_bytes)
            else:
                parsed = self._get_body_metadata(body_bytes, content_type)

        except (ValueError, RuntimeError, json.JSONDecodeError) as e:
            self.logger.warning(
                "Failed to read request body",
                error=str(e),
                correlation_id=RequestContext.get_correlation_id(),
            )
            return None, None
        else:
            return parsed, body_bytes

    def _build_request_log_data(
        self,
        method: str,
        path: str,
        correlation_id: str | None,
        query_params: dict[str, Any],
        headers: Headers | None = None,
    ) -> dict[str, Any]:
        """Build log data structure for request logging.

        Args:
            method: HTTP method (GET, POST, etc.).
            path: Request URL path.
            correlation_id: Request correlation ID for tracing.
            query_params: Query parameters from the request.
            headers: Optional request headers for logging when body logging is enabled.

        Returns:
            dict[str, Any]: Dictionary containing structured log data with sanitized
                values.
        """
        log_data: dict[str, Any] = {
            "method": method,
            "path": path,
            "correlation_id": correlation_id,
        }

        # Add sanitized query params if present
        if query_params:
            sanitized_params = sanitize_context({"params": query_params})["params"]
            log_data["query_params"] = sanitized_params

        # Add request headers if body logging is enabled
        if self.log_request_body and headers:
            log_data["headers"] = RequestLoggingMiddleware._sanitize_headers(headers)

        return log_data

    async def _handle_request_body(
        self, request: Request, log_data: dict[str, Any]
    ) -> bytes | None:
        """Handle request body parsing and logging.

        Args:
            request: The incoming FastAPI request.
            log_data: Dictionary to populate with parsed body data.

        Returns:
            bytes | None: Raw body bytes if body was read, None otherwise.
            Side effect: Updates log_data with parsed and sanitized body content.
        """
        if not self.log_request_body or request.method not in REQUEST_BODY_METHODS:
            return None

        parsed_body, body_bytes = await self._parse_request_body(request)
        if parsed_body is not None:
            # Sanitize the parsed body
            if isinstance(parsed_body, dict):
                log_data["body"] = sanitize_context({"body": parsed_body})["body"]
            else:
                log_data["body"] = parsed_body

        return body_bytes

    async def _capture_response_body(self, response: Response) -> bytes:
        """Capture response body from streaming response.

        Args:
            response: The streaming response object.

        Returns:
            bytes: Concatenated bytes of the entire response body.
        """
        body_bytes = b""
        if hasattr(response, "body_iterator"):
            async for chunk in response.body_iterator:
                if isinstance(chunk, bytes):
                    body_bytes += chunk
                elif isinstance(chunk, str):
                    body_bytes += chunk.encode("utf-8")
        return body_bytes

    def _log_response_body(
        self, response_log_data: dict[str, Any], body_bytes: bytes, headers: Headers
    ) -> None:
        """Log response body if applicable.

        Args:
            response_log_data: Dictionary to update with response body data.
            body_bytes: Raw bytes of the response body.
            headers: Response headers to determine content type.

        Returns:
            None: Updates response_log_data in place with parsed or truncated body.
        """
        content_type = RequestLoggingMiddleware._get_content_type(headers)
        if not body_bytes:
            return

        if content_type in JSON_CONTENT_TYPES:
            try:
                parsed = json.loads(body_bytes)
            except (json.JSONDecodeError, ValueError, TypeError):
                response_log_data["response_body"] = self._truncate_body(body_bytes)
            else:
                response_log_data["response_body"] = sanitize_context({"body": parsed})[
                    "body"
                ]
        else:
            response_log_data["response_body"] = self._truncate_body(body_bytes)

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
            Response: The HTTP response.

        Raises:
            Exception: Re-raises any exception that occurs during request processing.
        """
        # Check if path is excluded from logging
        path = request.url.path
        if path in self.log_config.excluded_paths:
            # Still need to process the request
            return await call_next(request)

        # Start timing the request
        start_time = time.time()

        # Get correlation ID from context
        correlation_id = RequestContext.get_correlation_id()

        # Extract request details
        method = request.method
        path = request.url.path
        query_params = dict(request.query_params)

        # Build log data
        log_data = self._build_request_log_data(
            method, path, correlation_id, query_params, request.headers
        )

        # Handle request body
        body_for_handler = await self._handle_request_body(request, log_data)

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
            duration_ms = (time.time() - start_time) * MILLISECONDS_PER_SECOND

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
                response = await self._handle_response_logging(
                    response, response_log_data
                )

            # Log response
            self.logger.info("request_completed", **response_log_data)

        except Exception as exc:
            # Calculate duration even for errors
            duration_ms = (time.time() - start_time) * MILLISECONDS_PER_SECOND

            # Log the error
            self.logger.exception(
                "request_failed",
                method=method,
                path=path,
                duration_ms=round(duration_ms, 2),
                correlation_id=correlation_id,
                error_type=type(exc).__name__,
            )

            # Re-raise the exception to be handled by error handlers
            raise
        else:
            return response

    async def _handle_response_logging(
        self, response: Response, response_log_data: dict[str, Any]
    ) -> Response:
        """Handle response body logging and create new response.

        Args:
            response: The original streaming response.
            response_log_data: Dictionary to populate with response data.

        Returns:
            Response: New Response object with the captured body content, preserving
            original status code, headers, and media type.
        """
        # Add response headers
        response_log_data["response_headers"] = (
            RequestLoggingMiddleware._sanitize_headers(response.headers)
        )

        # Capture response body
        body_bytes = await self._capture_response_body(response)

        # Log the response body
        self._log_response_body(response_log_data, body_bytes, response.headers)

        # Create a new response with the same body
        return StarletteResponse(
            content=body_bytes,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.media_type,
        )
