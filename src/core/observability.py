"""Observability and tracing setup for the application.

This module configures OpenTelemetry with GCP Cloud Trace integration
and provides utilities for distributed tracing.
"""

import asyncio
import gc
import os
import resource
from typing import Any

import psutil
from opentelemetry import metrics, trace
from opentelemetry.exporter.cloud_monitoring import (
    CloudMonitoringMetricsExporter,
)
from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
from opentelemetry.metrics import (
    CallbackOptions,
    Counter,
    Histogram,
    Meter,
    Observation,
)
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import ReadableSpan, TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.sampling import TraceIdRatioBased
from opentelemetry.trace import Span, Status, StatusCode, Tracer
from sqlalchemy.pool import Pool

from src.core.config import get_settings
from src.core.context import RequestContext
from src.core.exceptions import Severity, TributumError
from src.core.logging import get_logger

logger = get_logger(__name__)

# Module-level meter instance
_meter: Meter | None = None

# Metric instruments (initialized in setup_observability)
request_counter: Counter | None = None
request_duration_histogram: Histogram | None = None
error_counter: Counter | None = None
db_query_counter: Counter | None = None
db_query_duration_histogram: Histogram | None = None


class ErrorTrackingSpanProcessor(BatchSpanProcessor):
    """Custom span processor that enriches spans with TributumError context.

    Note: Since spans are read-only in on_end, this processor analyzes
    the span but doesn't modify it. The TributumError context should be
    added when recording the exception using record_tributum_error_in_span.
    """

    def on_end(self, span: ReadableSpan) -> None:
        """Process span on end to analyze error context.

        Args:
            span: The span that is ending
        """
        # In on_end, spans are read-only (ReadableSpan), so we can only
        # analyze them, not modify them. The actual context enrichment
        # happens in record_tributum_error_in_span when the error occurs.

        # Call parent processor
        super().on_end(span)


def setup_observability() -> None:
    """Configure OpenTelemetry tracing and metrics with GCP integration.

    This function:
    - Sets up trace provider with configured sampling
    - Configures GCP Cloud Trace exporter if enabled
    - Sets up meter provider with GCP Cloud Monitoring exporter
    - Creates metric instruments for the application
    - Integrates with TributumError context capture
    """
    global _meter, request_counter, request_duration_histogram  # noqa: PLW0603
    global error_counter, db_query_counter, db_query_duration_histogram  # noqa: PLW0603

    settings = get_settings()
    obs_config = settings.observability_config

    # Create resource with service information (shared by tracing and metrics)
    service_resource = Resource.create(
        {
            "service.name": obs_config.service_name,
            "service.version": settings.app_version,
            "deployment.environment": settings.environment,
        }
    )

    # Setup tracing if enabled
    if obs_config.enable_tracing:
        logger.info(
            "Setting up tracing",
            service_name=obs_config.service_name,
            sample_rate=obs_config.trace_sample_rate,
        )

        # Create tracer provider with sampling
        sampler = TraceIdRatioBased(obs_config.trace_sample_rate)
        provider = TracerProvider(resource=service_resource, sampler=sampler)

        # Add GCP Cloud Trace exporter if project ID is configured
        if obs_config.gcp_project_id:
            try:
                cloud_trace_exporter = CloudTraceSpanExporter(
                    project_id=obs_config.gcp_project_id
                )
                # Use our custom processor that adds error context
                provider.add_span_processor(
                    ErrorTrackingSpanProcessor(cloud_trace_exporter)
                )
                logger.info(
                    "GCP Cloud Trace exporter configured",
                    project_id=obs_config.gcp_project_id,
                )
            except (ValueError, RuntimeError) as e:
                # Log the full exception traceback
                logger.exception(
                    "Failed to configure GCP Cloud Trace exporter",
                    error=str(e),
                    project_id=obs_config.gcp_project_id,
                )
        else:
            logger.warning("GCP project ID not configured, traces will not be exported")

        # Set the global tracer provider
        trace.set_tracer_provider(provider)
        logger.info("Tracing setup complete")
    else:
        logger.info("Tracing is disabled")

    # Setup metrics if enabled
    if obs_config.enable_metrics:
        logger.info(
            "Setting up metrics",
            service_name=obs_config.service_name,
            export_interval_ms=obs_config.metrics_export_interval_ms,
        )

        # Create metric readers and exporters
        readers = []

        if obs_config.gcp_project_id:
            try:
                # Create GCP Cloud Monitoring exporter
                cloud_monitoring_exporter = CloudMonitoringMetricsExporter(
                    project_id=obs_config.gcp_project_id
                )
                metric_reader = PeriodicExportingMetricReader(
                    exporter=cloud_monitoring_exporter,
                    export_interval_millis=obs_config.metrics_export_interval_ms,
                )
                readers.append(metric_reader)
                logger.info(
                    "GCP Cloud Monitoring exporter configured",
                    project_id=obs_config.gcp_project_id,
                )
            except (ValueError, RuntimeError) as e:
                logger.exception(
                    "Failed to configure GCP Cloud Monitoring exporter",
                    error=str(e),
                    project_id=obs_config.gcp_project_id,
                )
        else:
            logger.warning(
                "GCP project ID not configured, metrics will not be exported"
            )

        # Create meter provider with readers
        meter_provider = MeterProvider(
            resource=service_resource,
            metric_readers=readers,
        )

        # Set the global meter provider
        metrics.set_meter_provider(meter_provider)

        # Get a meter for creating instruments
        _meter = meter_provider.get_meter(
            name="tributum",
            version=settings.app_version,
        )

        # Create metric instruments
        request_counter = _meter.create_counter(
            name="http.server.request.count",
            unit="1",
            description="Total number of HTTP requests",
        )

        request_duration_histogram = _meter.create_histogram(
            name="http.server.request.duration",
            unit="ms",
            description="HTTP request duration in milliseconds",
        )

        error_counter = _meter.create_counter(
            name="http.server.error.count",
            unit="1",
            description="Total number of HTTP errors",
        )

        db_query_counter = _meter.create_counter(
            name="db.query.count",
            unit="1",
            description="Total number of database queries",
        )

        db_query_duration_histogram = _meter.create_histogram(
            name="db.query.duration",
            unit="ms",
            description="Database query duration in milliseconds",
        )

        # Register system metrics collectors if enabled
        if obs_config.enable_system_metrics:
            _register_system_metrics(_meter)

        logger.info("Metrics setup complete")
    else:
        logger.info("Metrics are disabled")


