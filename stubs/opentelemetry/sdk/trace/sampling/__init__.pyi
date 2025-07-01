"""Type stubs for opentelemetry.sdk.trace.sampling."""

from typing import Any

class Sampler:
    """Type stub for Sampler."""

    def should_sample(
        self,
        parent_context: dict[str, Any] | None,
        trace_id: int,
        name: str,
        kind: int | None = None,
        attributes: dict[str, Any] | None = None,
        links: list[Any] | None = None,
    ) -> bool: ...
    def get_description(self) -> str: ...

class TraceIdRatioBased(Sampler):
    """Type stub for TraceIdRatioBased."""

    def __init__(self, rate: float) -> None: ...
    def should_sample(
        self,
        parent_context: dict[str, Any] | None,
        trace_id: int,
        name: str,
        kind: int | None = None,
        attributes: dict[str, Any] | None = None,
        links: list[Any] | None = None,
    ) -> bool: ...
    def get_description(self) -> str: ...
