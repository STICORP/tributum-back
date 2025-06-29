# Phase 5: Native OpenTelemetry

## Overview
This phase implements vendor-neutral OpenTelemetry tracing with pluggable exporters. The implementation supports local development (console exporter), cloud providers (GCP, AWS), and self-hosted solutions (Jaeger, Zipkin) through configuration alone.

## Prerequisites
- Phase 4 completed (Error context sanitization)
- OpenTelemetry packages already in dependencies (kept from Phase 0)

## Objectives
1. Create simplified observability module (~100 lines vs 733)
2. Implement pluggable exporter system
3. Add standard instrumentation for FastAPI and SQLAlchemy
4. Ensure correlation IDs propagate to traces
5. Test with console exporter (no cloud required)

## Implementation

### Step 1: Create Simplified Observability Module

Create new `src/core/observability.py`:

```python
"""Observability configuration using OpenTelemetry with pluggable exporters.

This module provides vendor-neutral distributed tracing that works with:
- Local development (console/file output)
- Cloud providers (GCP Cloud Trace, AWS X-Ray)
- Self-hosted (Jaeger, Zipkin via OTLP)
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import TYPE_CHECKING, Any, Final

from loguru import logger
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
from opentelemetry.sdk.trace.sampling import TraceIdRatioBased

from src.core.context import RequestContext

if TYPE_CHECKING:
    from fastapi import FastAPI
    from starlette.requests import Request

    from src.core.config import Settings

# Constants
SERVICE_NAME_KEY: Final[str] = "service.name"
SERVICE_VERSION_KEY: Final[str] = "service.version"
ENVIRONMENT_KEY: Final[str] = "deployment.environment"


def get_span_exporter(settings: Settings) -> SpanExporter | None:
    """Get the appropriate span exporter based on configuration.

    This function returns the correct exporter for the configured
    environment without requiring cloud-specific imports unless needed.

    Args:
        settings: Application settings.

    Returns:
        SpanExporter: Configured exporter or None if disabled.
    """
    exporter_type = settings.observability_config.exporter_type.lower()

    if exporter_type == "console":
        # Console exporter for local development
        logger.info("Using console span exporter for development")
        return ConsoleSpanExporter()

    elif exporter_type == "gcp":
        # GCP Cloud Trace - only import if needed
        try:
            from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter

            project_id = settings.observability_config.gcp_project_id
            if not project_id:
                # Try to auto-detect from environment
                project_id = os.getenv("GOOGLE_CLOUD_PROJECT")

            if not project_id:
                logger.warning("GCP project ID not configured, disabling tracing")
                return None

            logger.info(f"Using GCP Cloud Trace exporter for project {project_id}")
            return CloudTraceSpanExporter(project_id=project_id)

        except ImportError:
            logger.error(
                "GCP exporter requested but opentelemetry-exporter-gcp-trace not installed. "
                "Install with: uv add opentelemetry-exporter-gcp-trace"
            )
            return None

    elif exporter_type == "aws":
        # AWS X-Ray via OTLP
        endpoint = settings.observability_config.exporter_endpoint or "http://localhost:4317"
        logger.info(f"Using AWS X-Ray exporter via OTLP at {endpoint}")
        return OTLPSpanExporter(
            endpoint=endpoint,
            insecure=settings.environment == "development",
        )

    elif exporter_type == "otlp":
        # Generic OTLP exporter (Jaeger, Zipkin, etc.)
        endpoint = settings.observability_config.exporter_endpoint or "http://localhost:4317"
        logger.info(f"Using OTLP exporter at {endpoint}")
        return OTLPSpanExporter(
            endpoint=endpoint,
            insecure=settings.environment == "development",
        )

    elif exporter_type == "none":
        # Explicitly disabled
        logger.info("Tracing explicitly disabled")
        return None

    else:
        # Unknown exporter type
        logger.warning(f"Unknown exporter type: {exporter_type}, disabling tracing")
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


def setup_tracing(settings: Settings) -> None:
    """Configure OpenTelemetry tracing with pluggable exporters.

    This function sets up distributed tracing with the configured
    exporter. It works without any cloud dependencies for local
    development.

    Args:
        settings: Application settings.
    """
    if not settings.observability_config.enable_tracing:
        logger.info("Tracing disabled by configuration")
        return

    # Create resource with service information
    resource = Resource.create({
        SERVICE_NAME_KEY: settings.app_name,
        SERVICE_VERSION_KEY: settings.app_version,
        ENVIRONMENT_KEY: settings.environment,
    })

    # Create tracer provider with sampling
    tracer_provider = TracerProvider(
        resource=resource,
        sampler=TraceIdRatioBased(settings.observability_config.trace_sample_rate),
    )

    # Get the appropriate exporter
    exporter = get_span_exporter(settings)
    if exporter:
        tracer_provider.add_span_processor(
            BatchSpanProcessor(exporter)
        )

    # Set as global tracer provider
    trace.set_tracer_provider(tracer_provider)

    logger.info(
        "Tracing configured",
        exporter_type=settings.observability_config.exporter_type,
        sample_rate=settings.observability_config.trace_sample_rate,
    )


def instrument_app(app: FastAPI, settings: Settings) -> None:
    """Instrument FastAPI application for tracing.

    Args:
        app: FastAPI application to instrument.
        settings: Application settings.
    """
    if not settings.observability_config.enable_tracing:
        return

    # Instrument FastAPI
    FastAPIInstrumentor.instrument_app(
        app,
        excluded_urls="/health,/metrics,/docs,/redoc,/openapi.json",
        server_request_hook=add_correlation_id_to_span,
    )

    # Instrument SQLAlchemy if database is configured
    if settings.database_config:
        SQLAlchemyInstrumentor().instrument(
            enable_commenter=True,
            commenter_options={
                "opentelemetry_values": True,
            },
        )

    logger.info("Application instrumented for tracing")


def add_correlation_id_to_span(span: trace.Span, request: Request) -> None:
    """Add correlation ID from context to the current span.

    This is used as a server_request_hook for FastAPI instrumentation
    to ensure correlation IDs are included in traces.

    Args:
        span: The current span.
        request: The current request (unused but required by signature).
    """
    if correlation_id := RequestContext.get_correlation_id():
        span.set_attribute("correlation_id", correlation_id)

    # Also add request ID if available
    if hasattr(request, "headers"):
        if request_id := request.headers.get("X-Request-ID"):
            span.set_attribute("request_id", request_id)


def add_span_attributes(**attributes: Any) -> None:
    """Add attributes to the current span.

    This is a convenience function for adding custom attributes
    to the current trace span.

    Args:
        **attributes: Key-value pairs to add as span attributes.
    """
    span = trace.get_current_span()
    if span and span.is_recording():
        for key, value in attributes.items():
            # OpenTelemetry requires string values for attributes
            span.set_attribute(key, str(value))


def trace_operation(name: str, **attributes: Any) -> Any:
    """Context manager for tracing a custom operation.

    Args:
        name: Operation name for the span.
        **attributes: Initial attributes for the span.

    Returns:
        Context manager that creates a span.

    Example:
        >>> with trace_operation("database_query", query_type="select"):
        >>>     result = await db.execute(query)
    """
    tracer = get_tracer(__name__)
    span = tracer.start_span(name)

    # Add initial attributes
    for key, value in attributes.items():
        span.set_attribute(key, str(value))

    # Add correlation ID if available
    if correlation_id := RequestContext.get_correlation_id():
        span.set_attribute("correlation_id", correlation_id)

    return trace.use_span(span, end_on_exit=True)
```

