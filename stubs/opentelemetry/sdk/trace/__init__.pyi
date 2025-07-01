"""Type stubs for opentelemetry.sdk.trace."""

from collections.abc import Mapping
from typing import Any

from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace.export import SpanProcessor
from opentelemetry.sdk.trace.sampling import Sampler
from opentelemetry.trace import (
    SpanContext,
    SpanKind,
    Status,
)
from opentelemetry.trace import (
    TracerProvider as BaseTracerProvider,
)

class IdGenerator:
    """Type stub for IdGenerator."""

class ReadableSpan:
    """Type stub for ReadableSpan."""

    @property
    def name(self) -> str: ...
    @property
    def kind(self) -> SpanKind: ...
    @property
    def attributes(self) -> Mapping[str, Any] | None: ...
    @property
    def start_time(self) -> int | None: ...
    @property
    def end_time(self) -> int | None: ...
    @property
    def status(self) -> Status: ...
    def get_span_context(self) -> SpanContext: ...
    def to_json(self, indent: int = 4) -> str: ...

class TracerProvider(BaseTracerProvider):
    """Type stub for TracerProvider."""

    def __init__(
        self,
        resource: Resource | None = None,
        sampler: Sampler | None = None,
        id_generator: IdGenerator | None = None,
    ) -> None: ...
    def add_span_processor(self, span_processor: SpanProcessor) -> None: ...
