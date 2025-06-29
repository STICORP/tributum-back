# Phase 2: Request Context and Middleware

## Overview
This phase integrates Loguru with the existing RequestContextMiddleware to ensure correlation IDs propagate correctly through async contexts. We'll also create a simplified RequestLoggingMiddleware that tracks basic request metrics.

## Prerequisites
- Phase 1 completed (Loguru basic setup)
- RequestContextMiddleware still intact from Phase 0

## Objectives
1. Update RequestContextMiddleware to propagate correlation IDs to Loguru
2. Create simplified RequestLoggingMiddleware (150 lines vs 855)
3. Ensure correlation IDs flow through async contexts
4. Add basic request duration tracking
5. Create tests for middleware integration

## Implementation

### Step 1: Verify Constants

Ensure `src/api/constants.py` still has:
```python
CORRELATION_ID_HEADER = "X-Correlation-ID"
```

This constant will be used throughout the middleware.

### Step 2: Update RequestContextMiddleware

Update `src/api/middleware/request_context.py`:
```python
"""Request context middleware for correlation ID management."""

import uuid
from typing import Any

from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from src.api.constants import CORRELATION_ID_HEADER
from src.core.context import RequestContext


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Middleware to manage request context and correlation IDs.

    This middleware:
    - Generates or extracts correlation IDs
    - Sets them in contextvars for propagation
    - Binds them to Loguru for structured logging
    """

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        """Process the request with context management.

        Args:
            request: The incoming request.
            call_next: The next middleware/endpoint.

        Returns:
            Response with correlation ID header.
        """
        # Extract or generate correlation ID
        correlation_id = request.headers.get(
            CORRELATION_ID_HEADER,
            str(uuid.uuid4())
        )

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
```

### Step 2: Create Simplified RequestLoggingMiddleware

Create `src/api/middleware/request_logging.py`:
```python
"""Request logging middleware with performance tracking."""

from __future__ import annotations

import time
import uuid
from typing import TYPE_CHECKING, Any, Final

from fastapi import Request, Response
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from src.core.context import RequestContext

if TYPE_CHECKING:
    from src.core.config import LogConfig

# Constants
EXCLUDED_HEADERS: Final[set[str]] = {"authorization", "cookie", "x-api-key"}
MAX_BODY_LOG_SIZE: Final[int] = 10240  # 10KB


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging HTTP requests and responses.

    This simplified middleware:
    - Logs request start/completion with timing
    - Tracks basic performance metrics
    - Excludes configured paths
    - Integrates with correlation IDs
    """

    def __init__(self, app: Any, log_config: LogConfig) -> None:
        """Initialize the middleware.

        Args:
            app: The ASGI application.
            log_config: Logging configuration.
        """
        super().__init__(app)
        self.log_config = log_config
        self.excluded_paths = set(log_config.excluded_paths)

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        """Process the request and log details.

        Args:
            request: The incoming request.
            call_next: The next middleware/endpoint.

        Returns:
            Response: The response from the application.
        """
        # Skip logging for excluded paths
        if request.url.path in self.excluded_paths:
            return await call_next(request)

        # Generate or extract request ID
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))

        # Get correlation ID from context
        correlation_id = RequestContext.get_correlation_id()

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
                query_params=dict(request.query_params) if request.query_params else None,
            )

            # Track timing
            start_time = time.perf_counter()

            try:
                # Process request
                response = await call_next(request)

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
```

### Step 3: Update Application Middleware Registration

Update `src/api/main.py` to register the new middleware:
```python
# In create_app function, after registering exception handlers:

# Register middleware in correct order (last added = first executed)
# 3. Request logging middleware (logs requests/responses)
application.add_middleware(
    RequestLoggingMiddleware,
    log_config=settings.log_config
)

# 2. Request context middleware (creates correlation ID)
application.add_middleware(RequestContextMiddleware)

# 1. Security headers middleware (adds security headers)
application.add_middleware(SecurityHeadersMiddleware)
```

### Important Note: contextualize() vs bind()

From the specification, it's critical to understand the difference:

**`logger.contextualize()`** - Returns a context manager for request-scoped data:
```python
with logger.contextualize(request_id="123"):
    # All logs within this context include request_id
    await process_request()
```

**`logger.bind()`** - Returns a new logger instance with bound values:
```python
user_logger = logger.bind(user_id=456)
user_logger.info("User action")  # Includes user_id
```