### Step 2: Update Configuration

Update `src/core/config.py` to add observability configuration:

```python
class ObservabilityConfig(BaseModel):
    """Cloud-agnostic observability configuration."""

    enable_tracing: bool = Field(
        default=True,
        description="Enable OpenTelemetry tracing",
    )
    exporter_type: Literal["console", "gcp", "aws", "otlp", "none"] = Field(
        default="console",
        description="Trace exporter type. Auto-detected if not specified.",
    )
    exporter_endpoint: str | None = Field(
        default=None,
        description="OTLP exporter endpoint (for OTLP/AWS exporters)",
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
```

### Step 3: Update Application Initialization

Update `src/api/main.py`:

```python
# Add imports
from src.core.observability import instrument_app, setup_tracing

# In create_app function, after creating FastAPI instance:
def create_app(settings: Settings | None = None) -> FastAPI:
    """Create and configure the FastAPI application."""
    if settings is None:
        settings = get_settings()

    # Setup logging first
    setup_logging(settings)

    # Setup tracing
    setup_tracing(settings)

    application = FastAPI(
        # ... existing config ...
    )

    # ... register middleware and routes ...

    # Instrument application for tracing (at the end)
    instrument_app(application, settings)

    return application
```

### Step 4: Create Tests

Create `tests/unit/core/test_observability_simplified.py`:

