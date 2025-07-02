"""Observability configuration using OpenTelemetry with pluggable exporters.

This module provides vendor-neutral distributed tracing that works with:
- Local development (console/file output)
- Cloud providers (GCP Cloud Trace, AWS X-Ray)
- Self-hosted (Jaeger, Zipkin via OTLP)
"""

from __future__ import annotations

import importlib
import os
from contextlib import contextmanager
from functools import lru_cache
from typing import TYPE_CHECKING, Any, Final

from loguru import logger
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import ReadableSpan, TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    SpanExporter,
    SpanExportResult,
)
from opentelemetry.sdk.trace.sampling import TraceIdRatioBased

from src.core.context import RequestContext

if TYPE_CHECKING:
    from collections.abc import Generator, Sequence

    from fastapi import FastAPI

    from src.core.config import Settings

# Constants
SERVICE_NAME_KEY: Final[str] = "service.name"
SERVICE_VERSION_KEY: Final[str] = "service.version"
ENVIRONMENT_KEY: Final[str] = "deployment.environment"


class LoguruSpanExporter(SpanExporter):
    """Custom span exporter that sends traces through Loguru logger."""

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        """Export spans through Loguru logger instead of stdout.

        This ensures traces follow our logging configuration and don't
        pollute the console with raw JSON.
        """
        for span in spans:
            # Extract key span information
            span_context = span.get_span_context()
            if not span_context:
                continue

            attributes = dict(span.attributes or {})

            # Add correlation ID if available
            correlation_id = attributes.get(
                "correlation_id", RequestContext.get_correlation_id()
            )

            # Calculate duration if both times are available
            duration_ms = None
            if span.end_time and span.start_time:
                duration_ms = (span.end_time - span.start_time) // 1_000_000

            # Skip noisy internal spans in development
            if span.name in ["connect", "http send", "http receive", "cursor.execute"]:
                continue

            # Create a structured log entry for the span
            logger.bind(
                trace_id=f"0x{span_context.trace_id:032x}",
                span_id=f"0x{span_context.span_id:016x}",
                correlation_id=correlation_id,
                span_name=span.name,
                span_kind=span.kind.name,
                duration_ms=duration_ms,
                attributes=attributes,
                status=span.status.status_code.name,
            ).debug("Trace span completed: {}", span.name)

        return SpanExportResult.SUCCESS


def get_span_exporter(settings: Settings) -> SpanExporter | None:
    """Get the appropriate span exporter based on configuration.

    This function returns the correct exporter for the configured
    environment without requiring cloud-specific imports unless needed.

    Args:
        settings: Application settings.

    Returns:
        SpanExporter | None: Configured exporter or None if disabled.
    """
    exporter_type = settings.observability_config.exporter_type.lower()

    if exporter_type == "console":
        logger.info("Using Loguru span exporter for development")
        return LoguruSpanExporter()

    if exporter_type == "gcp":
        return _get_gcp_exporter(settings)

    if exporter_type in ("aws", "otlp"):
        return _get_otlp_exporter(settings, exporter_type)

    if exporter_type == "none":
        logger.info("Tracing explicitly disabled")
        return None

    logger.warning(f"Unknown exporter type: {exporter_type}, disabling tracing")
    return None


def _get_gcp_exporter(settings: Settings) -> SpanExporter | None:
    """Get GCP Cloud Trace exporter."""
    try:
        # Dynamic import to avoid requiring cloud dependencies
        module = importlib.import_module("opentelemetry.exporter.cloud_trace")

        project_id = settings.observability_config.gcp_project_id
        if not project_id:
            project_id = os.getenv("GOOGLE_CLOUD_PROJECT")

        if not project_id:
            logger.warning("GCP project ID not configured, disabling tracing")
            return None

        logger.info(f"Using GCP Cloud Trace exporter for project {project_id}")
        # Access the class directly from module
        exporter_class = module.CloudTraceSpanExporter
        exporter: SpanExporter = exporter_class(project_id=project_id)

    except ImportError:
        logger.error(
            "GCP exporter requested but opentelemetry-exporter-gcp-trace "
            "not installed. Install with: uv add opentelemetry-exporter-gcp-trace"
        )
        return None
    else:
        return exporter


def _get_otlp_exporter(settings: Settings, exporter_type: str) -> SpanExporter:
    """Get OTLP-based exporter (AWS X-Ray or generic OTLP)."""
    endpoint = (
        settings.observability_config.exporter_endpoint or "http://localhost:4317"
    )

    if exporter_type == "aws":
        logger.info(f"Using AWS X-Ray exporter via OTLP at {endpoint}")
    else:
        logger.info(f"Using OTLP exporter at {endpoint}")

    return OTLPSpanExporter(
        endpoint=endpoint,
        insecure=settings.environment == "development",
    )


@lru_cache(maxsize=1)
def get_tracer(name: str) -> trace.Tracer:
    """Get a tracer instance for the given component.

    Args:
        name: Component name, typically __name__.

    Returns:
        trace.Tracer: OpenTelemetry tracer instance.
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
    resource = Resource.create(
        {
            SERVICE_NAME_KEY: settings.app_name,
            SERVICE_VERSION_KEY: settings.app_version,
            ENVIRONMENT_KEY: settings.environment,
        }
    )

    # Create tracer provider with sampling
    tracer_provider = TracerProvider(
        resource=resource,
        sampler=TraceIdRatioBased(settings.observability_config.trace_sample_rate),
    )

    # Get the appropriate exporter
    exporter = get_span_exporter(settings)
    if exporter:
        tracer_provider.add_span_processor(BatchSpanProcessor(exporter))

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


def add_correlation_id_to_span(span: trace.Span, scope: dict[str, Any]) -> None:
    """Add correlation ID from context to the current span.

    This is used as a server_request_hook for FastAPI instrumentation
    to ensure correlation IDs are included in traces.

    Args:
        span: The current span.
        scope: ASGI scope dict containing request information.
    """
    if correlation_id := RequestContext.get_correlation_id():
        span.set_attribute("correlation_id", correlation_id)

    # Also add request ID if available from headers
    headers = dict(scope.get("headers", []))
    if request_id := headers.get(b"x-request-id", b"").decode("utf-8"):
        span.set_attribute("request_id", request_id)


def add_span_attributes(**attributes: str | int | float | bool) -> None:
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


@contextmanager
def trace_operation(
    name: str, **attributes: str | int | float | bool
) -> Generator[trace.Span]:
    """Context manager for tracing a custom operation.

    Args:
        name: Operation name for the span.
        **attributes: Initial attributes for the span.

    Yields:
        Generator[trace.Span]: The created span for the operation.

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

    with trace.use_span(span, end_on_exit=True):
        yield span
