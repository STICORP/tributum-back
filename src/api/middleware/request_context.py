"""Request context middleware for correlation ID management."""

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
