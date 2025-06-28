"""Observability and tracing setup for the application.

This module configures OpenTelemetry with GCP Cloud Trace integration
and provides utilities for distributed tracing.
"""

import asyncio
import gc
import os
import resource
import time
from collections.abc import Mapping, Sequence
from typing import Any

import psutil
from opentelemetry import metrics, trace
from opentelemetry.context import Context
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
from opentelemetry.sdk.trace.sampling import (
    ALWAYS_ON,
    ParentBased,
    Sampler,
    SamplingResult,
    TraceIdRatioBased,
)
from opentelemetry.trace import Link, Span, SpanKind, Status, StatusCode, Tracer
from opentelemetry.trace.span import TraceState
from sqlalchemy.pool import AsyncAdaptedQueuePool, Pool, QueuePool

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


class CompositeSampler(Sampler):
    """Composite sampler with different strategies based on request attributes.

    This sampler:
    - Always samples errors and slow requests
    - Applies different sampling rates based on endpoint priority
    - Respects upstream sampling decisions

    Args:
        base_sample_rate: Default sampling rate (0.0 to 1.0)
    """

    def __init__(self, base_sample_rate: float) -> None:
        self.base_sample_rate = base_sample_rate
        # Create samplers for different scenarios
        self.always_on = ALWAYS_ON
        self.base_sampler = TraceIdRatioBased(base_sample_rate)
        # Different rates for different priorities
        self.high_priority_sampler = TraceIdRatioBased(min(base_sample_rate * 2, 1.0))
        self.low_priority_sampler = TraceIdRatioBased(base_sample_rate * 0.1)

    def should_sample(
        self,
        parent_context: Context | None,
        trace_id: int,
        name: str,
        kind: SpanKind | None = None,
        attributes: Mapping[str, Any] | None = None,
        links: Sequence[Link] | None = None,
        trace_state: TraceState | None = None,
    ) -> SamplingResult:
        """Determine if a span should be sampled based on attributes.

        Args:
            parent_context: Parent span context
            trace_id: Unique trace identifier
            name: Span name
            kind: Span kind (SERVER, CLIENT, etc.)
            attributes: Span attributes including our custom ones
            links: Span links
            trace_state: Trace state from parent context

        Returns:
            SamplingResult: Sampling decision
        """
        if attributes is None:
            attributes = {}

        # Fix kind default
        if kind is None:
            kind = SpanKind.INTERNAL

        # Always sample if there's an error status
        status_code = attributes.get("http.status_code", "")
        if isinstance(status_code, str) and status_code.startswith(("4", "5")):
            return self.always_on.should_sample(
                parent_context, trace_id, name, kind, attributes, links, trace_state
            )

        # Always sample slow requests (will be set by middleware)
        if attributes.get("tributum.slow_request", False):
            return self.always_on.should_sample(
                parent_context, trace_id, name, kind, attributes, links, trace_state
            )

        # Apply different sampling rates based on priority
        priority = attributes.get("tributum.request.priority", "medium")
        if priority == "high":
            return self.high_priority_sampler.should_sample(
                parent_context, trace_id, name, kind, attributes, links, trace_state
            )
        if priority == "low":
            return self.low_priority_sampler.should_sample(
                parent_context, trace_id, name, kind, attributes, links, trace_state
            )

        # Default sampling
        return self.base_sampler.should_sample(
            parent_context, trace_id, name, kind, attributes, links, trace_state
        )

    def get_description(self) -> str:
        """Get sampler description.

        Returns:
            str: Description of the sampling strategy
        """
        return (
            f"CompositeSampler(base_rate={self.base_sample_rate}, "
            f"high_priority_rate={min(self.base_sample_rate * 2, 1.0)}, "
            f"low_priority_rate={self.base_sample_rate * 0.1}, "
            f"always_sample_errors=True)"
        )


def _create_composite_sampler(base_sample_rate: float) -> ParentBased:
    """Create a composite sampler with parent-based wrapper.

    The parent-based wrapper ensures we respect upstream sampling decisions
    while applying our custom logic for root spans.

    Args:
        base_sample_rate: Base sampling rate for normal requests

    Returns:
        ParentBased: Composite sampler wrapped in parent-based logic
    """
    composite = CompositeSampler(base_sample_rate)
    # Wrap in ParentBased to respect upstream decisions
    return ParentBased(root=composite)


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

        # Create composite sampler with advanced rules
        sampler = _create_composite_sampler(obs_config.trace_sample_rate)
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


