"""Logging configuration using Loguru with full type safety and GCP integration."""

from __future__ import annotations

import logging
import sys
from typing import Any, Final, Protocol

from loguru import logger

# Type aliases for clarity
type LogLevel = str
type CorrelationID = str
type LogContext = dict[str, Any]


class _LoggingState:
    """Simple state holder to track if logging has been configured."""

    def __init__(self) -> None:
        self.configured = False


_state = _LoggingState()


class SettingsProtocol(Protocol):
    """Protocol for settings objects that setup_logging can accept."""

    @property
    def debug(self) -> bool:
        """Debug mode flag."""
        ...

    @property
    def log_config(self) -> LogConfigProtocol:
        """Log configuration."""
        ...


class LogConfigProtocol(Protocol):
    """Protocol for log configuration objects."""

    @property
    def log_level(self) -> str:
        """Logging level."""
        ...


# Constants
DEFAULT_LOG_FORMAT: Final[str] = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
    "{message}"
)


class InterceptHandler(logging.Handler):
    """Intercept standard logging and redirect to Loguru.

    This handler captures logs from libraries using standard logging
    and forwards them to Loguru for consistent formatting.
    """

    def emit(self, record: logging.LogRecord) -> None:
        """Forward log record to Loguru.

        Args:
            record: Standard library LogRecord to forward.
        """
        # Find caller from where originated the logged message
        try:
            frame = sys._getframe(6)
            depth = 6
            while frame and frame.f_code.co_filename == logging.__file__:
                next_frame = frame.f_back
                if next_frame is None:
                    break
                frame = next_frame
                depth += 1
        except ValueError:
            # _getframe can fail if there aren't enough frames
            depth = 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            record.levelname, record.getMessage()
        )


def should_log_path(record: dict[str, Any]) -> bool:
    """Filter out excluded paths from logs.

    Args:
        record: Loguru record dictionary.

    Returns:
        bool: True if the path should be logged.
    """
    # TODO: Implementation would check against excluded_paths from settings
    # For now, log everything
    del record  # Explicitly indicate parameter is unused in Phase 1
    return True


def setup_logging(settings: SettingsProtocol) -> None:
    """Configure Loguru for the application.

    This is a basic setup for Phase 1. Cloud-specific formatters
    will be added in Phase 3.

    Args:
        settings: Application settings containing log configuration.

    Note:
        This function ensures it's only called once using module state.
    """
    if _state.configured:
        return

    # Remove default handler
    logger.remove()

    # Add console handler with development-friendly format
    logger.add(
        sys.stdout,
        format=DEFAULT_LOG_FORMAT,
        level=settings.log_config.log_level,
        enqueue=True,  # Thread-safe async logging
        colorize=True,  # Colored output for development
        diagnose=settings.debug,  # Include variable values in tracebacks
        backtrace=settings.debug,  # Include full traceback
    )

    # Configure standard library logging to use Loguru
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)

    # Disable noisy loggers
    for logger_name in ["uvicorn.access", "urllib3.connectionpool"]:
        logging.getLogger(logger_name).disabled = True

    # Mark as configured
    _state.configured = True


def bind_context(**kwargs: object) -> None:
    """Bind context variables to the logger.

    This is for persistent context that should remain for the
    lifetime of the application or a long-running operation.

    For request-scoped context, use logger.contextualize() instead.

    Args:
        **kwargs: Context variables to bind.

    Example:
        >>> bind_context(service_name="api", version="1.0.0")
    """
    logger.configure(extra=kwargs)


def get_logger(name: str) -> object:
    """Get a logger instance with the given name.

    Args:
        name: Logger name, typically __name__.

    Returns:
        object: Logger instance bound with the name.
    """
    return logger.bind(logger_name=name)