def setup_tracing() -> None:
    """Configure OpenTelemetry tracing with GCP Cloud Trace integration.

    This is a compatibility wrapper that calls setup_observability().
    """
    setup_observability()


def _register_system_metrics(meter: Meter) -> None:
    """Register system metrics collectors.

    Args:
        meter: The meter to use for creating observable instruments
    """
    # CPU percentage gauge
    meter.create_observable_gauge(
        name="process.cpu.utilization",
        callbacks=[_get_cpu_percentage],
        unit="1",
        description="Process CPU utilization percentage (0-100)",
    )

    # Memory usage gauge
    meter.create_observable_gauge(
        name="process.memory.usage",
        callbacks=[_get_memory_usage],
        unit="By",
        description="Process memory usage in bytes (RSS)",
    )

    # Active asyncio tasks gauge
    meter.create_observable_gauge(
        name="process.asyncio.tasks.active",
        callbacks=[_get_active_tasks_count],
        unit="1",
        description="Number of active asyncio tasks",
    )

    # Garbage collection stats
    meter.create_observable_gauge(
        name="process.gc.collections",
        callbacks=[_get_gc_collections],
        unit="1",
        description="Number of garbage collections by generation",
    )


def _get_cpu_percentage(_: CallbackOptions) -> list[Observation]:
    """Get current process CPU percentage.

    Returns:
        list[Observation]: List of observations
    """
    try:
        # Get current process
        process = psutil.Process(os.getpid())
        # Get CPU percentage (will be 0 on first call)
        cpu_percent = process.cpu_percent(interval=None)
        return [Observation(cpu_percent, {})]
    except (psutil.NoSuchProcess, psutil.AccessDenied, AttributeError):
        logger.debug("Failed to get CPU percentage")
        return [Observation(0.0, {})]


def _get_memory_usage(_: CallbackOptions) -> list[Observation]:
    """Get current process memory usage (RSS).

    Returns:
        list[Observation]: List of observations
    """
    try:
        # Get current process
        process = psutil.Process(os.getpid())
        # Get memory info
        memory_info = process.memory_info()
        return [Observation(memory_info.rss, {})]
    except (psutil.NoSuchProcess, psutil.AccessDenied, AttributeError):
        # Fallback to resource module
        usage = resource.getrusage(resource.RUSAGE_SELF)
        # Convert from KB to bytes
        return [Observation(usage.ru_maxrss * 1024, {})]


