"""Observability and tracing setup for the application.

This module configures OpenTelemetry with GCP Cloud Trace integration
and provides utilities for distributed tracing.
"""

from opentelemetry import trace
from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import ReadableSpan, TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.sampling import TraceIdRatioBased
from opentelemetry.trace import Span, Status, StatusCode, Tracer

from src.core.config import get_settings
from src.core.exceptions import Severity, TributumError
from src.core.logging import get_logger

logger = get_logger(__name__)


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


def setup_tracing() -> None:
    """Configure OpenTelemetry tracing with GCP Cloud Trace integration.

    This function:
    - Sets up trace provider with configured sampling
    - Configures GCP Cloud Trace exporter if enabled
    - Adds custom span processor for error tracking
    - Integrates with TributumError context capture
    """
    settings = get_settings()
    obs_config = settings.observability_config

    if not obs_config.enable_tracing:
        logger.info("Tracing is disabled")
        return

    logger.info(
        "Setting up tracing",
        service_name=obs_config.service_name,
        sample_rate=obs_config.trace_sample_rate,
    )

    # Create resource with service information
    resource = Resource.create(
        {
            "service.name": obs_config.service_name,
            "service.version": settings.app_version,
            "deployment.environment": settings.environment,
        }
    )

    # Create tracer provider with sampling
    sampler = TraceIdRatioBased(obs_config.trace_sample_rate)
    provider = TracerProvider(resource=resource, sampler=sampler)

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
