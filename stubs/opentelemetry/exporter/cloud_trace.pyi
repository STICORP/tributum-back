"""Type stubs for opentelemetry.exporter.cloud_trace."""

from opentelemetry.sdk.trace.export import SpanExporter

class CloudTraceSpanExporter(SpanExporter):
    """Google Cloud Trace span exporter."""

    def __init__(self, project_id: str | None = None) -> None:
        """Initialize the Cloud Trace exporter.

        Args:
            project_id: GCP project ID. If not provided, will attempt to
                       infer from the environment.
        """
