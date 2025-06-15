"""Structured logging configuration for the Tributum application.

This module provides structured logging using structlog with support for
both development (console) and production (JSON) output formats.
"""

import logging
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import structlog
from structlog.typing import EventDict, Processor

from src.core.config import get_settings
from src.core.context import RequestContext


def add_log_level_upper(
    logger: logging.Logger, method_name: str, event_dict: EventDict
) -> EventDict:
    """Add log level in uppercase to the event dictionary.

    Args:
        logger: The logger instance.
        method_name: The logging method name.
        event_dict: The event dictionary.

    Returns:
        The modified event dictionary with uppercase log level.
    """
    _ = logger  # Required by structlog processor interface
    if method_name == "warn":
        method_name = "warning"
    event_dict["level"] = method_name.upper()
    return event_dict


def inject_correlation_id(
    logger: logging.Logger, method_name: str, event_dict: EventDict
) -> EventDict:
    """Inject correlation ID from context into log entries.

    Args:
        logger: The logger instance.
        method_name: The logging method name.
        event_dict: The event dictionary.

    Returns:
        The event dictionary with correlation ID if available.
    """
    _ = logger, method_name  # Required by structlog processor interface
    correlation_id = RequestContext.get_correlation_id()
    if correlation_id:
        event_dict["correlation_id"] = correlation_id
    return event_dict


def configure_structlog() -> None:
    """Configure structlog with appropriate processors for the environment.

    Sets up different processor pipelines for development (console) and
    production (JSON) environments. Integrates with stdlib logging for
    third-party libraries.
    """
    settings = get_settings()
    log_config = settings.log_config

    # Convert log level string to logging level
    log_level = getattr(logging, log_config.log_level.upper())

    # Base processors that are always included
    base_processors: list[Processor] = [
        structlog.stdlib.add_logger_name,
        add_log_level_upper,
        inject_correlation_id,  # Add correlation ID from context
        structlog.processors.CallsiteParameterAdder(
            parameters=[
                structlog.processors.CallsiteParameter.FILENAME,
                structlog.processors.CallsiteParameter.LINENO,
                structlog.processors.CallsiteParameter.FUNC_NAME,
            ]
        ),
    ]

    # Add timestamp if configured
    if log_config.add_timestamp:
        if log_config.timestamper_format == "iso":
            base_processors.append(structlog.processors.TimeStamper(fmt="iso"))
        else:
            base_processors.append(structlog.processors.TimeStamper(fmt=None))

    # Development processors (human-readable console output)
    dev_processors: list[Processor] = [
        *base_processors,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.dev.ConsoleRenderer(colors=True),
    ]

    # Production processors (JSON output)
    prod_processors: list[Processor] = [
        *base_processors,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.dict_tracebacks,
        structlog.processors.JSONRenderer(),
    ]

    # Choose processors based on configuration
    if log_config.render_json_logs or log_config.log_format == "json":
        processors = prod_processors
    else:
        processors = dev_processors

    # Configure structlog
    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure stdlib logging for integration with third-party libraries
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )

    # Add structlog processor to stdlib logging
    logging.getLogger().handlers[0].setFormatter(
        structlog.stdlib.ProcessorFormatter(
            processor=structlog.dev.ConsoleRenderer(colors=True)
            if not log_config.render_json_logs
            else structlog.processors.JSONRenderer(),
            foreign_pre_chain=base_processors,
        )
    )


def get_logger(name: str | None = None) -> Any:
    """Get a structlog logger instance.

    Args:
        name: The name of the logger. If None, uses the caller's module name.

    Returns:
        A bound structlog logger instance.
    """
    return structlog.get_logger(name)


@contextmanager
def log_context(**bindings: Any) -> Iterator[Any]:
    """Context manager for temporary log context bindings.

    This allows adding temporary context to all log messages within
    the context manager scope without using contextvars.

    Args:
        **bindings: Key-value pairs to bind to the logger context.

    Yields:
        A bound logger with the temporary context.

    Example:
        with log_context(user_id=123, request_id="abc") as logger:
            logger.info("User action")  # Will include user_id and request_id
    """
    # Get current logger and bind the context
    logger = structlog.get_logger()
    bound_logger = logger.bind(**bindings)

    # Yield the bound logger for use within the context
    yield bound_logger


def log_exception(
    logger: Any,
    error: Exception,
    message: str | None = None,
    **extra_context: Any,
) -> None:
    """Log an exception with full context and stack trace.

    This helper extracts context from TributumError instances and logs
    the exception with appropriate severity and metadata.

    Args:
        logger: The structlog logger instance to use
        error: The exception to log
        message: Optional custom message (defaults to exception message)
        **extra_context: Additional context to include in the log

    Example:
        try:
            risky_operation()
        except TributumError as e:
            log_exception(logger, e, "Operation failed")
    """
    from src.core.exceptions import TributumError

    # Prepare the log context
    context = dict(extra_context)

    # Extract context from TributumError instances
    if isinstance(error, TributumError):
        context.update(
            {
                "error_code": error.error_code,
                "severity": error.severity.value,
                "fingerprint": error.fingerprint,
            }
        )

        # Add error context if present
        if error.context:
            context["error_context"] = error.context

        # Use the appropriate log level based on severity
        log_method = {
            "LOW": logger.warning,
            "MEDIUM": logger.error,
            "HIGH": logger.error,
            "CRITICAL": logger.critical,
        }.get(error.severity.value, logger.error)

        # Use custom message or error message
        log_message = message or str(error)
    else:
        # For non-TributumError exceptions
        context["error_type"] = type(error).__name__
        log_method = logger.error
        log_message = message or str(error)

    # Log with exception info for stack trace
    log_method(log_message, exc_info=error, **context)
