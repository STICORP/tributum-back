"""Main entry point for running the Tributum FastAPI application."""

import os

import uvicorn

from src.api.main import app
from src.core.config import get_settings
from src.core.logging import setup_logging


def main() -> None:
    """Main entry point for the Tributum application."""
    settings = get_settings()

    # Setup logging first
    setup_logging(settings)

    # Check for Cloud Run PORT environment variable
    # Cloud Run sets PORT to the port the container should listen on
    port = int(os.environ.get("PORT", settings.api_port))

    # When reload is enabled, we must pass the app as an import string
    if settings.debug:
        uvicorn.run(
            "src.api.main:app",
            host=settings.api_host,
            port=port,
            reload=True,
            log_level=settings.log_config.log_level.lower(),
        )
    else:
        # In production, we can pass the app directly for better performance
        uvicorn.run(
            app,
            host=settings.api_host,
            port=port,
            reload=False,
            log_level=settings.log_config.log_level.lower(),
        )


if __name__ == "__main__":
    main()