**Common Pitfall to Avoid**:
```python
# WRONG: This creates a new logger instance, doesn't affect global logger
logger = logger.bind(request_id="123")

# RIGHT: Use contextualize for request-scoped data
with logger.contextualize(request_id="123"):
    process_request()
```

### Step 4: Update Logging Module for Context

Add to `src/core/logging.py`:
```python
def bind_context(**kwargs: Any) -> None:
    """Bind context variables to the logger.

    This is for persistent context that should remain for the
    lifetime of the application or a long-running operation.

    For request-scoped context, use logger.contextualize() instead.

    Args:
        **kwargs: Context variables to bind.

    Example:
        >>> bind_context(service_name="api", version="1.0.0")
    """
    logger.configure(extra=kwargs)
```

### Step 5: Create Tests

Create `tests/unit/api/middleware/test_request_logging_simplified.py`:
```python
"""Tests for simplified request logging middleware."""

import asyncio
from unittest.mock import Mock, AsyncMock

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from loguru import logger

from src.api.middleware.request_context import RequestContextMiddleware
from src.api.middleware.request_logging import RequestLoggingMiddleware
from src.core.config import LogConfig, Settings
from src.core.context import RequestContext


@pytest.fixture
def capture_logs():
    """Fixture to capture Loguru logs."""
    logs = []

    def sink(message):
        logs.append(message.record)

    handler_id = logger.add(sink, level="DEBUG")
    yield logs
    logger.remove(handler_id)


@pytest.fixture
def test_app():
    """Create test FastAPI app with middleware."""
    app = FastAPI()

    # Add test endpoint
    @app.get("/test")
    async def test_endpoint():
        # Log something to verify context
        logger.info("Inside endpoint")
        return {"status": "ok"}

    @app.get("/slow")
    async def slow_endpoint():
        await asyncio.sleep(0.1)
        return {"status": "slow"}

    @app.get("/error")
    async def error_endpoint():
        raise ValueError("Test error")

    # Add middleware in correct order
    log_config = LogConfig(
        excluded_paths=["/health"],
        slow_request_threshold_ms=50,
    )
    app.add_middleware(RequestLoggingMiddleware, log_config=log_config)
    app.add_middleware(RequestContextMiddleware)

    return app


class TestRequestLoggingMiddleware:
    """Test request logging middleware."""

    def test_basic_request_logging(self, test_app, capture_logs):
        """Test basic request is logged."""
        client = TestClient(test_app)

        response = client.get("/test")

        assert response.status_code == 200

        # Check logs
        log_messages = [log["message"] for log in capture_logs]
        assert "Request started" in log_messages
        assert "Request completed" in log_messages
        assert "Inside endpoint" in log_messages

        # Check context propagation
        for log in capture_logs:
            if log["message"] in ["Request started", "Request completed", "Inside endpoint"]:
                assert "correlation_id" in log["extra"]
                assert "request_id" in log["extra"]
                assert "method" in log["extra"]
                assert log["extra"]["method"] == "GET"
                assert log["extra"]["path"] == "/test"

    def test_excluded_paths(self, test_app, capture_logs):
        """Test excluded paths are not logged."""
        # Add health endpoint
        @test_app.get("/health")
        async def health():
            return {"status": "ok"}

        client = TestClient(test_app)
        response = client.get("/health")

        assert response.status_code == 200

        # Should not have request logs
        log_messages = [log["message"] for log in capture_logs]
        assert "Request started" not in log_messages
        assert "Request completed" not in log_messages

    def test_correlation_id_propagation(self, test_app, capture_logs):
        """Test correlation ID propagates correctly."""
        client = TestClient(test_app)

        # Send request with correlation ID
        headers = {"X-Correlation-ID": "test-correlation-123"}
        response = client.get("/test", headers=headers)

        assert response.status_code == 200
        assert response.headers["X-Correlation-ID"] == "test-correlation-123"

        # All logs should have the same correlation ID
        for log in capture_logs:
            if "correlation_id" in log["extra"]:
                assert log["extra"]["correlation_id"] == "test-correlation-123"

    def test_request_id_generation(self, test_app, capture_logs):
        """Test request ID is generated and returned."""
        client = TestClient(test_app)

        response = client.get("/test")

        assert response.status_code == 200
        assert "X-Request-ID" in response.headers

        request_id = response.headers["X-Request-ID"]

        # Check logs have request ID
        for log in capture_logs:
            if log["message"] in ["Request started", "Request completed"]:
                assert log["extra"]["request_id"] == request_id

    def test_slow_request_warning(self, test_app, capture_logs):
        """Test slow requests generate warnings."""
        client = TestClient(test_app)

        response = client.get("/slow")

        assert response.status_code == 200

        # Check for slow request warning
        warning_logs = [
            log for log in capture_logs
            if log["message"] == "Slow request detected"
        ]
        assert len(warning_logs) == 1
        assert warning_logs[0]["level"].name == "WARNING"
        assert warning_logs[0]["extra"]["duration_ms"] > 50

    def test_error_logging(self, test_app, capture_logs):
        """Test errors are logged correctly."""
        client = TestClient(test_app)

        response = client.get("/error")

        assert response.status_code == 500

        # Check error was logged
        error_logs = [
            log for log in capture_logs
            if log["message"] == "Request failed"
        ]
        assert len(error_logs) == 1
        assert error_logs[0]["level"].name == "ERROR"
        assert error_logs[0]["extra"]["error_type"] == "ValueError"
        assert error_logs[0]["extra"]["error_message"] == "Test error"

    def test_performance_metrics(self, test_app, capture_logs):
        """Test performance metrics are tracked."""
        client = TestClient(test_app)

        response = client.get("/test")

        assert response.status_code == 200

        # Find completion log
        completion_logs = [
            log for log in capture_logs
            if log["message"] == "Request completed"
        ]
        assert len(completion_logs) == 1

        # Check duration is tracked
        assert "duration_ms" in completion_logs[0]["extra"]
        assert completion_logs[0]["extra"]["duration_ms"] > 0
        assert completion_logs[0]["extra"]["status_code"] == 200


class TestContextPropagation:
    """Test context propagation through async calls."""

    @pytest.mark.asyncio
    async def test_async_context_propagation(self):
        """Test correlation ID propagates through async operations."""
        correlation_id = "async-test-123"

        async def nested_operation():
            logger.info("Nested operation")
            # Context should be available here
            assert RequestContext.get_correlation_id() == correlation_id

        # Set context
        RequestContext.set_correlation_id(correlation_id)

        # Use contextualize for proper async propagation
        with logger.contextualize(correlation_id=correlation_id):
            logger.info("Main operation")
            await nested_operation()

            # Verify context still set
            assert RequestContext.get_correlation_id() == correlation_id
```

