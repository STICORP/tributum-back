"""Type stubs for opentelemetry.exporter.otlp.proto.grpc.trace_exporter."""

from collections.abc import Sequence

from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult

class OTLPSpanExporter(SpanExporter):
    """Type stub for OTLPSpanExporter."""

    def __init__(
        self,
        endpoint: str | None = None,
        insecure: bool | None = None,
        credentials: object | None = None,
        headers: tuple[tuple[str, str], ...] | None = None,
        timeout: int | None = None,
        compression: str | None = None,
    ) -> None: ...
    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult: ...
    def shutdown(self) -> None: ...
    def force_flush(self, timeout_millis: int = 30000) -> bool: ...
