"""FastAPI middleware package for cross-cutting request/response concerns.

This package contains middleware components that handle common functionality
across all API endpoints:

- **SecurityHeadersMiddleware**: Adds security headers (HSTS, X-Frame-Options, etc.)
- **RequestContextMiddleware**: Manages correlation IDs and request context
- **RequestLoggingMiddleware**: Structured logging with performance tracking
- **ErrorHandler**: Centralized exception handling with consistent error responses

Middleware are executed in a specific order to ensure proper request processing:
1. Security headers (first to process, last to respond)
2. Request context (sets up correlation IDs)
3. Request logging (logs with correlation context)
4. Error handling (catches and formats all exceptions)
"""