```python
"""Tests for simplified observability implementation."""

import os
from unittest.mock import Mock, patch

import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter

from src.core.config import ObservabilityConfig, Settings
from src.core.context import RequestContext
from src.core.observability import (
    add_correlation_id_to_span,
    add_span_attributes,
    get_span_exporter,
    get_tracer,
    setup_tracing,
    trace_operation,
)


class TestExporterSelection:
    """Test exporter selection logic."""

    def test_console_exporter(self):
        """Test console exporter for development."""
        settings = Settings(
            observability_config=ObservabilityConfig(
                enable_tracing=True,
                exporter_type="console",
            )
        )

        exporter = get_span_exporter(settings)
        assert isinstance(exporter, ConsoleSpanExporter)

    def test_none_exporter(self):
        """Test explicitly disabled tracing."""
        settings = Settings(
            observability_config=ObservabilityConfig(
                enable_tracing=True,
                exporter_type="none",
            )
        )

        exporter = get_span_exporter(settings)
        assert exporter is None

    @patch("src.core.observability.OTLPSpanExporter")
    def test_otlp_exporter(self, mock_otlp):
        """Test OTLP exporter configuration."""
        settings = Settings(
            observability_config=ObservabilityConfig(
                enable_tracing=True,
                exporter_type="otlp",
                exporter_endpoint="http://jaeger:4317",
            )
        )

        exporter = get_span_exporter(settings)

        mock_otlp.assert_called_once_with(
            endpoint="http://jaeger:4317",
            insecure=True,  # Development environment
        )

    def test_gcp_exporter_without_package(self):
        """Test GCP exporter when package not installed."""
        settings = Settings(
            observability_config=ObservabilityConfig(
                enable_tracing=True,
                exporter_type="gcp",
                gcp_project_id="test-project",
            )
        )

        # Simulate import error
        with patch("builtins.__import__", side_effect=ImportError):
            exporter = get_span_exporter(settings)
            assert exporter is None


class TestTracingSetup:
    """Test tracing setup."""

    def test_tracing_disabled(self):
        """Test tracing can be disabled."""
        settings = Settings(
            observability_config=ObservabilityConfig(
                enable_tracing=False,
            )
        )

        # Clear any existing provider
        trace.set_tracer_provider(None)

        setup_tracing(settings)

        # Should not set up a provider
        provider = trace.get_tracer_provider()
        assert not isinstance(provider, TracerProvider)

    def test_tracing_with_console_exporter(self):
        """Test tracing setup with console exporter."""
        settings = Settings(
            app_name="test-app",
            app_version="1.0.0",
            environment="development",
            observability_config=ObservabilityConfig(
                enable_tracing=True,
                exporter_type="console",
                trace_sample_rate=0.5,
            )
        )

        setup_tracing(settings)

        # Verify provider is set
        provider = trace.get_tracer_provider()
        assert isinstance(provider, TracerProvider)

    def test_get_tracer(self):
        """Test getting a tracer instance."""
        tracer = get_tracer("test.module")
        assert hasattr(tracer, "start_span")


class TestSpanOperations:
    """Test span operations and utilities."""

    def test_add_correlation_id_to_span(self):
        """Test adding correlation ID to span."""
        # Create mock span
        mock_span = Mock()
        mock_request = Mock()
        mock_request.headers = {"X-Request-ID": "req-123"}

        # Set correlation ID in context
        RequestContext.set_correlation_id("corr-456")

        add_correlation_id_to_span(mock_span, mock_request)

        # Verify attributes were set
        mock_span.set_attribute.assert_any_call("correlation_id", "corr-456")
        mock_span.set_attribute.assert_any_call("request_id", "req-123")

    def test_add_span_attributes(self):
        """Test adding custom span attributes."""
        mock_span = Mock()
        mock_span.is_recording.return_value = True

        with patch("opentelemetry.trace.get_current_span", return_value=mock_span):
            add_span_attributes(
                user_id=123,
                action="login",
                success=True,
            )

        # All values should be converted to strings
        mock_span.set_attribute.assert_any_call("user_id", "123")
        mock_span.set_attribute.assert_any_call("action", "login")
        mock_span.set_attribute.assert_any_call("success", "True")

    def test_trace_operation_context_manager(self):
        """Test trace_operation context manager."""
        # Setup basic tracing
        settings = Settings(
            observability_config=ObservabilityConfig(
                enable_tracing=True,
                exporter_type="console",
            )
        )
        setup_tracing(settings)

        # Set correlation ID
        RequestContext.set_correlation_id("test-correlation")

        # Use trace_operation
        with trace_operation("test_operation", operation_type="unit_test"):
            # Operation code would go here
            pass

        # Verify span was created (basic check)
        # More detailed verification would require capturing spans


class TestInstrumentation:
    """Test application instrumentation."""

    @patch("src.core.observability.FastAPIInstrumentor")
    @patch("src.core.observability.SQLAlchemyInstrumentor")
    def test_instrument_app(self, mock_sqlalchemy, mock_fastapi):
        """Test FastAPI and SQLAlchemy instrumentation."""
        from fastapi import FastAPI

        app = FastAPI()
        settings = Settings(
            observability_config=ObservabilityConfig(
                enable_tracing=True,
            )
        )

        from src.core.observability import instrument_app

        instrument_app(app, settings)

        # Verify instrumentors were called
        mock_fastapi.instrument_app.assert_called_once()
        mock_sqlalchemy.return_value.instrument.assert_called_once()

    def test_instrument_app_disabled(self):
        """Test instrumentation when tracing is disabled."""
        from fastapi import FastAPI

        app = FastAPI()
        settings = Settings(
            observability_config=ObservabilityConfig(
                enable_tracing=False,
            )
        )

        # Should not crash when disabled
        from src.core.observability import instrument_app
        instrument_app(app, settings)


class TestCloudAgnostic:
    """Test cloud-agnostic functionality."""

    def test_no_cloud_dependencies_for_console(self):
        """Test console exporter requires no cloud dependencies."""
        settings = Settings(
            observability_config=ObservabilityConfig(
                enable_tracing=True,
                exporter_type="console",
            )
        )

        # Should work without any cloud authentication
        setup_tracing(settings)

        # Verify we can create spans
        tracer = get_tracer("test")
        with tracer.start_as_current_span("test_span") as span:
            span.set_attribute("test", "value")

    def test_environment_based_configuration(self, monkeypatch):
        """Test configuration via environment variables."""
        monkeypatch.setenv("OBSERVABILITY_CONFIG__EXPORTER_TYPE", "otlp")
        monkeypatch.setenv("OBSERVABILITY_CONFIG__EXPORTER_ENDPOINT", "http://tempo:4317")
        monkeypatch.setenv("OBSERVABILITY_CONFIG__TRACE_SAMPLE_RATE", "0.1")

        settings = Settings()

        assert settings.observability_config.exporter_type == "otlp"
        assert settings.observability_config.exporter_endpoint == "http://tempo:4317"
        assert settings.observability_config.trace_sample_rate == 0.1
```