def _get_active_tasks_count(_: CallbackOptions) -> list[Observation]:
    """Get number of active asyncio tasks.

    Returns:
        list[Observation]: List of observations
    """
    try:
        tasks = asyncio.all_tasks()
        return [Observation(len(tasks), {})]
    except RuntimeError:
        # Not in asyncio context
        return [Observation(0, {})]


def _get_gc_collections(_: CallbackOptions) -> list[Observation]:
    """Get garbage collection statistics by generation.

    Returns:
        list[Observation]: List of observations
    """
    results = []
    for generation in range(gc.get_count().__len__()):
        collections = gc.get_stats()[generation].get("collections", 0)
        results.append(Observation(collections, {"generation": str(generation)}))
    return results


def get_database_pool_metrics(pool: Pool | None) -> dict[str, int]:
    """Get database connection pool metrics.

    Args:
        pool: SQLAlchemy connection pool instance

    Returns:
        dict[str, int]: Dictionary with pool metrics
    """
    if not pool:
        return {
            "size": 0,
            "checked_in": 0,
            "checked_out": 0,
            "overflow": 0,
            "total": 0,
        }

    try:
        return {
            "size": pool.size(),  # type: ignore[attr-defined]
            "checked_in": pool.checked_in_connections,  # type: ignore[attr-defined]
            "checked_out": pool.checked_out_connections,  # type: ignore[attr-defined]
            "overflow": pool.overflow,  # type: ignore[attr-defined]
            "total": pool.total,  # type: ignore[attr-defined]
        }
    except AttributeError:
        logger.debug("Failed to get pool metrics")
        return {
            "size": 0,
            "checked_in": 0,
            "checked_out": 0,
            "overflow": 0,
            "total": 0,
        }


def get_meter() -> Meter | None:
    """Get the global meter instance.

    Returns:
        Meter | None: The meter instance if metrics are enabled, None otherwise
    """
    return _meter


def get_tracer(name: str) -> Tracer:
    """Get a tracer instance for the given component name.

    Args:
        name: The name of the component requesting the tracer

    Returns:
        Tracer: A configured tracer instance
    """
    return trace.get_tracer(name)


def record_tributum_error_in_span(span: Span, error: TributumError) -> None:
    """Record a TributumError in the current span with full context.

    This enriches the span with:
    - Error severity as span status
    - Error context as span attributes
    - Stack trace information
    - Fingerprint for error grouping

    Args:
        span: The current span
        error: The TributumError to record
    """
    # Map severity to span status
    if error.severity in (Severity.CRITICAL, Severity.HIGH):
        span.set_status(Status(StatusCode.ERROR, error.message))
    else:
        # MEDIUM and below don't fail the span
        span.set_status(Status(StatusCode.OK))

    # Add error attributes
    span.set_attribute("tributum.error_code", error.error_code)
    span.set_attribute("tributum.severity", error.severity.value)
    span.set_attribute("tributum.fingerprint", error.fingerprint)

    # Add error context as span attributes
    if error.context:
        for key, value in error.context.items():
            # Prefix with tributum.context to avoid collisions
            attr_key = f"tributum.context.{key}"
            # OpenTelemetry only supports certain types
            if isinstance(value, (str, bool, int, float)):
                span.set_attribute(attr_key, value)
            else:
                span.set_attribute(attr_key, str(value))

    # Record the exception
    span.record_exception(
        error,
        attributes={
            "tributum.error_code": error.error_code,
            "tributum.severity": error.severity.value,
            "tributum.fingerprint": error.fingerprint,
        },
    )


def add_correlation_id_to_span(span: Span, request_scope: dict[str, Any]) -> None:
    """Add correlation ID to the current span if available.

    This function is called by the FastAPI instrumentor for each request
    to enrich spans with correlation IDs.

    Args:
        span: The current OpenTelemetry span
        request_scope: The ASGI request scope
    """
    # Add request path as span attribute
    if "path" in request_scope:
        span.set_attribute("http.target", request_scope["path"])

    # Add correlation ID if available
    correlation_id = RequestContext.get_correlation_id()
    if correlation_id:
        span.set_attribute("correlation_id", correlation_id)
        span.set_attribute("tributum.correlation_id", correlation_id)
