"""Main FastAPI application module."""

from typing import Annotated, Any

from fastapi import Depends, FastAPI

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

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
        docs_url=settings.docs_url,
        redoc_url=settings.redoc_url,
        openapi_url=settings.openapi_url,
    )

    # Define routes
    @app.get("/")
    async def root() -> dict[str, str]:
        """Root endpoint returning a hello world message.

        Returns:
            dict: A dictionary containing a welcome message.
        """
        return {"message": "Hello from Tributum!"}

    @app.get("/info")
    async def info(
        settings: Annotated[Settings, Depends(get_settings)],
    ) -> dict[str, Any]:
        """Get application information.

        Args:
            settings: Application settings injected via dependency.

        Returns:
            dict[str, Any]: Application information including name, version,
                and environment.
        """
        return {
            "app_name": settings.app_name,
            "version": settings.app_version,
            "environment": settings.environment,
            "debug": settings.debug,
        }

    return app


app = create_app()
