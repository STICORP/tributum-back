"""Type stubs for opentelemetry.instrumentation.fastapi."""

from collections.abc import Callable
from typing import Any

from fastapi import FastAPI
from opentelemetry.trace import TracerProvider

class FastAPIInstrumentor:
    """Type stub for FastAPIInstrumentor."""

    is_instrumented_by_opentelemetry: bool

    @staticmethod
    def instrument_app(
        app: FastAPI,
        server_request_hook: Callable[[Any, dict[str, Any]], None] | None = None,
        client_request_hook: Callable[[Any, dict[str, Any]], None] | None = None,
        client_response_hook: Callable[[Any, dict[str, Any]], None] | None = None,
        tracer_provider: TracerProvider | None = None,
        meter_provider: object | None = None,
        excluded_urls: str | None = None,
    ) -> None: ...
    def instrument(
        self,
        server_request_hook: Callable[[Any, dict[str, Any]], None] | None = None,
        client_request_hook: Callable[[Any, dict[str, Any]], None] | None = None,
        client_response_hook: Callable[[Any, dict[str, Any]], None] | None = None,
        tracer_provider: TracerProvider | None = None,
        meter_provider: object | None = None,
        excluded_urls: str | None = None,
    ) -> None: ...
    def uninstrument(self) -> None: ...
    @staticmethod
    def uninstrument_app(app: FastAPI) -> None: ...
