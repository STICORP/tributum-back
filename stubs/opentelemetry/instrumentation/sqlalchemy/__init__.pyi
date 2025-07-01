"""Type stubs for opentelemetry.instrumentation.sqlalchemy."""

from typing import Any

from opentelemetry.trace import TracerProvider

class SQLAlchemyInstrumentor:
    """Type stub for SQLAlchemyInstrumentor."""

    def instrument(
        self,
        engine: object | None = None,
        tracer_provider: TracerProvider | None = None,
        enable_commenter: bool | None = None,
        commenter_options: dict[str, Any] | None = None,
    ) -> None: ...
    def uninstrument(self, engine: object | None = None) -> None: ...
