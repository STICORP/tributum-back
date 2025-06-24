"""Security headers middleware for adding common security headers to responses."""

from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from src.core.constants import DEFAULT_HSTS_MAX_AGE


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers to all responses.

    This middleware adds the following security headers:
    - X-Content-Type-Options: nosniff - Prevents MIME type sniffing
    - X-Frame-Options: DENY - Prevents clickjacking attacks
    - X-XSS-Protection: 1; mode=block - Enables XSS filtering in older browsers
    - Strict-Transport-Security: max-age=31536000; includeSubDomains (if HSTS enabled)

    Args:
        app: The ASGI application to wrap.
        hsts_enabled: Whether to include HSTS header (defaults to True).
        hsts_max_age: Max age for HSTS in seconds (defaults to 1 year).
        hsts_include_subdomains: Whether to include subdomains in HSTS.
        hsts_preload: Whether to include preload directive.
    """

    def __init__(
        self,
        app: ASGIApp,
        *,
        hsts_enabled: bool = True,
        hsts_max_age: int = DEFAULT_HSTS_MAX_AGE,
        hsts_include_subdomains: bool = True,
        hsts_preload: bool = False,
    ) -> None:
        super().__init__(app)
        self.hsts_enabled = hsts_enabled
        self.hsts_max_age = hsts_max_age
        self.hsts_include_subdomains = hsts_include_subdomains
        self.hsts_preload = hsts_preload

    def _build_hsts_header(self) -> str:
        """Build the Strict-Transport-Security header value.

        Returns:
            str: The HSTS header value string.
        """
        parts = [f"max-age={self.hsts_max_age}"]

        if self.hsts_include_subdomains:
            parts.append("includeSubDomains")

        if self.hsts_preload:
            parts.append("preload")

        return "; ".join(parts)

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """Add security headers to the response.

        Args:
            request: The incoming HTTP request.
            call_next: The next middleware or route handler.

        Returns:
            Response: The HTTP response with security headers added.
        """
        # Process the request
        response = await call_next(request)

        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Add HSTS header if enabled
        if self.hsts_enabled:
            response.headers["Strict-Transport-Security"] = self._build_hsts_header()

        return response