## Validation Checklist

- [ ] RequestContextMiddleware updated to use Loguru contextualize
- [ ] RequestLoggingMiddleware created (~150 lines)
- [ ] Middleware registered in correct order
- [ ] Correlation IDs propagate through async contexts
- [ ] Request IDs generated and returned in headers
- [ ] Slow requests generate warnings
- [ ] Errors are logged with context
- [ ] Excluded paths are not logged
- [ ] All tests passing
- [ ] `make lint` passes
- [ ] `make type-check` passes

## Expected Results

After Phase 2:
- All requests logged with correlation IDs
- Request duration tracked
- Correlation IDs propagate through entire request lifecycle
- ~20-30 tests for middleware functionality
- Clean, structured logs with request context

## Testing the Integration

Manual test to verify everything works:

```bash
# Start the application
make dev

# Make a request with correlation ID
curl -H "X-Correlation-ID: test-123" http://localhost:8000/

# Check logs show:
# - Request started with correlation_id=test-123
# - Request completed with same correlation ID
# - Duration in milliseconds

# Make a request without correlation ID
curl http://localhost:8000/

# Check logs show:
# - Auto-generated correlation ID
# - Request ID in response headers
```

## Notes for Next Phases

- Phase 3 will add cloud-specific formatters that use this context
- Current implementation is cloud-agnostic
- Context propagation is critical for distributed tracing
- Keep middleware lightweight for performance

## Troubleshooting

### Context Not Propagating
- Ensure using `logger.contextualize()` not `logger.bind()`
- Check RequestContextMiddleware runs before RequestLoggingMiddleware
- Verify contextvars are properly set

### Missing Correlation IDs
- Check middleware order in application
- Ensure RequestContext.set_correlation_id() is called
- Verify async context is not broken

### Performance Issues
- Check slow_request_threshold_ms is reasonable
- Ensure not logging request/response bodies (removed in simplification)
- Verify enqueue=True in logger setup
