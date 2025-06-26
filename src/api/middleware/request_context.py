"""Request context middleware for correlation ID management."""

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from src.api.constants import CORRELATION_ID_HEADER
from src.core.context import RequestContext, generate_correlation_id


class RequestContextMiddleware:
    """Middleware to manage request context and correlation IDs.

    This middleware:
    1. Extracts correlation ID from incoming request headers
    2. Generates a new correlation ID if none exists
    3. Sets the correlation ID in the request context
    4. Adds the correlation ID to response headers
    5. Clears the context after request completion

    This uses pure ASGI middleware to avoid issues with BaseHTTPMiddleware
    exception handling.

    Args:
        app: The ASGI application to wrap.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Process the ASGI request.

        Args:
            scope: The ASGI connection scope.
            receive: The ASGI receive callable.
            send: The ASGI send callable.

        Raises:
            Exception: Re-raises any exception that occurs during request processing.
        """
        if scope["type"] != "http":
            # Only handle HTTP requests
            await self.app(scope, receive, send)
            return

        # Extract headers from scope
        headers = dict(scope.get("headers", []))
        correlation_id_bytes = headers.get(CORRELATION_ID_HEADER.lower().encode())

        # Get or generate correlation ID
        if correlation_id_bytes:
            correlation_id = correlation_id_bytes.decode("latin-1")
        else:
            correlation_id = generate_correlation_id()

        # Set correlation ID in context
        RequestContext.set_correlation_id(correlation_id)

        # Flag to track if headers have been sent
        headers_sent = False

        async def send_wrapper(message: Message) -> None:
            """Wrap the send callable to add correlation ID header.

            Args:
                message: The ASGI message to send.
            """
            nonlocal headers_sent

            if message["type"] == "http.response.start" and not headers_sent:
                headers_sent = True
                # Add correlation ID to response headers
                response_headers = list(message.get("headers", []))
                response_headers.append(
                    (
                        CORRELATION_ID_HEADER.lower().encode(),
                        correlation_id.encode("latin-1"),
                    )
                )
                message["headers"] = response_headers

            await send(message)

        try:
            # Process the request
            await self.app(scope, receive, send_wrapper)
        except Exception:
            # Clear context but re-raise the exception
            RequestContext.clear()
            raise
        finally:
            # Ensure context is cleared even if no exception
            RequestContext.clear()