### Step 5: Update .env.example

Add the new observability configuration section:
```bash
# ==========================================
# Observability Configuration (Added in Phase 5)
# ==========================================

# Enable distributed tracing
OBSERVABILITY_CONFIG__ENABLE_TRACING=true

# Trace exporter type
# Options: console (dev), gcp (Google Cloud Trace), aws (X-Ray), otlp (Jaeger/Zipkin), none
# Leave empty for auto-detection based on environment
OBSERVABILITY_CONFIG__EXPORTER_TYPE=console

# OTLP endpoint (for otlp or aws exporters)
# OBSERVABILITY_CONFIG__EXPORTER_ENDPOINT=http://localhost:4317

# GCP Project ID (only for gcp exporter)
# OBSERVABILITY_CONFIG__GCP_PROJECT_ID=your-project-id

# Trace sampling rate (0.0 to 1.0)
# 1.0 = 100% (development), 0.1 = 10% (production)
OBSERVABILITY_CONFIG__TRACE_SAMPLE_RATE=1.0

# ==========================================
# Environment-Specific Tracing Examples
# ==========================================

# Local Development with console output
# OBSERVABILITY_CONFIG__EXPORTER_TYPE=console
# OBSERVABILITY_CONFIG__TRACE_SAMPLE_RATE=1.0

# GCP Production
# OBSERVABILITY_CONFIG__EXPORTER_TYPE=gcp
# OBSERVABILITY_CONFIG__GCP_PROJECT_ID=your-project-id
# OBSERVABILITY_CONFIG__TRACE_SAMPLE_RATE=0.1

# AWS Production
# OBSERVABILITY_CONFIG__EXPORTER_TYPE=aws
# OBSERVABILITY_CONFIG__EXPORTER_ENDPOINT=https://xray.region.amazonaws.com
# OBSERVABILITY_CONFIG__TRACE_SAMPLE_RATE=0.1

# Self-hosted with Jaeger
# OBSERVABILITY_CONFIG__EXPORTER_TYPE=otlp
# OBSERVABILITY_CONFIG__EXPORTER_ENDPOINT=http://jaeger:4317
# OBSERVABILITY_CONFIG__TRACE_SAMPLE_RATE=0.5
```

### Step 6: Update Dependencies (Optional)

The core OpenTelemetry packages should already be in `pyproject.toml` from the original setup. For cloud-specific exporters, make them optional:

