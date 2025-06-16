"""Main FastAPI application module."""

from typing import Annotated, Any

from fastapi import Depends, FastAPI

from src.api.utils.responses import ORJSONResponse
from src.core.config import Settings, get_settings


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
    )

    # Define routes
    @application.get("/")
    async def root() -> dict[str, str]:
        """Root endpoint returning a hello world message.

        Returns:
            dict: A dictionary containing a welcome message.
        """
        return {"message": "Hello from Tributum!"}

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
