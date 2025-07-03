"""Request context middleware for distributed tracing and correlation.

This module implements middleware that manages request correlation IDs,
enabling distributed tracing across service boundaries and consistent
log correlation throughout the request lifecycle.

Key features:
- **Correlation ID propagation**: Extracts or generates unique IDs per request
- **Context variables**: Uses Python contextvars for thread-safe propagation
- **Loguru integration**: Automatically binds correlation IDs to all logs
- **Response headers**: Includes correlation ID in responses for client tracing

The correlation ID follows the request through all layers of the application,
making it easier to trace issues across logs, metrics, and distributed systems.
"""

import uuid

from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from src.core.context import RequestContext

CORRELATION_ID_HEADER = "X-Correlation-ID"


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Middleware to manage request context and correlation IDs.

    This middleware:
    - Generates or extracts correlation IDs
    - Sets them in contextvars for propagation
    - Binds them to Loguru for structured logging
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Process the request with context management.

        Args:
            request: The incoming request.
            call_next: The next middleware/endpoint.

        Returns:
            Response: Response with correlation ID header.
        """
        # Extract or generate correlation ID
        correlation_id = request.headers.get(CORRELATION_ID_HEADER) or str(uuid.uuid4())

        # Set in contextvars
        RequestContext.set_correlation_id(correlation_id)

        # IMPORTANT: Use contextualize for request-scoped data
        # This ensures the correlation ID is automatically cleaned up
        with logger.contextualize(correlation_id=correlation_id):
            # Process the request
            response = await call_next(request)

            # Add correlation ID to response headers
            response.headers[CORRELATION_ID_HEADER] = correlation_id

            return response
