"""Type stubs for opentelemetry.trace."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from enum import IntEnum
from typing import Any

class Context:
    """Type stub for Context."""

class SpanKind(IntEnum):
    """Type stub for SpanKind."""

    INTERNAL = ...
    SERVER = ...
    CLIENT = ...
    PRODUCER = ...
    CONSUMER = ...

    @property
    def name(self) -> str: ...

class StatusCode(IntEnum):
    """Type stub for StatusCode."""

    UNSET = ...
    OK = ...
    ERROR = ...

    @property
    def name(self) -> str: ...

class Status:
    """Type stub for Status."""

    def __init__(
        self,
        status_code: StatusCode = StatusCode.UNSET,
        description: str | None = None,
    ) -> None: ...
    @property
    def status_code(self) -> StatusCode: ...
    @property
    def description(self) -> str | None: ...

class SpanContext:
    """Type stub for SpanContext."""

    @property
    def trace_id(self) -> int: ...
    @property
    def span_id(self) -> int: ...
    @property
    def is_remote(self) -> bool: ...
    @property
    def trace_flags(self) -> int: ...
    @property
    def trace_state(self) -> dict[str, str]: ...

class Span:
    """Type stub for Span."""

    def set_attribute(self, key: str, value: str | int | float | bool) -> None: ...
    def is_recording(self) -> bool: ...
    def add_event(
        self, name: str, attributes: dict[str, Any] | None = None
    ) -> None: ...
    def set_status(self, status: Status, description: str | None = None) -> None: ...
    def update_name(self, name: str) -> None: ...
    def get_span_context(self) -> SpanContext: ...

class Tracer:
    """Type stub for Tracer."""

    def start_span(
        self,
        name: str,
        context: Context | None = None,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: dict[str, Any] | None = None,
        links: list[Any] | None = None,
        start_time: int | None = None,
        record_exception: bool = True,
        set_status_on_exception: bool = True,
    ) -> Span: ...
    @contextmanager
    def start_as_current_span(
        self,
        name: str,
        context: Context | None = None,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: dict[str, Any] | None = None,
        links: list[Any] | None = None,
        start_time: int | None = None,
        record_exception: bool = True,
        set_status_on_exception: bool = True,
        end_on_exit: bool = True,
    ) -> Iterator[Span]: ...

class TracerProvider:
    """Type stub for TracerProvider."""

    def get_tracer(
        self,
        instrumenting_module_name: str,
        instrumenting_library_version: str | None = None,
        schema_url: str | None = None,
    ) -> Tracer: ...

# Module-level functions
def get_tracer(
    instrumenting_module_name: str,
    instrumenting_library_version: str | None = None,
    tracer_provider: TracerProvider | None = None,
) -> Tracer: ...
def set_tracer_provider(tracer_provider: TracerProvider) -> None: ...
def get_current_span() -> Span: ...
@contextmanager
def use_span(
    span: Span,
    end_on_exit: bool = False,
    record_exception: bool = True,
    set_status_on_exception: bool = True,
) -> Iterator[Span]: ...
