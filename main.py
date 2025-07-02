"""Main entry point for running the Tributum FastAPI application."""

import os

import uvicorn
from loguru import logger

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

    # Configure uvicorn to use our logging
    log_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "handlers": {
            "default": {
                "class": "src.core.logging.InterceptHandler",
            },
        },
        "loggers": {
            "uvicorn": {"handlers": ["default"], "level": "INFO", "propagate": False},
            "uvicorn.error": {
                "handlers": ["default"],
                "level": "INFO",
                "propagate": False,
            },
            "uvicorn.access": {
                "handlers": ["default"],
                "level": "INFO",
                "propagate": False,
            },
        },
    }

    # When reload is enabled, we must pass the app as an import string
    if settings.debug:
        logger.info(
            f"Starting Uvicorn on http://{settings.api_host}:{port} "
            "(development mode with auto-reload)"
        )
        uvicorn.run(
            "src.api.main:app",
            host=settings.api_host,
            port=port,
            reload=True,
            log_config=log_config,
        )
    else:
        # In production, we can pass the app directly for better performance
        logger.info(
            f"Starting Uvicorn on http://{settings.api_host}:{port} (production mode)"
        )
        uvicorn.run(
            app,
            host=settings.api_host,
            port=port,
            reload=False,
            log_config=log_config,
        )


if __name__ == "__main__":
    main()
