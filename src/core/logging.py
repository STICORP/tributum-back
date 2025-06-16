"""Structured logging configuration for the Tributum application.

This module provides structured logging using structlog with support for
both development (console) and production (JSON) output formats.
"""

import logging
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any

import orjson
import structlog
from structlog.typing import EventDict, Processor

from src.core.config import get_settings
from src.core.context import RequestContext


class ORJSONRenderer:
    """Custom JSON renderer using orjson for better performance.

    This renderer handles all types commonly used in logs including
    datetime, UUID, and exceptions, while providing significant
    performance improvements over the standard JSONRenderer.
    """

    def __init__(self, **options: Any) -> None:
        """Initialize the renderer with orjson options.

        Args:
            **options: Additional options passed to orjson.dumps.
                      Default includes OPT_SORT_KEYS for consistency.
        """
        # Default options for consistency
        self._options = orjson.OPT_SORT_KEYS

        # Add any additional options
        for opt_name, opt_value in options.items():
            if hasattr(orjson, opt_name) and opt_value:
                self._options |= getattr(orjson, opt_name)

    def __call__(self, logger: logging.Logger, name: str, event_dict: EventDict) -> str:
        """Render the event dictionary as JSON using orjson.

        Args:
            logger: The logger instance (unused but required by interface).
            name: The name of the logger (unused but required by interface).
            event_dict: The event dictionary to render.

        Returns:
            JSON-encoded string of the event dictionary.
        """
        _ = logger, name  # Required by structlog processor interface

        # Convert special types that orjson handles natively
        # orjson handles datetime, UUID, etc. automatically
        # but we need to handle exceptions which it doesn't
        processed_dict = self._process_dict(event_dict)

        # Use orjson for fast serialization
        return orjson.dumps(processed_dict, option=self._options).decode("utf-8")

    def _process_dict(self, d: EventDict | dict[str, Any]) -> dict[str, Any]:
        """Process dictionary to handle types that orjson doesn't handle.

        Args:
            d: Dictionary to process.

        Returns:
            Processed dictionary safe for orjson serialization.
        """
        result: dict[str, Any] = {}
        for key, value in d.items():
            if isinstance(value, dict):
                # Recursively process nested dictionaries
                result[key] = self._process_dict(value)
            elif isinstance(value, list | tuple):
                # Process lists and tuples
                processed_list: list[Any] = []
                for item in value:
                    if isinstance(item, dict):
                        processed_list.append(self._process_dict(item))
                    elif isinstance(item, Exception):
                        processed_list.append(str(item))
                    elif isinstance(item, type):
                        processed_list.append(item.__name__)
                    else:
                        processed_list.append(item)
                result[key] = processed_list
            elif isinstance(value, Exception):
                # Convert exceptions to string representation
                result[key] = str(value)
            elif isinstance(value, type):
                # Convert types to their string representation
                result[key] = value.__name__
            else:
                # orjson handles datetime, UUID, str, int, float, bool, None
                result[key] = value
        return result


# Context variable for storing additional logger context across async boundaries
_logger_context_var: ContextVar[dict[str, Any] | None] = ContextVar(
    "logger_context", default=None
)


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


def inject_logger_context(
    logger: logging.Logger, method_name: str, event_dict: EventDict
) -> EventDict:
    """Inject additional context from contextvars into log entries.

    This processor adds any context stored in the logger context var
    to all log entries, enabling context propagation across async boundaries.

    Args:
        logger: The logger instance.
        method_name: The logging method name.
        event_dict: The event dictionary.

    Returns:
        The event dictionary with additional context merged in.
    """
    _ = logger, method_name  # Required by structlog processor interface
    context = _logger_context_var.get()
    if context is not None:
        # Merge context, with event_dict taking precedence
        for key, value in context.items():
            if key not in event_dict:
                event_dict[key] = value
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
        inject_logger_context,  # Add additional context from contextvars
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
    json_renderer = ORJSONRenderer()

    prod_processors: list[Processor] = [
        *base_processors,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.dict_tracebacks,
        json_renderer,
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
    stdlib_processor: Processor
    if not log_config.render_json_logs:
        stdlib_processor = structlog.dev.ConsoleRenderer(colors=True)
    else:
        # Use same JSON renderer as prod_processors
        stdlib_processor = ORJSONRenderer()

    logging.getLogger().handlers[0].setFormatter(
        structlog.stdlib.ProcessorFormatter(
            processor=stdlib_processor,
            foreign_pre_chain=base_processors,
        )
    )


def get_logger(name: str | None = None, **initial_context: Any) -> Any:
    """Get a structlog logger instance with automatic context binding.

    This function returns a logger that automatically includes any context
    stored in contextvars, ensuring context propagation across async boundaries.

    Args:
        name: The name of the logger. If None, uses the caller's module name.
        **initial_context: Initial key-value pairs to bind to this logger instance.

    Returns:
        A bound structlog logger instance with context from contextvars.
    """
    logger = structlog.get_logger(name)
    if initial_context:
        logger = logger.bind(**initial_context)
    return logger


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


def bind_logger_context(**bindings: Any) -> None:
    """Bind additional context to all loggers in the current async context.

    This function adds key-value pairs to the logger context that will be
    automatically included in all log messages within the current async context.
    This is useful for adding request-specific context that should appear in
    all logs during request processing.

    Args:
        **bindings: Key-value pairs to add to the logger context.

    Example:
        # At the start of request processing
        bind_logger_context(user_id=123, request_id="abc-123")

        # All subsequent logs will include user_id and request_id
        logger.info("Processing request")  # Will include user_id and request_id
    """
    current_context = _logger_context_var.get()
    if current_context is None:
        updated_context = bindings
    else:
        updated_context = {**current_context, **bindings}
    _logger_context_var.set(updated_context)


def clear_logger_context() -> None:
    """Clear all logger context for the current async context.

    This should typically be called at the end of request processing to ensure
    a clean state for the next request.
    """
    _logger_context_var.set(None)
