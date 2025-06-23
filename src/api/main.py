"""Main FastAPI application module."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Annotated, Any

from fastapi import Depends, FastAPI
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from src.api.middleware.error_handler import register_exception_handlers
from src.api.middleware.request_context import RequestContextMiddleware
from src.api.middleware.request_logging import RequestLoggingMiddleware
from src.api.middleware.security_headers import SecurityHeadersMiddleware
from src.api.utils.responses import ORJSONResponse
from src.core.config import Settings, get_settings
from src.core.context import RequestContext
from src.core.logging import get_logger
from src.core.observability import get_tracer, setup_tracing
from src.infrastructure.database.session import close_database, get_engine


@asynccontextmanager
async def lifespan(app_instance: FastAPI) -> AsyncGenerator[None]:
    """Manage application lifespan events.

    Args:
        app_instance: The FastAPI application instance.

    Yields:
        None: Nothing is yielded, this is just a lifespan context.

    Raises:
        Exception: If database connection fails during startup.
    """
    logger = get_logger(__name__)
    tracer = get_tracer(__name__)

    # Startup: Initialize tracing
    setup_tracing()

    # Startup: Check database connection
    with tracer.start_as_current_span("startup_database_check") as span:
        try:
            engine = get_engine()
            async with engine.connect() as conn:
                result = await conn.execute(text("SELECT 1"))
                _ = result.scalar()

            pool_size = engine.pool.size() if hasattr(engine.pool, "size") else "N/A"
            span.set_attribute("database.pool_size", str(pool_size))
            span.set_attribute("database.connection_check", "success")

            logger.info(
                "Database connection successful",
                pool_size=pool_size,
            )
        except Exception as e:
            span.set_attribute("database.connection_check", "failed")
            span.set_attribute("error.type", type(e).__name__)
            span.record_exception(e)
            span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))

            logger.exception(
                "Database connection failed during startup",
                error_type=type(e).__name__,
            )
            raise

    # Log startup with app info
    logger.info(
        "Application startup complete",
        app_name=app_instance.title,
        version=app_instance.version,
    )

    yield

    # Shutdown: Cleanup database connections
    logger.info("Application shutdown initiated")
    await close_database()
    logger.info("Application shutdown complete")


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create and configure the FastAPI application.

    Args:
        settings: Optional settings instance. If not provided, will use get_settings().

    Returns:
        FastAPI: Configured FastAPI application instance.
    """
    if settings is None:
        settings = get_settings()

    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
        docs_url=settings.docs_url,
        redoc_url=settings.redoc_url,
        openapi_url=settings.openapi_url,
        default_response_class=ORJSONResponse,
        lifespan=lifespan,
    )

    # Register exception handlers BEFORE middleware
    register_exception_handlers(application)

    # Register middleware AFTER exception handlers
    # Order is important: middleware are executed in reverse order of registration
    # So the last middleware added is the first to process requests

    # 3. Request logging middleware (logs requests/responses with correlation ID)
    application.add_middleware(RequestLoggingMiddleware)

    # 2. Request context middleware (creates correlation ID)
    application.add_middleware(RequestContextMiddleware)

    # 1. Security headers middleware (adds security headers to all responses)
    application.add_middleware(SecurityHeadersMiddleware)

    # Define routes
    @application.get("/")
    async def root() -> dict[str, str]:
        """Root endpoint returning a hello world message.

        Returns:
            dict[str, str]: A dictionary containing a welcome message.
        """
        return {"message": "Hello from Tributum!"}

    @application.get("/health")
    async def health() -> dict[str, object]:
        """Health check endpoint for monitoring and container orchestration.

        Used by:
        - Docker health checks
        - Kubernetes liveness/readiness probes
        - GCP Cloud Run health checks
        - Load balancers

        Returns:
            dict[str, object]: A dictionary with status and database connectivity.
        """
        health_status: dict[str, object] = {"status": "healthy", "database": False}
        tracer = get_tracer(__name__)

        # Check database connectivity
        with tracer.start_as_current_span("health_check_database") as span:
            try:
                engine = get_engine()
                async with engine.connect() as conn:
                    result = await conn.execute(text("SELECT 1"))
                    _ = result.scalar()
                health_status["database"] = True
                span.set_attribute("database.available", "true")
            except SQLAlchemyError as e:
                # Log error but don't fail the health check entirely
                # This allows the service to report as "degraded" rather than "down"
                logger = get_logger(__name__)
                logger.warning("Database health check failed")
                health_status["status"] = "degraded"

                span.set_attribute("database.available", "false")
                span.set_attribute("error.type", type(e).__name__)
                span.record_exception(e)
                # Don't set ERROR status - degraded state is expected behavior
                span.set_status(
                    trace.Status(
                        trace.StatusCode.OK,
                        "Database unavailable but service operational",
                    )
                )

            span.set_attribute("health.status", str(health_status["status"]))

        return health_status

    @application.get("/info")
    async def info(
        app_settings: Annotated[Settings, Depends(get_settings)],
    ) -> dict[str, Any]:
        """Get application information.

        Args:
            app_settings: Application settings injected via dependency.

        Returns:
            dict[str, Any]: Application information including name, version,
                and environment.
        """
        return {
            "app_name": app_settings.app_name,
            "version": app_settings.app_version,
            "environment": app_settings.environment,
            "debug": app_settings.debug,
        }

    return application


def _add_correlation_id_to_span(
    span: trace.Span, request_scope: dict[str, Any]
) -> None:
    """Add correlation ID to the current span if available.

    This function is called by the FastAPI instrumentor for each request
    to enrich spans with correlation IDs.

    Args:
        span: The current OpenTelemetry span
        request_scope: The ASGI request scope
    """
    # Add request path as span attribute
    if "path" in request_scope:
        span.set_attribute("http.target", request_scope["path"])

    # Add correlation ID if available
    correlation_id = RequestContext.get_correlation_id()
    if correlation_id:
        span.set_attribute("correlation_id", correlation_id)
        span.set_attribute("tributum.correlation_id", correlation_id)


app = create_app()

# Instrument FastAPI after app creation to ensure proper tracing
# The instrumentor adds automatic span creation for all HTTP requests
FastAPIInstrumentor.instrument_app(
    app,
    server_request_hook=_add_correlation_id_to_span,
    excluded_urls="/docs,/redoc,/openapi.json",
)