def get_database_pool_metrics(
    pool: AsyncAdaptedQueuePool | QueuePool | Pool | None,
) -> dict[str, int]:
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
        # All our pool types (AsyncAdaptedQueuePool and QueuePool) have these methods
        if isinstance(pool, (AsyncAdaptedQueuePool, QueuePool)):
            # These pool types have the methods we need
            size = pool.size()
            overflow = pool.overflow()
            checked_out = pool.checkedout()
            checked_in = pool.checkedin()
            total = size + overflow
        else:
            # For generic Pool type, we can't guarantee these methods exist
            # So we return zeros and log a debug message
            logger.debug(
                "Pool type does not support detailed metrics",
                pool_type=type(pool).__name__,
            )
            return {
                "size": 0,
                "checked_in": 0,
                "checked_out": 0,
                "overflow": 0,
                "total": 0,
            }
    except (AttributeError, TypeError) as e:
        logger.debug(
            "Failed to get pool metrics", error=str(e), pool_type=type(pool).__name__
        )
        return {
            "size": 0,
            "checked_in": 0,
            "checked_out": 0,
            "overflow": 0,
            "total": 0,
        }
    else:
        return {
            "size": size,
            "checked_in": checked_in,
            "checked_out": checked_out,
            "overflow": overflow,
            "total": total,
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
    """Add correlation ID and enhanced metadata to the current span.

    This function is called by the FastAPI instrumentor for each request
    to enrich spans with correlation IDs and additional context for better
    observability and analysis in Cloud Trace.

    Args:
        span: The current OpenTelemetry span
        request_scope: The ASGI request scope
    """
    # Add basic request attributes
    _add_basic_request_attributes(span, request_scope)

    # Add correlation ID if available
    correlation_id = RequestContext.get_correlation_id()
    if correlation_id:
        span.set_attribute("correlation_id", correlation_id)
        span.set_attribute("tributum.correlation_id", correlation_id)

    # Add header-based attributes
    _add_header_attributes(span, request_scope)

    # Add user and tenant context (placeholders for now)
    # TODO: Extract from JWT/session when auth is implemented
    span.set_attribute("tributum.user.id", "anonymous")
    # TODO: Extract from request context when multi-tenancy is implemented
    span.set_attribute("tributum.tenant.id", "default")


def _add_basic_request_attributes(span: Span, request_scope: dict[str, Any]) -> None:
    """Add basic request attributes to span.

    Args:
        span: The OpenTelemetry span
        request_scope: The ASGI request scope
    """
    # Add request path and classify endpoint
    if "path" in request_scope:
        path = request_scope["path"]
        span.set_attribute("http.target", path)

        # Add endpoint classification based on path patterns
        if path.startswith("/api/v"):
            span.set_attribute("tributum.endpoint.type", "api")
            span.set_attribute("tributum.endpoint.version", path.split("/")[2])
        elif path == "/health":
            span.set_attribute("tributum.endpoint.type", "health_check")
        elif path in ("/docs", "/redoc", "/openapi.json"):
            span.set_attribute("tributum.endpoint.type", "documentation")
        elif path == "/":
            span.set_attribute("tributum.endpoint.type", "root")
        else:
            span.set_attribute("tributum.endpoint.type", "other")

        # Add request priority for sampling decisions
        if path == "/health":
            span.set_attribute("tributum.request.priority", "low")
        elif path.startswith("/api/"):
            span.set_attribute("tributum.request.priority", "high")
        else:
            span.set_attribute("tributum.request.priority", "medium")

    # Add request method
    if "method" in request_scope:
        span.set_attribute("http.method", request_scope["method"])


def add_span_milestone(
    event_name: str,
    attributes: dict[str, Any] | None = None,
    span: Span | None = None,
) -> None:
    """Add a milestone event to the current or provided span.

    This function adds structured events to spans for tracking key milestones
    in request processing, such as database connections, external API calls,
    or business logic checkpoints.

    Args:
        event_name: Name of the milestone event
        attributes: Optional attributes to attach to the event
        span: Optional span to add the event to (uses current span if None)
    """
    if span is None:
        span = trace.get_current_span()

    if not span or not span.is_recording():
        return

    # Add timestamp to attributes
    event_attributes = {"timestamp": time.time()}
    if attributes:
        event_attributes.update(attributes)

    # Add the event to the span
    span.add_event(event_name, attributes=event_attributes)


def _add_header_attributes(span: Span, request_scope: dict[str, Any]) -> None:
    """Add header-based attributes to span.

    Args:
        span: The OpenTelemetry span
        request_scope: The ASGI request scope
    """
    # Extract headers for additional context
    headers = dict(request_scope.get("headers", []))

    # Add user agent for client identification
    user_agent = headers.get(b"user-agent", b"").decode("utf-8", errors="ignore")
    if user_agent:
        span.set_attribute("http.user_agent", user_agent)

    # Add content type for request classification
    content_type = headers.get(b"content-type", b"").decode("utf-8", errors="ignore")
    if content_type:
        span.set_attribute("http.request.content_type", content_type.split(";")[0])

    # Add request size if available
    content_length = headers.get(b"content-length", b"").decode(
        "utf-8", errors="ignore"
    )
    if content_length and content_length.isdigit():
        span.set_attribute("http.request.size_bytes", int(content_length))

    # Add client IP for geographic analysis (if behind proxy)
    x_forwarded_for = headers.get(b"x-forwarded-for", b"").decode(
        "utf-8", errors="ignore"
    )
    if x_forwarded_for:
        client_ip = x_forwarded_for.split(",")[0].strip()
        span.set_attribute("http.client_ip", client_ip)
    elif client := request_scope.get("client"):
        span.set_attribute("http.client_ip", client[0])