```toml
# In pyproject.toml

# Core dependencies (keep existing)
dependencies = [
    # ... other dependencies ...
    "opentelemetry-api>=1.34.1",
    "opentelemetry-sdk>=1.34.1",
    "opentelemetry-instrumentation-fastapi>=0.55b1",
    "opentelemetry-instrumentation-sqlalchemy>=0.55b1",
    "opentelemetry-exporter-otlp>=1.34.1",  # For OTLP/AWS
]

[project.optional-dependencies]
# GCP-specific dependencies
gcp = [
    "opentelemetry-exporter-gcp-trace>=1.9.0",
]
```

## Validation Checklist

- [ ] Observability module created (~100 lines)
- [ ] Pluggable exporter system implemented
- [ ] Console exporter works for local development
- [ ] No cloud dependencies required for local setup
- [ ] FastAPI instrumentation configured
- [ ] SQLAlchemy instrumentation configured
- [ ] Correlation IDs propagate to traces
- [ ] Custom trace operations supported
- [ ] **.env.example updated with observability settings**
- [ ] **Clear examples for each cloud provider**
- [ ] Tests cover all exporters
- [ ] `make lint` passes
- [ ] `make type-check` passes

## Expected Results

After Phase 5:
- Distributed tracing with OpenTelemetry
- Works locally without cloud services
- Easy switching between trace backends
- Standard instrumentation for HTTP and SQL
- ~25 tests for observability
- 86% code reduction (100 lines vs 733)

## Testing Tracing Locally

```bash
# Start with console exporter
OBSERVABILITY_CONFIG__EXPORTER_TYPE=console make dev

# Make some requests
curl http://localhost:8000/
curl http://localhost:8000/health

# Check console output for trace information
# You'll see span details printed to stdout

# Test with Jaeger locally
docker run -d --name jaeger \
  -p 16686:16686 \
  -p 4317:4317 \
  jaegertracing/all-in-one:latest

# Use OTLP exporter
OBSERVABILITY_CONFIG__EXPORTER_TYPE=otlp \
OBSERVABILITY_CONFIG__EXPORTER_ENDPOINT=http://localhost:4317 \
make dev

# View traces at http://localhost:16686
```

## Cloud Migration Examples

### Deploy to GCP
```yaml
# .env.production.gcp
OBSERVABILITY_CONFIG__EXPORTER_TYPE=gcp
OBSERVABILITY_CONFIG__GCP_PROJECT_ID=your-project-id
OBSERVABILITY_CONFIG__TRACE_SAMPLE_RATE=0.1
```

### Deploy to AWS
```yaml
# .env.production.aws
OBSERVABILITY_CONFIG__EXPORTER_TYPE=aws
OBSERVABILITY_CONFIG__EXPORTER_ENDPOINT=https://xray.us-east-1.amazonaws.com
OBSERVABILITY_CONFIG__TRACE_SAMPLE_RATE=0.1
```

### Deploy to Kubernetes with Jaeger
```yaml
# .env.production.k8s
OBSERVABILITY_CONFIG__EXPORTER_TYPE=otlp
OBSERVABILITY_CONFIG__EXPORTER_ENDPOINT=http://jaeger-collector.monitoring:4317
OBSERVABILITY_CONFIG__TRACE_SAMPLE_RATE=0.5
```

## Notes for Next Phases

- Phase 6 will integrate all components
- Current setup is vendor-neutral
- Sampling rate prevents overwhelming trace storage
- Keep instrumentation lightweight

## Common Usage Patterns

```python
# Manual span creation
from src.core.observability import trace_operation

async def process_payment(amount: float):
    with trace_operation("payment_processing", amount=amount, currency="USD"):
        # Process payment
        result = await payment_gateway.charge(amount)

        # Add result to span
        add_span_attributes(
            success=result.success,
            transaction_id=result.transaction_id,
        )

        return result

# Using tracer directly
from src.core.observability import get_tracer

tracer = get_tracer(__name__)

async def complex_operation():
    with tracer.start_as_current_span("complex_operation") as span:
        span.set_attribute("operation.type", "batch_processing")

        # Nested spans
        with tracer.start_as_current_span("step_1"):
            await step_1()

        with tracer.start_as_current_span("step_2"):
            await step_2()
```

## Troubleshooting

### No Traces Appearing
- Check `enable_tracing` is True
- Verify exporter configuration
- Check sample rate (1.0 = 100%)
- Look for errors in logs during startup

### Missing Correlation IDs
- Ensure RequestContextMiddleware runs first
- Verify correlation ID is set before creating spans
- Check span attributes in trace viewer

### Performance Impact
- Reduce sample rate in production
- Use batch span processor (default)
- Avoid creating too many spans in loops
