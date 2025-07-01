"""Type stubs for opentelemetry.sdk.trace.export."""

from collections.abc import Sequence
from enum import IntEnum
from typing import Any

from opentelemetry.sdk.trace import ReadableSpan

class SpanExportResult(IntEnum):
    """Type stub for SpanExportResult."""

    SUCCESS = ...
    FAILURE = ...

class SpanExporter:
    """Type stub for SpanExporter."""

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult: ...
    def shutdown(self) -> None: ...
    def force_flush(self, timeout_millis: int = 30000) -> bool: ...

class SpanProcessor:
    """Type stub for SpanProcessor."""

    def on_start(
        self, span: ReadableSpan, parent_context: dict[str, Any] | None = None
    ) -> None: ...
    def on_end(self, span: ReadableSpan) -> None: ...
    def shutdown(self) -> None: ...
    def force_flush(self, timeout_millis: int = 30000) -> bool: ...

class BatchSpanProcessor(SpanProcessor):
    """Type stub for BatchSpanProcessor."""

    def __init__(
        self,
        span_exporter: SpanExporter,
        max_queue_size: int = 2048,
        schedule_delay_millis: float = 5000,
        max_export_batch_size: int = 512,
        export_timeout_millis: float = 30000,
    ) -> None: ...
    def on_start(
        self, span: ReadableSpan, parent_context: dict[str, Any] | None = None
    ) -> None: ...
    def on_end(self, span: ReadableSpan) -> None: ...
    def shutdown(self) -> None: ...
    def force_flush(self, timeout_millis: int = 30000) -> bool: ...
