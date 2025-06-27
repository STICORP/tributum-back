"""Main FastAPI application module."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Annotated, Any

from fastapi import Depends, FastAPI
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from src.api.middleware.error_handler import register_exception_handlers
from src.api.middleware.request_context import RequestContextMiddleware
from src.api.middleware.request_logging import RequestLoggingMiddleware
from src.api.middleware.security_headers import SecurityHeadersMiddleware
from src.api.utils.responses import ORJSONResponse
from src.core.config import Settings, get_settings
from src.core.logging import get_logger
from src.core.observability import add_correlation_id_to_span, get_tracer, setup_tracing
from src.infrastructure.database.session import (
    check_database_connection,
    close_database,
)


@asynccontextmanager
async def lifespan(app_instance: FastAPI) -> AsyncGenerator[None]:
    """Manage application lifespan events.

    Args:
        app_instance: The FastAPI application instance.

    Yields:
        None: Nothing is yielded, this is just a lifespan context.

    Raises:
        RuntimeError: If database connection fails during startup.
    """
    logger = get_logger(__name__)
    tracer = get_tracer(__name__)

    # Startup: Initialize tracing
    setup_tracing()

    # Startup: Check database connection
    with tracer.start_as_current_span("startup_database_check") as span:
        is_healthy, error_msg = await check_database_connection()

        if is_healthy:
            span.set_attribute("database.connection_check", "success")
            logger.info("Database connection successful")
        else:
            span.set_attribute("database.connection_check", "failed")
            span.set_attribute("error.message", error_msg or "Unknown error")
            span.set_status(
                trace.Status(
                    trace.StatusCode.ERROR, error_msg or "Database connection failed"
                )
            )

            logger.error(
                "Database connection failed during startup",
                error_message=error_msg,
            )
            msg = f"Database connection failed: {error_msg}"
            raise RuntimeError(msg)

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
    application.add_middleware(RequestLoggingMiddleware, log_config=settings.log_config)

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
            is_healthy, error_msg = await check_database_connection()

            health_status["database"] = is_healthy
            span.set_attribute("database.available", str(is_healthy).lower())

            if not is_healthy:
                # Log error but don't fail the health check entirely
                # This allows the service to report as "degraded" rather than "down"
                logger = get_logger(__name__)
                logger.warning(
                    "Database health check failed",
                    error_message=error_msg,
                )
                health_status["status"] = "degraded"

                span.set_attribute("error.message", error_msg or "Unknown error")
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


app = create_app()

# Instrument FastAPI after app creation to ensure proper tracing
# The instrumentor adds automatic span creation for all HTTP requests
FastAPIInstrumentor.instrument_app(
    app,
    server_request_hook=add_correlation_id_to_span,
    excluded_urls="/docs,/redoc,/openapi.json",
)
