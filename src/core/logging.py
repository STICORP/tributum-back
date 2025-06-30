"""Logging configuration using Loguru with pluggable formatters."""

from __future__ import annotations

import json
import logging
import os
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

    @property
    def log_formatter_type(self) -> str | None:
        """Log formatter type."""
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


def serialize_for_json(record: dict[str, Any]) -> str:
    """Format log record as generic JSON for development/self-hosted.

    Args:
        record: Loguru record to format.

    Returns:
        str: JSON-formatted log entry with newline.
    """
    log_entry: dict[str, Any] = {
        "timestamp": record["time"].isoformat(),
        "level": record["level"].name,
        "message": record["message"],
        "logger": record["name"],
        "function": record["function"],
        "module": record["module"],
        "line": record["line"],
    }

    # Add extra fields (includes correlation_id, request_id, etc.)
    if extra := record.get("extra", {}):
        # Filter out internal Loguru fields
        filtered_extra = {k: v for k, v in extra.items() if not k.startswith("_")}
        if filtered_extra:
            log_entry.update(filtered_extra)

    # Add exception info if present
    if exc := record.get("exception"):
        exception_info = {
            "type": exc.type.__name__ if exc.type else None,
            "value": str(exc.value) if exc.value else None,
            "traceback": exc.traceback if exc.traceback else None,
        }
        log_entry["exception"] = exception_info

    return json.dumps(log_entry, default=str) + "\n"


def serialize_for_gcp(record: dict[str, Any]) -> str:
    """Format log record for GCP Cloud Logging.

    Follows GCP structured logging format:
    https://cloud.google.com/logging/docs/structured-logging

    Args:
        record: Loguru record to format.

    Returns:
        str: JSON-formatted log entry for GCP with newline.
    """
    # Map Loguru levels to GCP severity
    severity_mapping = {
        "TRACE": "DEBUG",
        "DEBUG": "DEBUG",
        "INFO": "INFO",
        "SUCCESS": "INFO",
        "WARNING": "WARNING",
        "ERROR": "ERROR",
        "CRITICAL": "CRITICAL",
    }

    # Build GCP-compatible log entry
    log_entry: dict[str, Any] = {
        "severity": severity_mapping.get(record["level"].name, "INFO"),
        "message": record["message"],
        "timestamp": record["time"].isoformat(),
    }

    # Add labels for GCP
    labels = {
        "function": record["function"],
        "module": record["module"],
        "line": str(record["line"]),
    }

    # Add extra fields to labels
    if extra := record.get("extra", {}):
        # Add specific fields that GCP understands
        if correlation_id := extra.get("correlation_id"):
            log_entry["logging.googleapis.com/trace"] = correlation_id

        if request_id := extra.get("request_id"):
            labels["request_id"] = request_id

        # Add other fields to jsonPayload
        json_payload = {
            k: v
            for k, v in extra.items()
            if k not in {"correlation_id", "request_id"} and not k.startswith("_")
        }
        if json_payload:
            log_entry["jsonPayload"] = json_payload

    labels_dict: dict[str, str] = labels
    log_entry["logging.googleapis.com/labels"] = labels_dict

    # Add source location for error reporting
    if record.get("exception"):
        source_location = {
            "file": record["file"].path,
            "line": str(record["line"]),
            "function": record["function"],
        }
        log_entry["logging.googleapis.com/sourceLocation"] = source_location

    return json.dumps(log_entry, default=str) + "\n"


def serialize_for_aws(record: dict[str, Any]) -> str:
    """Format log record for AWS CloudWatch.

    Follows AWS CloudWatch Logs Insights format for better querying.

    Args:
        record: Loguru record to format.

    Returns:
        str: JSON-formatted log entry for AWS with newline.
    """
    log_entry: dict[str, Any] = {
        "timestamp": record["time"].isoformat(),
        "level": record["level"].name,
        "message": record["message"],
        "logger": record["name"],
        "function": record["function"],
        "module": record["module"],
        "line": record["line"],
    }

    # Add AWS-specific fields
    if extra := record.get("extra", {}):
        # AWS X-Ray integration
        if correlation_id := extra.get("correlation_id"):
            log_entry["traceId"] = correlation_id

        if request_id := extra.get("request_id"):
            log_entry["requestId"] = request_id

        # Add other fields
        for key, value in extra.items():
            if not key.startswith("_") and key not in log_entry:
                log_entry[key] = value

    # Add exception details
    if exc := record.get("exception"):
        error_info = {
            "type": exc.type.__name__ if exc.type else None,
            "message": str(exc.value) if exc.value else None,
            "stackTrace": exc.traceback if exc.traceback else None,
        }
        log_entry["error"] = error_info

    return json.dumps(log_entry, default=str) + "\n"


# Type for formatter functions
type FormatterFunc = Any  # Callable[[dict[str, Any]], str]

# Formatter registry - easily extensible
LOG_FORMATTERS: dict[str, FormatterFunc | None] = {
    "console": None,  # Use Loguru's default console formatter
    "json": serialize_for_json,
    "gcp": serialize_for_gcp,
    "aws": serialize_for_aws,
}


def detect_environment() -> str:
    """Auto-detect the deployment environment.

    Returns:
        str: Detected formatter type (console, gcp, aws).
    """
    # Check for cloud-specific environment variables
    if os.getenv("K_SERVICE"):  # Cloud Run
        return "gcp"
    if os.getenv("AWS_EXECUTION_ENV"):  # AWS Lambda/ECS
        return "aws"
    if os.getenv("WEBSITE_INSTANCE_ID"):  # Azure
        return "json"  # Azure uses generic JSON
    return "console"  # Local development


def setup_logging(settings: SettingsProtocol) -> None:
    """Configure Loguru with pluggable formatters.

    Args:
        settings: Application settings containing log configuration.

    Note:
        This function ensures it's only called once using module state.
    """
    if _state.configured:
        return

    # Remove default handler
    logger.remove()

    # Determine formatter type
    formatter_type = settings.log_config.log_formatter_type

    # Auto-detect if not specified
    if not formatter_type:
        formatter_type = detect_environment()

    # Get formatter function
    formatter = LOG_FORMATTERS.get(formatter_type)

    if formatter_type == "console" or formatter is None:
        # Human-readable console format for development
        logger.add(
            sys.stdout,
            format=DEFAULT_LOG_FORMAT,
            level=settings.log_config.log_level,
            enqueue=True,
            colorize=True,
            diagnose=settings.debug,
            backtrace=settings.debug,
        )
    else:
        # Structured format for cloud providers or JSON
        # Create a custom sink that uses the formatter
        def structured_sink(message: object) -> None:
            """Custom sink that formats and writes structured logs."""
            if formatter and hasattr(message, "record"):
                formatted = formatter(message.record)
                sys.stdout.write(formatted)
                sys.stdout.flush()

        logger.add(
            structured_sink,
            level=settings.log_config.log_level,
            enqueue=True,  # Thread-safe async logging
            diagnose=False,  # No variable values in production
            backtrace=False,  # Minimal traceback in production
        )

    # Configure standard library logging to use Loguru
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)

    # Disable noisy loggers
    for logger_name in ["uvicorn.access", "urllib3.connectionpool"]:
        logging.getLogger(logger_name).disabled = True

    # Log the formatter being used
    logger.info(
        "Logging configured with {} formatter",
        formatter_type,
        formatter_type=formatter_type,
        log_level=settings.log_config.log_level,
    )

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
