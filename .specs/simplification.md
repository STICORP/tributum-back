# Tributum Backend: Comprehensive Observability Simplification Plan

## Table of Contents
1. [Executive Summary](#executive-summary)
2. [Current State Analysis](#current-state-analysis)
3. [Codebase Architecture Overview](#codebase-architecture-overview)
4. [Modules That Remain Unchanged](#modules-that-remain-unchanged)
5. [Proposed Solution](#proposed-solution)
6. [Implementation Details](#implementation-details)
7. [Cloud Portability and Development Environment](#cloud-portability-and-development-environment)
8. [Import Migration Guide](#import-migration-guide)
9. [Integration Details](#integration-details)
10. [Type Safety Considerations](#type-safety-considerations)
11. [Feature Comparison](#feature-comparison)
12. [Test Impact Analysis](#test-impact-analysis)
13. [Testing with Loguru](#testing-with-loguru)
14. [Dependency Changes](#dependency-changes)
15. [Configuration Simplification](#configuration-simplification)
16. [Implementation Approach](#implementation-approach)
17. [Documentation Updates Required](#documentation-updates-required)
18. [Risk Assessment](#risk-assessment)
19. [Common Pitfalls](#common-pitfalls)
20. [Migration Script](#migration-script)
21. [Rollback Plan](#rollback-plan)
22. [Expected Outcomes](#expected-outcomes)

## Executive Summary

The Tributum backend currently contains **3,052 lines of custom observability code** that can be reduced to **~300 lines** while maintaining all business-critical features and providing cloud-agnostic flexibility. This plan outlines a complete replacement strategy using:

- **Loguru** for structured logging (replacing structlog) - works anywhere
- **Native OpenTelemetry** with pluggable exporters (vendor-neutral)
- **Cloud provider features** (GCP initially, easily portable to AWS/Azure)

Key benefits:
- 90% code reduction
- Cloud-agnostic design (migrate between clouds in hours, not weeks)
- Works in development without cloud access
- Improved maintainability
- Faster development velocity
- No vendor lock-in

## Current State Analysis

### Observability Code Breakdown (3,052 lines)

1. **Core Logging Module** (`src/core/logging.py`) - **875 lines**
   - Structured logging using structlog
   - Custom ORJSONRenderer for performance
   - Multiple custom processors for context injection
   - Advanced context management with layering
   - Auto-configuration system

2. **Request Logging Middleware** (`src/api/middleware/request_logging.py`) - **855 lines**
   - Comprehensive HTTP request/response logging
   - Request/response body parsing and sanitization
   - Performance metrics tracking
   - OpenTelemetry integration
   - Database query metrics collection

3. **Error Context Handling** (`src/core/error_context.py`) - **589 lines**
   - Advanced sensitive data detection (credit cards with Luhn, emails, phones, UUIDs, JWTs)
   - Multiple sanitization strategies (redact, mask, hash, truncate)
   - Configurable per-field sanitization
   - Circular reference detection

4. **Observability Module** (`src/core/observability.py`) - **733 lines**
   - OpenTelemetry integration for tracing and metrics
   - Custom CompositeSampler with intelligent sampling rules
   - GCP Cloud Trace and Cloud Monitoring exporters
   - System metrics collection
   - Error context enrichment

### Current Features Implemented

- Correlation ID propagation across async contexts
- 24 sensitive patterns for data redaction (19 field patterns + 5 value detection patterns)
- Credit card validation using Luhn algorithm
- Request/response body logging with size limits
- Database query performance tracking per request
- Memory and CPU usage monitoring
- Error fingerprinting for grouping
- Distributed tracing with custom sampling
- 30+ configuration options
- Context layering with depth limits

## Codebase Architecture Overview

Based on comprehensive analysis of the `src/` directory:

```
src/
├── api/                 # API layer - FastAPI application
│   ├── middleware/      # Middleware stack (executed in reverse order):
│   │   ├── security_headers.py    # Security headers (first)
│   │   ├── request_context.py     # Correlation IDs (second)
│   │   ├── request_logging.py     # Logging (third)
│   │   └── error_handler.py       # Error handling (fourth)
│   ├── schemas/         # Pydantic models
│   └── utils/           # Custom response classes
│
├── core/                # Core business logic
│   ├── config.py        # Pydantic Settings configuration
│   ├── logging.py       # Structured logging (TO BE REPLACED)
│   ├── observability.py # OpenTelemetry setup (TO BE SIMPLIFIED)
│   ├── error_context.py # Error sanitization (TO BE SIMPLIFIED)
│   ├── context.py       # Request context management
│   ├── exceptions.py    # Custom exception classes
│   └── types.py         # Type definitions
│
└── infrastructure/      # External services
    └── database/        # SQLAlchemy async setup
        ├── base.py      # Base model with common fields
        ├── repository.py # Generic repository pattern
        └── session.py    # Async session management
```

### Key Integration Points

1. **Configuration flows** from `Settings` → all components
2. **Logging is integrated** into every layer via `get_logger()`
3. **Correlation IDs propagate** through contextvars
4. **Error handling** uses custom exceptions with sanitization
5. **Database operations** track query metrics in logger context
6. **OpenTelemetry** instruments FastAPI and SQLAlchemy

## Modules That Remain Unchanged

The following modules will remain in the codebase with minimal or no changes:

### Core Layer
- **`src/core/context.py`** - Keep for correlation ID management using contextvars
- **`src/core/exceptions.py`** - Keep all custom exception classes (TributumError hierarchy)
- **`src/core/types.py`** - Keep all type definitions (JsonValue, LogContext, etc.)
- **`src/core/constants.py`** - Update to remove only logging-related constants

### API Layer
- **`src/api/middleware/request_context.py`** - Keep as-is for correlation ID generation
- **`src/api/middleware/security_headers.py`** - Keep as-is for security headers
- **`src/api/middleware/error_handler.py`** - Minor updates to use Loguru instead of get_logger()
- **`src/api/schemas/`** - Keep all schemas unchanged (ErrorResponse, etc.)
- **`src/api/utils/responses.py`** - Keep ORJSONResponse for fast JSON serialization
- **`src/api/constants.py`** - Keep all API-specific constants

### Infrastructure Layer
- **All files** - Unchanged except for updating logging imports from `get_logger()` to `logger`
- **`src/infrastructure/constants.py`** - Keep all infrastructure constants

## Proposed Solution

### 1. Replace structlog with Loguru

**Rationale**: Loguru provides equivalent features with 90% less code
- Built-in async support with `enqueue=True`
- Native JSON serialization
- Simple context management with `bind()`
- Automatic exception handling
- Built-in rotation and retention
- **Cloud-agnostic**: Pure Python, works anywhere

### 2. Vendor-Neutral OpenTelemetry Implementation

**Rationale**: Use standard OpenTelemetry patterns for maximum portability
- **Pluggable exporters**: Switch between GCP, AWS, Azure, or OTLP in minutes
- Standard FastAPI instrumentation (works with any backend)
- Default sampling strategies (vendor-independent)
- **Development mode**: Console exporter for local development

### 3. Cloud Provider Abstraction Layer

**Design for portability from day one**:
- **Pluggable log formatters**: GCP, AWS, Azure, or generic JSON
- **Configurable exporters**: Change providers via environment variables
- **Local development**: Full functionality without cloud services
- **Migration path**: Switch clouds by changing configuration, not code

## Implementation Details

### 1. Loguru Configuration with Full Type Safety

```python
# src/core/logging.py (new implementation)
"""Logging configuration using Loguru with full type safety and GCP integration."""

from __future__ import annotations

import json
import logging
import sys
from collections.abc import Mapping
from functools import lru_cache
from typing import TYPE_CHECKING, Any, ClassVar, Final, TypeAlias

from loguru import logger

if TYPE_CHECKING:
    from loguru import FilterDict, FormatFunction, Record

    from src.core.config import Settings

# Type aliases for clarity
LogLevel: TypeAlias = str
CorrelationID: TypeAlias = str
LogContext: TypeAlias = dict[str, Any]

# Constants
DEFAULT_LOG_FORMAT: Final[str] = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
    "{message}"
)

class InterceptHandler(logging.Handler):
    """Intercept standard logging and redirect to Loguru.

    This handler captures logs from libraries using standard logging
    and forwards them to Loguru for consistent formatting.
    """

    def emit(self, record: logging.LogRecord) -> None:
        """Forward log record to Loguru.

        Args:
            record: Standard library LogRecord to forward.
        """
        # Find caller from where originated the logged message
        frame, depth = sys._getframe(6), 6
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            record.levelname, record.getMessage()
        )


def should_log_path(record: dict[str, Any]) -> bool:
    """Filter out excluded paths from logs.

    Args:
        record: Loguru record dictionary.

    Returns:
        bool: True if the path should be logged.
    """
    # Implementation would check against excluded_paths from settings
    return True


def serialize_for_json(record: Record) -> str:
    """Format log record as generic JSON (for development/self-hosted).

    Args:
        record: Loguru record to format.

    Returns:
        str: JSON-formatted log entry.
    """
    log_entry = {
        "timestamp": record["time"].isoformat(),
        "level": record["level"].name,
        "message": record["message"],
        "logger": record["name"],
        "function": record["function"],
        "module": record["module"],
        "line": record["line"],
    }

    # Add extra fields
    if extra := record.get("extra", {}):
        log_entry.update(extra)

    # Add exception info
    if exc := record.get("exception"):
        log_entry["exception"] = {
            "type": exc.type.__name__ if exc.type else None,
            "value": str(exc.value) if exc.value else None,
            "traceback": exc.traceback if exc.traceback else None,
        }

    return json.dumps(log_entry, default=str) + "\n"


def serialize_for_gcp(record: Record) -> str:
    """Format log record for GCP Cloud Logging.

    Args:
        record: Loguru record to format.

    Returns:
        str: JSON-formatted log entry for GCP.
    """
    # Build GCP-compatible log entry
    log_entry = {
        "severity": record["level"].name,
        "message": record["message"],
        "timestamp": record["time"].isoformat(),
        "logging.googleapis.com/labels": {
            "function": record["function"],
            "module": record["module"],
            "line": str(record["line"]),
        },
    }

    # Add any extra fields
    if record.get("extra"):
        log_entry["jsonPayload"] = record["extra"]

    # Add trace context if available
    if correlation_id := record["extra"].get("correlation_id"):
        log_entry["logging.googleapis.com/trace"] = correlation_id

    # Add source location for GCP Error Reporting
    if record.get("exception"):
        log_entry["logging.googleapis.com/sourceLocation"] = {
            "file": record["file"].path,
            "line": str(record["line"]),
            "function": record["function"],
        }

    return json.dumps(log_entry, default=str) + "\n"


def serialize_for_aws(record: Record) -> str:
    """Format log record for AWS CloudWatch.

    Args:
        record: Loguru record to format.

    Returns:
        str: JSON-formatted log entry for AWS.
    """
    log_entry = {
        "timestamp": record["time"].isoformat(),
        "level": record["level"].name,
        "message": record["message"],
        "logger": record["name"],
        "requestId": record["extra"].get("correlation_id"),
        "function": record["function"],
        "module": record["module"],
        "line": record["line"],
    }

    # Add extra fields under customDimensions
    if extra := record.get("extra", {}):
        log_entry["customDimensions"] = extra

    return json.dumps(log_entry, default=str) + "\n"


# Formatter registry
LOG_FORMATTERS = {
    "json": serialize_for_json,
    "gcp": serialize_for_gcp,
    "aws": serialize_for_aws,
    "console": None,  # Use Loguru's default console formatter
}


@lru_cache(maxsize=1)
def setup_logging(settings: Settings) -> None:
    """Configure Loguru for the application with pluggable formatters.

    Args:
        settings: Application settings containing log configuration.

    Note:
        This function uses lru_cache to ensure it's only called once.
    """
    # Remove default handler
    logger.remove()

    # Get formatter based on configuration
    formatter_type = settings.log_config.log_formatter_type
    formatter = LOG_FORMATTERS.get(formatter_type)

    if formatter_type == "console" or formatter is None:
        # Human-readable console format (for development)
        logger.add(
            sys.stdout,
            format=DEFAULT_LOG_FORMAT,
            level=settings.log_config.log_level,
            enqueue=True,
            colorize=True,
            diagnose=settings.debug,
            backtrace=settings.debug,
        )
    else:
        # Structured format for cloud providers or JSON
        logger.add(
            sys.stdout,
            format=formatter,
            level=settings.log_config.log_level,
            enqueue=True,  # Thread-safe async logging
            serialize=False,  # We handle serialization in format function
            diagnose=False,  # No variable values in production
            backtrace=False,  # Minimal traceback in production
        )

    # Configure standard library logging to use Loguru
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)

    # Disable noisy loggers
    for logger_name in ["uvicorn.access", "urllib3.connectionpool"]:
        logging.getLogger(logger_name).disabled = True


def bind_context(**kwargs: Any) -> None:
    """Bind context variables to the logger.

    Args:
        **kwargs: Context variables to bind.

    Example:
        >>> bind_context(user_id=123, request_id="abc")
    """
    logger.configure(extra=kwargs)


def get_logger(name: str) -> Any:  # Returns loguru.Logger but can't import at module level
    """Get a logger instance with the given name.

    Args:
        name: Logger name, typically __name__.

    Returns:
        Logger instance bound with the name.
    """
    return logger.bind(logger_name=name)
```

### 2. Simplified Request Logging Middleware

```python
# src/api/middleware/request_logging.py (new implementation)
"""Request logging middleware with performance tracking."""

from __future__ import annotations

import time
import uuid
from typing import TYPE_CHECKING, Any, Final

from fastapi import Request, Response
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

if TYPE_CHECKING:
    from src.core.config import LogConfig

# Constants
EXCLUDED_HEADERS: Final[set[str]] = {"authorization", "cookie", "x-api-key"}
MAX_BODY_LOG_SIZE: Final[int] = 10240  # 10KB


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging HTTP requests and responses.

    This middleware:
    - Generates/extracts request IDs
    - Logs request details with timing
    - Tracks basic performance metrics
    - Integrates with GCP Cloud Logging
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

        # Bind context for this request
        with logger.contextualize(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            client_host=request.client.host if request.client else None,
        ):
            # Log request start
            logger.info("Request started")

            # Track timing
            start_time = time.perf_counter()

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
```

### 3. Native OpenTelemetry with Type Safety

```python
# src/core/observability.py (new implementation)
"""Observability configuration using OpenTelemetry with pluggable exporters."""

from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING, Any, Final

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
    SpanExporter,
)

if TYPE_CHECKING:
    from fastapi import FastAPI

    from src.core.config import Settings

# Constants
SERVICE_NAME_KEY: Final[str] = "service.name"
SERVICE_VERSION_KEY: Final[str] = "service.version"
ENVIRONMENT_KEY: Final[str] = "deployment.environment"


def get_span_exporter(settings: Settings) -> SpanExporter | None:
    """Get the appropriate span exporter based on configuration.

    Args:
        settings: Application settings.

    Returns:
        SpanExporter: Configured exporter or None if disabled.
    """
    exporter_type = settings.observability_config.exporter_type.lower()

    if exporter_type == "console":
        # Console exporter for local development
        return ConsoleSpanExporter(
            out=open("traces.log", "a") if settings.observability_config.trace_to_file
            else None
        )

    elif exporter_type == "gcp":
        # GCP Cloud Trace (only import if needed)
        from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter

        return CloudTraceSpanExporter(
            project_id=settings.observability_config.gcp_project_id
        )

    elif exporter_type == "aws":
        # AWS X-Ray via OTLP
        return OTLPSpanExporter(
            endpoint=settings.observability_config.exporter_endpoint or
                     "http://localhost:4317",
            insecure=True,  # Use TLS in production
        )

    elif exporter_type == "otlp":
        # Generic OTLP exporter (Jaeger, Zipkin, etc.)
        return OTLPSpanExporter(
            endpoint=settings.observability_config.exporter_endpoint or
                     "http://localhost:4317",
            insecure=settings.environment == "development",
        )

    elif exporter_type == "none":
        # Explicitly disabled
        return None

    else:
        # Unknown exporter type, use console in development
        if settings.environment == "development":
            return ConsoleSpanExporter()
        return None


@lru_cache(maxsize=1)
def get_tracer(name: str) -> trace.Tracer:
    """Get a tracer instance for the given component.

    Args:
        name: Component name, typically __name__.

    Returns:
        Tracer: OpenTelemetry tracer instance.
    """
    return trace.get_tracer(name)


def setup_tracing(app: FastAPI, settings: Settings) -> None:
    """Configure OpenTelemetry tracing with pluggable exporters.

    Args:
        app: FastAPI application instance.
        settings: Application settings.
    """
    if not settings.observability_config.enable_tracing:
        return

    # Create resource with service information
    resource = Resource.create({
        SERVICE_NAME_KEY: settings.app_name,
        SERVICE_VERSION_KEY: settings.app_version,
        ENVIRONMENT_KEY: settings.environment,
    })

    # Create tracer provider
    tracer_provider = TracerProvider(resource=resource)

    # Get the appropriate exporter
    exporter = get_span_exporter(settings)
    if exporter:
        tracer_provider.add_span_processor(
            BatchSpanProcessor(exporter)
        )

    # Set as global tracer provider
    trace.set_tracer_provider(tracer_provider)

    # Instrument FastAPI
    FastAPIInstrumentor.instrument_app(
        app,
        excluded_urls="/health,/metrics,/docs,/redoc,/openapi.json",
    )

    # Instrument SQLAlchemy if database is configured
    if settings.database_config:
        SQLAlchemyInstrumentor().instrument(
            enable_commenter=True,
            commenter_options={
                "opentelemetry_values": True,
            },
        )


def add_span_attributes(**attributes: Any) -> None:
    """Add attributes to the current span.

    Args:
        **attributes: Key-value pairs to add as span attributes.
    """
    span = trace.get_current_span()
    if span and span.is_recording():
        for key, value in attributes.items():
            span.set_attribute(key, str(value))
```

### 4. Simplified Error Context

```python
# src/core/error_context.py (new implementation)
"""Error context management with basic sensitive data sanitization."""

from __future__ import annotations

import re
from typing import Any, Final, Pattern

# Sensitive field patterns
SENSITIVE_FIELD_PATTERN: Final[Pattern[str]] = re.compile(
    r"(password|secret|token|api_key|apikey|auth|credential|private_key|ssn|pin)",
    re.IGNORECASE,
)

REDACTED: Final[str] = "[REDACTED]"


def is_sensitive_field(field_name: str) -> bool:
    """Check if a field name indicates sensitive data.

    Args:
        field_name: The field name to check.

    Returns:
        bool: True if the field appears to contain sensitive data.
    """
    return bool(SENSITIVE_FIELD_PATTERN.search(field_name))


def sanitize_value(value: Any, field_name: str = "") -> Any:
    """Sanitize a value if it appears to be sensitive.

    Args:
        value: The value to potentially sanitize.
        field_name: The field name for context.

    Returns:
        Any: Sanitized value or original if not sensitive.
    """
    if is_sensitive_field(field_name):
        return REDACTED

    if isinstance(value, dict):
        return {k: sanitize_value(v, k) for k, v in value.items()}

    if isinstance(value, list):
        return [sanitize_value(item) for item in value]

    return value


def sanitize_dict(data: dict[str, Any]) -> dict[str, Any]:
    """Sanitize a dictionary by redacting sensitive fields.

    Args:
        data: Dictionary to sanitize.

    Returns:
        dict[str, Any]: Sanitized copy of the dictionary.
    """
    return {key: sanitize_value(value, key) for key, value in data.items()}
```

### 5. Simplified Configuration

```python
# src/core/config.py (updated classes only)

class LogConfig(BaseModel):
    """Simplified logging configuration."""

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Logging level",
    )
    log_formatter_type: Literal["console", "json", "gcp", "aws"] = Field(
        default="console",
        description="Log output formatter (console for dev, json/gcp/aws for production)",
    )
    excluded_paths: list[str] = Field(
        default_factory=lambda: ["/health", "/metrics"],
        description="Paths to exclude from request logging",
    )
    slow_request_threshold_ms: int = Field(
        default=1000,
        gt=0,
        description="Threshold for slow request warnings (milliseconds)",
    )
    enable_sql_logging: bool = Field(
        default=False,
        description="Enable SQL query logging",
    )


class ObservabilityConfig(BaseModel):
    """Cloud-agnostic observability configuration."""

    enable_tracing: bool = Field(
        default=True,
        description="Enable OpenTelemetry tracing",
    )
    exporter_type: Literal["console", "gcp", "aws", "otlp", "none"] = Field(
        default="console",
        description="Trace exporter type (console for dev, cloud provider for prod)",
    )
    exporter_endpoint: str | None = Field(
        default=None,
        description="OTLP exporter endpoint (for OTLP/AWS exporters)",
    )
    trace_to_file: bool = Field(
        default=False,
        description="Write console traces to file (traces.log)",
    )
    gcp_project_id: str | None = Field(
        default=None,
        description="GCP project ID (only for GCP exporter)",
    )
    trace_sample_rate: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Trace sampling rate (0.0 to 1.0)",
    )


# Configuration helper for environment-based defaults
def get_config_defaults(environment: str) -> dict[str, Any]:
    """Get default configuration based on environment.

    Args:
        environment: The deployment environment.

    Returns:
        dict: Default configuration values.
    """
    if environment == "production":
        return {
            "log_config": {
                "log_formatter_type": "gcp",  # Or "aws" based on cloud provider
            },
            "observability_config": {
                "exporter_type": "gcp",  # Or "aws" based on cloud provider
            },
        }
    else:
        # Development defaults
        return {
            "log_config": {
                "log_formatter_type": "console",
            },
            "observability_config": {
                "exporter_type": "console",
                "trace_to_file": True,
            },
        }
```

## Cloud Portability and Development Environment

### Local Development Without Cloud Services

The solution is designed to work without any cloud services for local development:

```yaml
# .env.development
LOG_CONFIG__LOG_FORMATTER_TYPE=console
OBSERVABILITY_CONFIG__EXPORTER_TYPE=console
OBSERVABILITY_CONFIG__TRACE_TO_FILE=true
```

This gives you:
- **Colored console logs** with full debugging information
- **Traces written to `traces.log`** for analysis
- **No cloud dependencies** or authentication required
- **Full observability** features working locally

### Switching Between Cloud Providers

Migration between clouds requires only configuration changes:

#### For GCP Production
```yaml
# .env.production.gcp
LOG_CONFIG__LOG_FORMATTER_TYPE=gcp
OBSERVABILITY_CONFIG__EXPORTER_TYPE=gcp
OBSERVABILITY_CONFIG__GCP_PROJECT_ID=your-project-id
```

#### For AWS Production
```yaml
# .env.production.aws
LOG_CONFIG__LOG_FORMATTER_TYPE=aws
OBSERVABILITY_CONFIG__EXPORTER_TYPE=aws
OBSERVABILITY_CONFIG__EXPORTER_ENDPOINT=https://xray.us-east-1.amazonaws.com
```

#### For Self-Hosted (Kubernetes + Jaeger)
```yaml
# .env.production.selfhosted
LOG_CONFIG__LOG_FORMATTER_TYPE=json
OBSERVABILITY_CONFIG__EXPORTER_TYPE=otlp
OBSERVABILITY_CONFIG__EXPORTER_ENDPOINT=http://jaeger-collector:4317
```

### Migration Time Estimates

| From → To | Code Changes | Config Changes | Total Time |
|-----------|--------------|----------------|------------|
| GCP → AWS | 0 lines | 3 env vars | ~30 minutes |
| GCP → Azure | 0 lines | 3 env vars | ~30 minutes |
| GCP → Self-hosted | 0 lines | 3 env vars | ~1 hour |
| Any → Local Dev | 0 lines | 2 env vars | ~5 minutes |

Compare to current implementation: **weeks of refactoring**

### Environment-Specific Configuration

```python
# Example: Smart defaults based on environment detection
import os

def detect_cloud_provider() -> str:
    """Detect which cloud provider we're running on."""
    if os.getenv("K_SERVICE"):  # Cloud Run
        return "gcp"
    elif os.getenv("AWS_EXECUTION_ENV"):  # AWS Lambda/ECS
        return "aws"
    elif os.getenv("WEBSITE_INSTANCE_ID"):  # Azure
        return "azure"
    else:
        return "console"  # Local development

# In your settings
cloud_provider = detect_cloud_provider()
LOG_CONFIG__LOG_FORMATTER_TYPE = os.getenv("LOG_CONFIG__LOG_FORMATTER_TYPE", cloud_provider)
OBSERVABILITY_CONFIG__EXPORTER_TYPE = os.getenv("OBSERVABILITY_CONFIG__EXPORTER_TYPE", cloud_provider)
```

## Import Migration Guide

### Logging Imports

```python
# Old imports
from src.core.logging import get_logger
logger = get_logger(__name__)

# New imports
from loguru import logger
# No need to create a logger instance - Loguru provides a global logger
```

### Context Binding

```python
# Old context binding
from src.core.logging import bind_logger_context, layered_context
bind_logger_context(user_id=123, request_id="abc")
with layered_context(operation="database_query"):
    # do something

# New context binding
from loguru import logger
logger.bind(user_id=123, request_id="abc")
with logger.contextualize(operation="database_query"):
    # do something
```

### Getting Logger Context

```python
# Old way
from src.core.logging import get_logger_context
context = get_logger_context()

# New way
# Context is automatically included in log records
# Access via record["extra"] in format functions
```

### Error Logging

```python
# Old way
logger.error("Operation failed", exc_info=True, error_context=error_dict)

# New way
logger.exception("Operation failed", **error_dict)
# or
logger.error("Operation failed", exception=True, **error_dict)
```

### Exception Logging Utility

```python
# Old way - using utility function
from src.core.logging import log_exception
log_exception(logger, exc, "Operation failed", extra_context={"user_id": 123})

# New way - use logger.exception directly
logger.exception("Operation failed", user_id=123)
# The exception is automatically captured from the current context
```

### Structured Logging

```python
# Old way
logger.info("User action", user_id=123, action="login", duration_ms=150)

# New way (identical!)
logger.info("User action", user_id=123, action="login", duration_ms=150)
```

## Integration Details

### RequestContextMiddleware Integration

The existing `RequestContextMiddleware` will continue to work but needs to propagate correlation IDs to Loguru:

```python
# In RequestContextMiddleware.dispatch()
correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))

# Set in contextvars (existing)
RequestContext.set_correlation_id(correlation_id)

# Also bind to Loguru using contextualize for request-scoped data
with logger.contextualize(correlation_id=correlation_id):
    # Process the request
    await self.app(scope, receive, send_wrapper)
```

Note: Using `contextualize()` instead of `bind()` ensures the correlation ID is properly scoped to the request and automatically cleaned up.

### Database Session Integration

Update `src/infrastructure/database/dependencies.py`:

```python
# Old
from src.core.logging import get_logger, bind_logger_context

# New
from loguru import logger

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get database session with logging context."""
    async with get_async_session() as session:
        # Bind database metrics to logger
        logger.bind(db_query_count=0, db_query_duration_ms=0.0)
        yield session
```

### Cloud Provider Authentication

Authentication is only needed when using cloud-specific exporters:

#### GCP Authentication (only when `exporter_type=gcp`)

1. **Application Default Credentials (ADC)** - Recommended for development
   ```bash
   gcloud auth application-default login
   ```

2. **Service Account** - For production
   ```bash
   export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account-key.json"
   ```

3. **GCP Metadata Service** - Automatic on GCP (Cloud Run, GKE, etc.)
   - No configuration needed when running on GCP

#### AWS Authentication (only when `exporter_type=aws`)

1. **AWS Credentials** - Via standard AWS SDK methods
   ```bash
   aws configure
   # or
   export AWS_ACCESS_KEY_ID=xxx
   export AWS_SECRET_ACCESS_KEY=xxx
   ```

2. **IAM Roles** - Automatic on AWS (ECS, Lambda, EC2)

#### Local Development (no authentication needed)

When using `exporter_type=console`, no cloud authentication is required. This is the default for development environments.

### Error Handler Integration

Update `src/api/middleware/error_handler.py`:

```python
# Old
from src.core.logging import get_logger
logger = get_logger(__name__)

# New
from loguru import logger

# In exception handlers
logger.error(
    f"Handled {type(exc).__name__}",
    error_code=error_response.error_code,
    status_code=status_code,
    correlation_id=error_response.correlation_id,
)
```

## Type Safety Considerations

### Why `get_logger()` Returns `Any`

In the new implementation, `get_logger()` returns `Any` instead of a typed logger to prevent circular imports:

```python
def get_logger(name: str) -> Any:  # Returns loguru.Logger but can't import at module level
    """Get a logger instance with the given name.

    The return type is Any to avoid circular imports when loguru
    needs to import from src.core.config during initialization.
    """
    return logger.bind(logger_name=name)
```

### Handling MyPy/Pyright Warnings

If type checkers complain about untyped logger usage:

```python
# Option 1: Type assertion
from typing import TYPE_CHECKING, cast
if TYPE_CHECKING:
    from loguru import Logger

logger = cast("Logger", logger)  # Type assertion for type checkers

# Option 2: Type ignore comment (simpler)
logger.info("Message")  # type: ignore[attr-defined]

# Option 3: Create a typed protocol (most robust)
from typing import Protocol

class LoggerProtocol(Protocol):
    """Protocol matching Loguru's logger interface."""
    def info(self, message: str, **kwargs: Any) -> None: ...
    def error(self, message: str, **kwargs: Any) -> None: ...
    def bind(self, **kwargs: Any) -> "LoggerProtocol": ...
    # Add other methods as needed

# Use the protocol for type hints
def process_request(logger: LoggerProtocol) -> None:
    logger.info("Processing request")
```

### Loguru-Specific Patterns

#### `contextualize()` vs `bind()`

- **`logger.contextualize()`** - Returns a context manager for request-scoped data
  ```python
  with logger.contextualize(request_id="123"):
      # All logs within this context include request_id
      await process_request()
  ```

- **`logger.bind()`** - Returns a new logger instance with bound values
  ```python
  user_logger = logger.bind(user_id=456)
  user_logger.info("User action")  # Includes user_id
  ```

#### Accessing Context in Format Functions

```python
def serialize_for_gcp(record: Record) -> str:
    """Format log record for GCP Cloud Logging."""
    # Access all bound context via record["extra"]
    extra = record.get("extra", {})
    correlation_id = extra.get("correlation_id")
    user_id = extra.get("user_id")

    # Build structured log entry
    log_entry = {
        "severity": record["level"].name,
        "message": record["message"],
        "jsonPayload": extra,  # All context data
    }
    return json.dumps(log_entry)
```

## Feature Comparison

### 🟢 Features We'll Keep (Implemented Differently)

| Feature | Current Implementation | New Implementation | Complexity Reduction |
|---------|----------------------|-------------------|---------------------|
| **Structured Logging** | structlog with 12 custom processors | Loguru with built-in features | 95% |
| **JSON Output** | Custom ORJSONRenderer (200 lines) | Loguru's serialize=True | 100% |
| **Correlation IDs** | Complex contextvars management | Loguru's contextualize() | 90% |
| **Request Logging** | 855-line middleware | 150-line middleware | 82% |
| **Async Safety** | Custom async handling | Loguru's enqueue=True | 100% |
| **GCP Cloud Logging** | Manual JSON formatting | Single format function | 95% |
| **Exception Logging** | Custom formatting | Loguru's built-in | 100% |
| **OpenTelemetry Tracing** | 733 lines with custom sampling | 100 lines standard setup | 86% |
| **FastAPI Instrumentation** | Manual with custom hooks | Standard instrumentor | 90% |
| **Basic Sensitive Data Redaction** | 589 lines with patterns | 50 lines simple regex | 91% |
| **Request ID Tracking** | Custom implementation | Standard header handling | 80% |
| **Performance Warnings** | Complex thresholds | Simple duration check | 85% |
| **Error Response Format** | Keep existing ErrorResponse schema | No change | 0% |
| **Database Health Checks** | Keep existing implementation | No change | 0% |

### 🔴 Features We'll Lose

| Feature | Current Implementation | Alternative Solution |
|---------|----------------------|-------------------|
| **Credit Card Detection with Luhn** | Full validation algorithm | Use GCP DLP API if needed |
| **Advanced Pattern Detection** | SSN, UUID, JWT validation | GCP DLP API for compliance |
| **Layered Context Management** | Complex context stacking (rarely used) | Flat context (simpler) |
| **log_exception() utility** | Custom exception logging helper | Direct logger.exception() |
| **Context Size Limits** | Automatic truncation | Trust GCP's limits |
| **Circular Reference Detection** | Full graph traversal | Python's default handling |
| **Custom Error Fingerprinting** | Hash-based grouping | GCP Error Reporting (better) |
| **Field-Specific Sanitization** | Different strategies per field | Uniform redaction |
| **Memory Tracking** | tracemalloc integration | GCP Cloud Monitoring |
| **Active Task Counting** | asyncio task tracking | GCP metrics |
| **Database Query Aggregation** | Per-request metrics | Basic query logging |
| **Custom Sampling Strategies** | Composite sampler | OpenTelemetry defaults |
| **Request/Response Body Parsing** | Full parsing with limits | Log size only |
| **Performance Processors** | Custom CPU/memory tracking | GCP monitoring |
| **Log Sampling** | Custom rate limiting | No sampling needed |
| **Multiple Sanitization Strategies** | redact/mask/hash/truncate | Redact only (sufficient) |

### 🆕 Features We'll Gain

| Feature | Benefit | Impact |
|---------|---------|--------|
| **Built-in Log Rotation** | No manual cleanup | Operational simplicity |
| **Colored Console Output** | Better dev experience | Faster debugging |
| **Native Exception Formatting** | Automatic traceback formatting | Less code |
| **Lazy Evaluation** | Better performance | Lower overhead |
| **Simple Testing** | Easy to mock/capture | Faster test writing |
| **Better IDE Support** | Built-in type hints | Improved DX |
| **GCP Error Reporting Integration** | Automatic error grouping | Better than custom |
| **GCP Cloud Monitoring** | Rich dashboards out-of-box | No custom metrics code |

## Test Impact Analysis

### Current Test Suite
- **Total Test Functions**: ~690 (estimated from test function counts)
- **Affected Test Functions**: 323 (47%)
- **Unaffected Test Functions**: 367 (53%)

Note: These numbers represent individual test functions, not test files. The actual test file count is 66 total, with 19 files specifically for observability features.

### Test Changes Required

| Component | Current Tests | New Tests | Reduction | Strategy |
|-----------|--------------|-----------|-----------|----------|
| Core Logging | 110 | 15 | 86% | Test Loguru config and basic features |
| Request Logging | 77 | 20 | 74% | Test middleware with HTTPX client |
| Error Context | 78 | 10 | 87% | Test basic sanitization only |
| Observability | 53 | 25 | 53% | Test OpenTelemetry setup |
| Error Handlers | 9 | 5 | 44% | Keep error response tests |
| **Total** | **327** | **75** | **77%** | Focus on integration tests |

### New Test Implementation Strategy

```python
# Example: Testing Loguru configuration
import pytest
from loguru import logger

def test_logging_configuration(caplog):
    """Test that Loguru is configured correctly."""
    with caplog.at_level("INFO"):
        logger.info("Test message")
    assert "Test message" in caplog.text

# Example: Testing middleware
async def test_request_logging_middleware(client: TestClient):
    """Test request logging middleware."""
    response = await client.get("/")
    assert "X-Request-ID" in response.headers
```

## Testing with Loguru

### Basic Testing with pytest

#### Using `caplog` Fixture

```python
import pytest
from loguru import logger

def test_with_caplog(caplog):
    """Test logging with pytest's caplog fixture."""
    # caplog works with Loguru via InterceptHandler
    with caplog.at_level("INFO"):
        logger.info("Test message")

    assert "Test message" in caplog.text
    assert caplog.records[0].levelname == "INFO"
```

#### Creating a Test Sink

```python
import pytest
from loguru import logger

@pytest.fixture
def capture_logs():
    """Fixture to capture Loguru logs."""
    # Remove default handlers
    logger.remove()

    # Create list to capture logs
    logs = []

    # Add handler that captures to list
    handler_id = logger.add(
        lambda msg: logs.append(msg),
        format="{time} | {level} | {message} | {extra}",
        level="DEBUG"
    )

    yield logs

    # Cleanup
    logger.remove(handler_id)
    # Re-add default handler for other tests
    logger.add(sys.stderr)

def test_with_capture(capture_logs):
    """Test using custom log capture."""
    logger.info("Test message", user_id=123)

    assert len(capture_logs) == 1
    assert "Test message" in capture_logs[0]
    assert "user_id" in capture_logs[0]
```

### Testing Async Code

```python
import pytest
from loguru import logger

@pytest.mark.asyncio
async def test_async_logging(capture_logs):
    """Test logging in async functions."""
    async def async_operation():
        logger.info("Starting async operation")
        # Simulate async work
        await asyncio.sleep(0.1)
        logger.info("Completed async operation")

    await async_operation()

    assert len(capture_logs) == 2
    assert "Starting async operation" in capture_logs[0]
    assert "Completed async operation" in capture_logs[1]
```

### Testing Context Propagation

```python
@pytest.mark.asyncio
async def test_context_propagation(capture_logs):
    """Test that context propagates through async calls."""
    async def nested_operation():
        logger.info("Nested operation")

    with logger.contextualize(request_id="test-123"):
        logger.info("Main operation")
        await nested_operation()

    # Both logs should have request_id
    for log in capture_logs:
        assert "request_id" in log
        assert "test-123" in log
```

### Testing Middleware

```python
from fastapi.testclient import TestClient
from src.api.main import app

@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)

def test_request_logging_middleware(client, capture_logs):
    """Test that middleware logs requests."""
    response = client.get("/health")

    # Find request logs
    request_logs = [log for log in capture_logs if "Request" in log]

    assert len(request_logs) >= 2  # Start and complete
    assert any("Request started" in log for log in request_logs)
    assert any("Request completed" in log for log in request_logs)

    # Check for request ID header
    assert "X-Request-ID" in response.headers
```

### Testing Error Logging

```python
def test_exception_logging(capture_logs):
    """Test exception logging."""
    try:
        raise ValueError("Test error")
    except ValueError:
        logger.exception("Error occurred")

    assert len(capture_logs) == 1
    assert "Error occurred" in capture_logs[0]
    assert "ValueError: Test error" in capture_logs[0]
    assert "Traceback" in capture_logs[0]
```

### Testing Structured Data

```python
import json

@pytest.fixture
def json_logs():
    """Capture logs as JSON."""
    logger.remove()
    logs = []

    def sink(message):
        # Parse the JSON log entry
        logs.append(json.loads(message))

    handler_id = logger.add(sink, serialize=True, level="DEBUG")

    yield logs

    logger.remove(handler_id)
    logger.add(sys.stderr)

def test_structured_logging(json_logs):
    """Test structured logging output."""
    logger.info("User action", user_id=123, action="login")

    assert len(json_logs) == 1
    log_entry = json_logs[0]

    assert log_entry["text"] == "User action"
    assert log_entry["record"]["extra"]["user_id"] == 123
    assert log_entry["record"]["extra"]["action"] == "login"
```

### Mocking Loguru in Unit Tests

```python
from unittest.mock import Mock, patch

def test_with_mock_logger():
    """Test with mocked logger."""
    mock_logger = Mock()

    with patch("loguru.logger", mock_logger):
        # Your code that uses logger
        from your_module import function_that_logs
        function_that_logs()

    # Verify logging calls
    mock_logger.info.assert_called_once()
    mock_logger.error.assert_not_called()
```

### Testing in Cloud-Agnostic Environment

```python
@pytest.fixture
def test_settings():
    """Settings for testing without cloud dependencies."""
    return Settings(
        environment="development",
        log_config={
            "log_level": "DEBUG",
            "log_formatter_type": "json",  # Use JSON for structured assertions
        },
        observability_config={
            "enable_tracing": True,
            "exporter_type": "console",  # No cloud dependencies
            "trace_to_file": True,
        },
    )

def test_without_cloud_services(test_settings):
    """Test observability features work without cloud access."""
    from src.core.logging import setup_logging
    from src.core.observability import setup_tracing

    # Setup works without any cloud authentication
    setup_logging(test_settings)
    setup_tracing(app, test_settings)

    # Verify traces are written to file
    logger.info("Test message")
    assert Path("traces.log").exists()
```

### Testing Log Configuration

```python
def test_logging_configuration():
    """Test that logging is configured correctly."""
    from src.core.logging import setup_logging
    from src.core.config import Settings

    # Create test settings
    settings = Settings(
        environment="development",
        log_config={"log_level": "DEBUG"}
    )

    # Clear existing handlers
    logger.remove()

    # Setup logging
    setup_logging(settings)

    # Verify configuration
    # Note: Loguru doesn't expose handler config directly
    # Test by logging and checking output format
    with capture_logs() as logs:
        logger.debug("Debug message")
        assert len(logs) == 1  # DEBUG level is active
```

### Best Practices for Testing with Loguru

1. **Always clean up handlers** in fixtures to avoid interference between tests
2. **Use `logger.remove()` carefully** - it removes ALL handlers
3. **Test both message and context** - Loguru excels at structured logging
4. **Mock sparingly** - Loguru is fast enough for most integration tests
5. **Test async context propagation** - Critical for correlation IDs

### Example Test Suite Structure

```python
# tests/unit/core/test_logging.py
class TestLogging:
    """Test logging configuration and utilities."""

    def test_gcp_format(self):
        """Test GCP Cloud Logging format."""
        # Test serialize_for_gcp function

    def test_sensitive_data_exclusion(self):
        """Test that sensitive data is not logged."""
        # Verify passwords, tokens are redacted

    def test_correlation_id_propagation(self):
        """Test correlation ID flows through context."""
        # Verify contextvars integration

# tests/integration/test_logging_integration.py
class TestLoggingIntegration:
    """Integration tests for logging across the application."""

    @pytest.mark.asyncio
    async def test_request_lifecycle_logging(self, client):
        """Test complete request logging lifecycle."""
        # Make request and verify all expected logs

    @pytest.mark.asyncio
    async def test_database_query_logging(self, db_session):
        """Test database operations are logged."""
        # Perform DB operation and check logs
```

## Dependency Changes

### pyproject.toml Updates

```toml
# Core dependencies (always needed):
dependencies = [
    # ... existing dependencies ...
    "loguru>=0.7.2",  # Modern logging library
    "opentelemetry-api>=1.34.1",  # Keep existing
    "opentelemetry-sdk>=1.34.1",  # Keep existing
    "opentelemetry-instrumentation-fastapi>=0.55b1",  # Keep existing
    "opentelemetry-instrumentation-sqlalchemy>=0.55b1",  # Keep existing
    "opentelemetry-exporter-otlp>=1.34.1",  # For OTLP/AWS/self-hosted
]

# Optional cloud-specific dependencies (add only if using that cloud):
# For GCP deployment:
optional-dependencies.gcp = [
    "opentelemetry-exporter-gcp-trace>=1.9.0",  # Keep existing
    "opentelemetry-exporter-gcp-monitoring>=1.9.0a0",  # Keep existing
]

# For AWS deployment (future):
optional-dependencies.aws = [
    # AWS X-Ray support via OTLP is included in core
]

# Remove:
# "structlog>=25.4.0",  # Replaced by loguru

# Keep all other dependencies:
# - orjson (used for API responses)
# - psutil (might be used elsewhere)
# - All database, FastAPI, Pydantic packages
```

### Installation Examples

```bash
# For local development (no cloud dependencies)
uv sync --all-extras --dev

# For GCP production
uv sync --extra gcp

# For AWS production (OTLP already included)
uv sync

# For self-hosted with Jaeger
uv sync
```

### Summary
- **Core Dependencies Added**: 1 (loguru)
- **Dependencies Removed**: 1 (structlog)
- **Cloud Dependencies**: Now optional extras
- **Net Change**: More flexible, less required

## Configuration Simplification

### Current: 30+ Options
```python
# Complex nested configuration with many options
class LogConfig(BaseModel):
    log_level: str
    log_format: str
    render_json_logs: bool
    add_timestamp: bool
    timestamper_format: str
    sampling_rate: float
    enable_async_logging: bool
    async_queue_size: int
    excluded_paths: list[str]
    sensitive_fields: list[str]
    enable_sql_logging: bool
    slow_query_threshold_ms: int
    enable_performance_processor: bool
    enable_environment_processor: bool
    enable_error_context_processor: bool
    log_request_body: bool
    log_response_body: bool
    max_body_log_size: int
    enable_performance_metrics: bool
    track_request_duration: bool
    track_active_tasks: bool
    track_request_sizes: bool
    enable_memory_tracking: bool
    slow_request_threshold_ms: int
    critical_request_threshold_ms: int
    additional_sensitive_patterns: list[str]
    sensitive_value_detection: bool
    excluded_fields_from_sanitization: list[str]
    default_sanitization_strategy: str
    field_sanitization_strategies: dict[str, str]
```

### New: 11 Essential Options (Cloud-Agnostic)
```python
class LogConfig(BaseModel):
    """Simplified logging configuration."""

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    log_formatter_type: Literal["console", "json", "gcp", "aws"] = "console"
    excluded_paths: list[str] = ["/health", "/metrics"]
    slow_request_threshold_ms: int = 1000
    enable_sql_logging: bool = False

class ObservabilityConfig(BaseModel):
    """Cloud-agnostic observability configuration."""

    enable_tracing: bool = True
    exporter_type: Literal["console", "gcp", "aws", "otlp", "none"] = "console"
    exporter_endpoint: str | None = None
    trace_to_file: bool = False
    gcp_project_id: str | None = None
    trace_sample_rate: float = 1.0
```

## Implementation Approach

Since this is unreleased software in early stage, we'll do a **direct replacement** with no migration:

### Week 1: Implementation
1. **Day 1**: Add loguru dependency, create new modules
2. **Day 2-3**: Update all imports throughout codebase
3. **Day 4**: Remove old modules and tests
4. **Day 5**: Write new simplified tests
5. **Day 6**: Run all quality checks, fix any issues

### Implementation Checklist
- [ ] Add loguru to pyproject.toml
- [ ] Create new `src/core/logging.py` with Loguru and pluggable formatters
- [ ] Create cloud-agnostic `src/core/observability.py` with pluggable exporters
- [ ] Create simplified `src/core/error_context.py`
- [ ] Update `src/api/middleware/request_logging.py`
- [ ] Update `src/api/middleware/request_context.py` to propagate correlation IDs to Loguru
- [ ] Update `src/api/middleware/error_handler.py` logging imports
- [ ] Update `src/core/config.py` classes (LogConfig, ObservabilityConfig)
- [ ] Update all imports in codebase using migration script
- [ ] Verify correlation ID propagation through async contexts
- [ ] Update `src/infrastructure/database/dependencies.py` for Loguru
- [ ] Update `src/infrastructure/database/session.py` logging
- [ ] Remove 323 obsolete tests
- [ ] Write 75 new tests with proper fixtures
- [ ] Test local development without cloud services
- [ ] Test GCP Cloud Logging format (when using GCP)
- [ ] Test OpenTelemetry integration with console exporter
- [ ] Verify cloud authentication only required for cloud exporters
- [ ] Delete old modules (2,319 lines)
- [ ] Remove structlog from dependencies
- [ ] Run `make all-checks`
- [ ] Update README.md
- [ ] Update CLAUDE.md
- [ ] Create LOGGING.md
- [ ] Create temporary MIGRATION_NOTES.md
- [ ] Update deployment documentation
- [ ] Benchmark performance improvements
- [ ] Verify all third-party library logs are captured

### Code Quality Compliance

All new code will comply with your strict standards:
- **ALL Ruff rules** enabled (except your specific exclusions)
- **Strict MyPy** type checking
- **Pyright** validation
- **Google-style docstrings**
- **McCabe complexity < 10**
- **100% test coverage**

## Documentation Updates Required

### 1. README.md
- Remove all references to structlog
- Update logging section to show Loguru usage
- Update development setup instructions
- Add note about GCP authentication for observability

### 2. CLAUDE.md
- Add Loguru patterns and best practices
- Update logging examples to use `from loguru import logger`
- Document correlation ID propagation with Loguru
- Add note about avoiding `logger.bind()` for request-scoped data

### 3. Create LOGGING.md
```markdown
# Logging Guide

## Overview
This project uses Loguru for structured logging with GCP Cloud Logging integration.

## Basic Usage
```python
from loguru import logger

# Simple logging
logger.info("User logged in", user_id=123)

# Error logging with context
logger.error("Payment failed", order_id=456, error_code="INSUFFICIENT_FUNDS")

# Exception logging
try:
    process_payment()
except Exception:
    logger.exception("Payment processing error")
```

## Request Context
Request-scoped data is automatically added via middleware:
- `request_id`: Unique request identifier
- `method`: HTTP method
- `path`: Request path
- `correlation_id`: For distributed tracing

## Best Practices
1. Use `logger.contextualize()` for request-scoped data
2. Use `logger.bind()` for persistent context
3. Always include relevant IDs in log messages
4. Let exceptions bubble up after logging

## Configuration
Logging configuration is in `src/core/config.py` under `LogConfig`.
```

### 4. API Documentation
- Update OpenAPI descriptions to mention correlation ID header
- Document `X-Request-ID` response header
- Add examples showing correlation ID usage

### 5. Deployment Documentation
- Add section on GCP authentication methods
- Document required GCP IAM roles:
  - `roles/cloudtrace.agent` for Cloud Trace
  - `roles/logging.logWriter` for Cloud Logging
- Environment variables for GCP configuration

### 6. Migration Notes (temporary)
Create `MIGRATION_NOTES.md` for the team:
- List of import changes
- Common patterns that need updating
- Gotchas and solutions
- Can be deleted after migration complete

### 7. Update Type Stubs
If the project has custom type stubs, update them to remove structlog types.

## Risk Assessment

### Low Risk Areas
- **Loguru**: Mature, well-tested, widely used, cloud-agnostic
- **OpenTelemetry**: Industry standard, vendor-neutral
- **Cloud Integrations**: All use official, well-documented libraries
- **Cloud Portability**: Actually reduces risk by avoiding vendor lock-in

### Medium Risk Areas
- **Sensitive Data Detection**: Simpler approach may miss edge cases
  - *Mitigation*: Use cloud provider DLP APIs (GCP DLP, AWS Macie, etc.) for compliance-critical data
- **Test Coverage**: Temporary dip during refactoring
  - *Mitigation*: Focus on integration tests first

### No Risk Areas
- **No Vendor Lock-in**: Solution works with any cloud provider or locally
- **No External Services Required**: Full functionality in development without cloud access
- **No Data Migration**: Configuration changes only
- **No Breaking Changes**: API contracts remain the same

### New Benefits (Risk Reduction)
- **Multi-Cloud Ready**: Can switch providers without code changes
- **Local Development**: No cloud dependencies for development/testing
- **Cost Control**: Can run entirely locally to reduce cloud costs
- **Compliance Flexibility**: Can keep logs on-premises if required

### Additional Risk Considerations

#### Correlation ID Propagation
- **Risk**: Correlation IDs might not propagate correctly through Loguru's contextvars
- **Mitigation**:
  - Thorough testing of async context propagation
  - Use `logger.contextualize()` for request-scoped data (not `bind()`)
  - Verify with integration tests
  - Ensure RequestContextMiddleware wraps entire request processing

#### Third-party Library Logging
- **Risk**: Libraries using standard logging might not integrate properly
- **Mitigation**:
  - InterceptHandler captures standard logging
  - Test with SQLAlchemy, Uvicorn, and other key libraries
  - Configure log levels for noisy libraries

#### GCP Authentication
- **Risk**: Authentication failures in different environments
- **Mitigation**:
  - Document all authentication methods clearly
  - Test in local, CI/CD, and production environments
  - Provide fallback to local logging if GCP unavailable

#### Type Checking Issues
- **Risk**: MyPy/Pyright might complain about Loguru's dynamic nature
- **Mitigation**:
  - Use type assertions where needed
  - Create protocol types for critical interfaces
  - Document type ignore patterns

#### Performance Regression
- **Risk**: New implementation might be slower than expected
- **Mitigation**:
  - Benchmark before and after
  - Use Loguru's `enqueue=True` for async logging
  - Monitor production performance

## Common Pitfalls

### 1. Context Manager Misuse
**Wrong**:
```python
# This creates a new logger instance, doesn't affect global logger
logger = logger.bind(request_id="123")
```

**Right**:
```python
# Use contextualize for request-scoped data
with logger.contextualize(request_id="123"):
    process_request()
```

### 2. Handler Cleanup in Tests
**Wrong**:
```python
def test_something():
    logger.add(custom_handler)
    # Forgot to remove handler - affects other tests
```

**Right**:
```python
def test_something():
    handler_id = logger.add(custom_handler)
    try:
        # test code
    finally:
        logger.remove(handler_id)
```

### 3. Forgetting InterceptHandler
**Wrong**:
```python
# Standard library logs won't be captured
setup_logging()
```

**Right**:
```python
# Configure standard logging to use Loguru
logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
```

### 4. Import Order Issues
**Wrong**:
```python
# Configure logging after imports
from src.api.main import app
setup_logging()  # Too late!
```

**Right**:
```python
# Configure logging before other imports
setup_logging()
from src.api.main import app
```

## Migration Script

Create `scripts/migrate_logging.py`:

```python
#!/usr/bin/env python3
"""Script to migrate logging imports from structlog to loguru."""

import re
from pathlib import Path

def update_imports(file_path: Path) -> bool:
    """Update imports in a single file."""
    content = file_path.read_text()
    original = content

    # Update imports
    content = re.sub(
        r'from src\.core\.logging import get_logger\nlogger = get_logger\(__name__\)',
        'from loguru import logger',
        content
    )

    # Update other logging imports
    content = re.sub(
        r'from src\.core\.logging import (\w+)',
        r'# TODO: Update \1 usage',
        content
    )

    # Update bind_logger_context calls
    content = re.sub(
        r'bind_logger_context\((.*?)\)',
        r'logger.bind(\1)',
        content
    )

    if content != original:
        file_path.write_text(content)
        return True
    return False

def main():
    """Run migration on all Python files."""
    updated = 0
    for file_path in Path("src").rglob("*.py"):
        if update_imports(file_path):
            print(f"Updated: {file_path}")
            updated += 1

    for file_path in Path("tests").rglob("*.py"):
        if update_imports(file_path):
            print(f"Updated: {file_path}")
            updated += 1

    print(f"\nTotal files updated: {updated}")

if __name__ == "__main__":
    main()
```

### Shell Commands for Additional Updates

```bash
# Find all files that need manual review
grep -r "get_logger_context\|layered_context\|ContextLogger" src tests

# Update simple imports
find src tests -name "*.py" -exec sed -i \
  's/from src.core.logging import get_logger/from loguru import logger/g' {} +

# Remove logger initialization lines
find src tests -name "*.py" -exec sed -i \
  '/logger = get_logger(__name__)/d' {} +
```

## Rollback Plan

Even though this is early-stage software, having a rollback plan provides confidence:

### 1. Git-based Rollback
```bash
# Tag before changes
git tag pre-loguru-migration

# If rollback needed
git revert <commit-hash>
```

### 2. Feature Flag Approach (if desired)
```python
# In settings
use_legacy_logging: bool = Field(default=False)

# In initialization
if settings.use_legacy_logging:
    from src.core.logging_legacy import setup_logging
else:
    from src.core.logging import setup_logging
```

### 3. Parallel Implementation
- Keep old modules renamed with `_legacy` suffix
- Can switch back by updating imports
- Remove after successful production deployment

### 4. Rollback Checklist
- [ ] Revert git commits
- [ ] Re-add structlog to dependencies
- [ ] Restore original test files
- [ ] Update imports back to original
- [ ] Restore log_exception utility function
- [ ] Run full test suite
- [ ] Notify team of rollback

## Expected Outcomes

### Metrics
| Metric | Current | New | Improvement |
|--------|---------|-----|-------------|
| **Lines of Code** | 3,052 | ~300 | 90.2% reduction |
| **Test Count** | 323 | ~75 | 76.8% reduction |
| **Dependencies** | 6 observability | 5 | 1 fewer |
| **Config Options** | 30+ | 11 | 63% reduction |
| **Cloud Portability** | GCP only | Any cloud/local | 100% improvement |
| **Dev Environment** | Requires GCP | Works locally | No cloud needed |
| **Startup Time** | ~2s | <0.5s | Est. 50-75% faster |
| **Memory Usage** | Higher | Lower | Est. 20-30% reduction |

*Note: Performance improvements are estimates. Actual improvements will be benchmarked during implementation.*

### Developer Experience
- **Onboarding**: New developers productive in hours, not days
- **Debugging**: Clearer logs with better formatting
- **Testing**: Simpler test setup and mocking
- **IDE Support**: Better autocomplete with Loguru

### Operational Benefits
- **Cloud Flexibility**: Works with GCP, AWS, Azure, or self-hosted
- **Local Development**: Full observability without cloud dependencies
- **Monitoring**: Rich dashboards with any cloud provider
- **Alerting**: Built-in alerting with your chosen platform
- **Cost**: Lower compute requirements + ability to run locally = lower costs
- **Migration Freedom**: Switch clouds in hours, not weeks

## Conclusion

This plan delivers a 90% reduction in observability code complexity while maintaining all business-critical features and adding cloud portability. By leveraging industry-standard tools (Loguru + OpenTelemetry) with pluggable backends, we achieve better functionality with dramatically less code and no vendor lock-in. The direct replacement approach is appropriate for early-stage software and will be completed within one week.

The key insights:
- **We've been solving problems that the Python ecosystem has already solved better.**
- **Cloud-agnostic design from day one prevents future migration pain.**
- **Local development without cloud services improves developer productivity.**
