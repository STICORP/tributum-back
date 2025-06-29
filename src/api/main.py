"""Main FastAPI application module."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Annotated, Any

from fastapi import Depends, FastAPI
from loguru import logger

from src.api.middleware.error_handler import register_exception_handlers
from src.api.middleware.request_context import RequestContextMiddleware
from src.api.middleware.security_headers import SecurityHeadersMiddleware
from src.api.utils.responses import ORJSONResponse
from src.core.config import Settings, get_settings
from src.core.logging import setup_logging
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
    # Startup: Check database connection
    is_healthy, error_msg = await check_database_connection()

    if is_healthy:
        logger.info("Database connection successful")
    else:
        logger.error("Database connection failed during startup: %s", error_msg)
        msg = f"Database connection failed: {error_msg}"
        raise RuntimeError(msg)

    # Log startup with app info
    logger.info(
        "Application startup complete - %s v%s",
        app_instance.title,
        app_instance.version,
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

    # Setup logging first
    setup_logging(settings)

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

        # Check database connectivity
        is_healthy, error_msg = await check_database_connection()

        health_status["database"] = is_healthy

        if not is_healthy:
            # Log error but don't fail the health check entirely
            # This allows the service to report as "degraded" rather than "down"
            logger.warning("Database health check failed: %s", error_msg)
            health_status["status"] = "degraded"

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
