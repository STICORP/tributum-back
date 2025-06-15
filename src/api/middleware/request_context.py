"""Request context middleware for correlation ID management."""

from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from src.core.context import (
    CORRELATION_ID_HEADER,
    RequestContext,
    generate_correlation_id,
)


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Middleware to manage request context and correlation IDs.

    This middleware:
    1. Extracts correlation ID from incoming request headers
    2. Generates a new correlation ID if none exists
    3. Sets the correlation ID in the request context
    4. Adds the correlation ID to response headers
    5. Clears the context after request completion

    Attributes:
        app: The ASGI application to wrap.
    """

    def __init__(self, app: ASGIApp) -> None:
        """Initialize the middleware.

        Args:
            app: The ASGI application to wrap.
        """
        super().__init__(app)

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """Process the request and manage correlation ID context.

        Args:
            request: The incoming HTTP request.
            call_next: The next middleware or route handler.

        Returns:
            The HTTP response with correlation ID header added.
        """
        # Extract or generate correlation ID
        correlation_id = request.headers.get(CORRELATION_ID_HEADER)
        if not correlation_id:
            correlation_id = generate_correlation_id()

        # Set correlation ID in context
        RequestContext.set_correlation_id(correlation_id)

        try:
            # Process the request
            response = await call_next(request)

            # Add correlation ID to response headers
            response.headers[CORRELATION_ID_HEADER] = correlation_id

            return response
        finally:
            # Clear the context to prevent leakage
            RequestContext.clear()
