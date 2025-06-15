"""Main entry point for running the Tributum FastAPI application."""

import uvicorn

from src.core.config import get_settings


def main() -> None:
    """Main entry point for the Tributum application."""
    settings = get_settings()

    # When reload is enabled, we must pass the app as an import string
    if settings.debug:
        uvicorn.run(
            "src.api.main:app",
            host=settings.api_host,
            port=settings.api_port,
            reload=True,
            log_level=settings.log_config.log_level.lower(),
        )
    else:
        # In production, we can import and pass the app directly for better performance
        from src.api.main import app

        uvicorn.run(
            app,
            host=settings.api_host,
            port=settings.api_port,
            reload=False,
            log_level=settings.log_config.log_level.lower(),
        )


if __name__ == "__main__":
    main()
