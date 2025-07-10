"""Structured logging system with cloud provider integrations.

This module implements a sophisticated logging system using Loguru that
provides structured, contextual logging with automatic formatting for
different deployment environments.

Features:
- **Structured logging**: JSON output with consistent schema
- **Context propagation**: Automatic inclusion of correlation IDs
- **Cloud formatters**: Native formats for GCP, AWS, and Azure
- **Performance optimization**: Async logging with thread-safe queues
- **Standard library integration**: Captures logs from all Python modules
- **Rich console output**: Development-friendly formatting with context

Formatter types:
- **console**: Human-readable with inline context (development)
- **json**: Generic structured format (self-hosted)
- **gcp**: Google Cloud Logging format with trace integration
- **aws**: CloudWatch Logs Insights optimized format

The logging system automatically detects the deployment environment
and selects the appropriate formatter, ensuring logs are properly
ingested and indexed by the platform's logging service.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from typing import Any, Final, Protocol, cast

from loguru import logger

from src.core.config import get_settings

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
CORRELATION_ID_DISPLAY_LENGTH: Final[int] = 8
MAX_FIELD_VALUE_LENGTH: Final[int] = 100


def _format_priority_field(field: str, value: object) -> str | None:
    """Format a priority field for display.

    Args:
        field: The field name.
        value: The field value.

    Returns:
        str | None: Formatted value or None if formatting fails.
    """
    try:
        if (
            field == "correlation_id"
            and value
            and len(str(value)) > CORRELATION_ID_DISPLAY_LENGTH
        ):
            # Shorten correlation ID for readability
            value = str(value)[:CORRELATION_ID_DISPLAY_LENGTH]
        elif field == "duration_ms":
            value = f"{value}ms"
        elif field == "status_code":
            # Color code status codes
            status_str = str(value)
            if status_str.startswith("2"):
                value = f"<green>{value}</green>"
            elif status_str.startswith("3"):
                value = f"<yellow>{value}</yellow>"
            elif status_str.startswith("4"):
                value = f"<red>{value}</red>"
            elif status_str.startswith("5"):
                value = f"<red><bold>{value}</bold></red>"
        # Escape braces to prevent format string errors
        return str(value).replace("{", "{{").replace("}", "}}")
    except (AttributeError, TypeError, ValueError) as e:
        logger.trace(f"Failed to format priority field {field}: {e}")
        return None


def _format_extra_field(key: str, value: object) -> str | None:
    """Format an extra field for display.

    Args:
        key: The field name.
        value: The field value.

    Returns:
        str | None: Formatted field or None if formatting fails.
    """
    try:
        # Convert value to string
        str_value = str(value)

        # Check for sensitive fields and redact
        settings = get_settings()
        if key in settings.log_config.sensitive_fields:
            str_value = "[REDACTED]"
        elif len(str_value) > MAX_FIELD_VALUE_LENGTH:
            # Limit length of field values to prevent huge logs
            str_value = str_value[: MAX_FIELD_VALUE_LENGTH - 3] + "..."

        # Escape braces to prevent format string errors
        str_value = str_value.replace("{", "{{").replace("}", "}}")
        safe_key = str(key).replace("{", "{{").replace("}", "}}")
    except (AttributeError, TypeError, ValueError) as e:
        logger.trace(f"Failed to format extra field {key}: {e}")
        return None
    else:
        return f"{safe_key}={str_value}"


def _format_timestamp(record: dict[str, Any]) -> str:
    """Format timestamp from record.

    Args:
        record: Loguru record.

    Returns:
        str: Formatted timestamp string.
    """
    timestamp = record.get("time")
    if timestamp:
        return str(timestamp.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3])
    return "unknown"


def _format_level(record: dict[str, Any]) -> str:
    """Format log level from record.

    Args:
        record: Loguru record.

    Returns:
        str: Formatted level name.
    """
    level = record.get("level", {})
    if hasattr(level, "name"):
        return getattr(level, "name", "INFO")
    return str(level)


def _format_context_fields(extra: dict[str, Any]) -> list[str]:
    """Format all context fields from extra data.

    Args:
        extra: Extra fields from the log record.

    Returns:
        list[str]: List of formatted context parts.
    """
    context_parts = []

    # Priority fields that should appear first
    priority_fields = [
        "correlation_id",
        "request_id",
        "method",
        "path",
        "status_code",
        "duration_ms",
        "client_host",
        "user_agent",
    ]

    # Add priority fields if present
    for field in priority_fields:
        if field in extra and extra[field] is not None:
            formatted = _format_priority_field(field, extra[field])
            if formatted:
                context_parts.append(f"<yellow>{formatted}</yellow>")

    # Add any other fields not in priority list
    for key, value in extra.items():
        if key not in priority_fields and not key.startswith("_") and value is not None:
            formatted = _format_extra_field(key, value)
            if formatted:
                context_parts.append(f"<dim>{formatted}</dim>")

    return context_parts


def format_console_with_context(record: dict[str, Any]) -> str:
    """Format log record for console with all context fields visible.

    This formatter displays all extra fields in a readable inline format,
    making development logging comprehensive and useful.

    Args:
        record: Loguru record to format.

    Returns:
        str: Formatted log string with context.
    """
    try:
        # Format basic parts
        time_str = _format_timestamp(record)
        level_name = _format_level(record)

        parts = [
            f"<green>{time_str}</green>",
            f"<level>{level_name: <8}</level>",
        ]

        # Add logger location
        name = record.get("name", "")
        function = record.get("function", "")
        line = record.get("line", "")
        location = f"{name}:{function}:{line}"
        parts.append(f"<cyan>{location}</cyan>")

        # Extract and format context fields
        extra = record.get("extra", {})
        context_parts = _format_context_fields(extra)

        # Combine context parts
        if context_parts:
            context_str = " ".join(f"[{part}]" for part in context_parts)
            parts.append(context_str)

        # Add the message and escape braces
        message = str(record.get("message", "")).replace("{", "{{").replace("}", "}}")
        parts.append(message)

        # Add exception if present
        if record.get("exception"):
            parts.append("\n{{exception}}")

        # Join all parts with pipe separator and add newline
        return " | ".join(parts) + "\n"
    except (AttributeError, TypeError, ValueError, KeyError) as e:
        # Fallback to default format if anything goes wrong
        logger.trace(f"Failed to format log record: {e}")
        return DEFAULT_LOG_FORMAT + "\n"


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

        # Extract extra context from LogRecord if available
        extra = {}

        # Map uvicorn access log fields to our standard fields
        if record.name == "uvicorn.access" and hasattr(record, "scope"):
            scope = record.scope
            extra["method"] = scope.get("method", "")
            extra["path"] = scope.get("path", "")
            extra["client_host"] = scope.get("client", ["unknown"])[0]

            # Try to get correlation ID from scope headers
            headers = dict(scope.get("headers", []))
            correlation_id = headers.get(b"x-correlation-id", b"").decode("utf-8")
            if correlation_id:
                extra["correlation_id"] = correlation_id

        # Pass along any extra fields from the record
        skip_fields = {
            "name",
            "msg",
            "args",
            "created",
            "msecs",
            "relativeCreated",
            "thread",
            "threadName",
            "processName",
            "process",
            "pathname",
            "filename",
            "module",
            "lineno",
            "funcName",
            "stack_info",
            "exc_text",
            "color_message",
            "taskName",
        }
        # Use dictionary comprehension as suggested by PERF403
        additional_fields = {
            key: value
            for key, value in record.__dict__.items()
            if (
                key not in logging.LogRecord.__dict__
                and not key.startswith("_")
                and key not in skip_fields
            )
        }
        extra.update(additional_fields)

        logger.opt(depth=depth, exception=record.exc_info).bind(**extra).log(
            record.levelname, record.getMessage()
        )


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

    # Add service context for better filtering in Error Reporting
    settings = get_settings()
    log_entry["serviceContext"] = {
        "service": settings.app_name,
        "version": settings.app_version,
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

        # Add error fingerprint to labels for grouping (truncated for GCP label limits)
        if fingerprint := extra.get("fingerprint"):
            labels["error_fingerprint"] = fingerprint[:8]

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

    # Add source location and Error Reporting fields for errors
    if record.get("exception") or record["level"].name in ["ERROR", "CRITICAL"]:
        source_location = {
            "file": record["file"].path,
            "line": str(record["line"]),
            "function": record["function"],
        }
        log_entry["logging.googleapis.com/sourceLocation"] = source_location

        # Add Error Reporting type for better integration
        log_entry["@type"] = (
            "type.googleapis.com/google.devtools.clouderrorreporting.v1beta1.ReportedErrorEvent"
        )

        # Add context for Error Reporting
        if extra and "stack_trace" in extra:
            log_entry["context"] = {
                "reportLocation": {
                    "filePath": record["file"].path,
                    "lineNumber": record["line"],
                    "functionName": record["function"],
                }
            }
            # Include the custom stack trace
            log_entry["stack_trace"] = extra["stack_trace"]

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
        # Human-readable console format for development with full context
        logger.add(
            sys.stdout,
            format=cast("Any", format_console_with_context),
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

    # Intercept all uvicorn loggers - they're already configured by main.py
    # Just ensure they're not disabled
    for logger_name in ["uvicorn", "uvicorn.error", "uvicorn.access"]:
        uvicorn_logger = logging.getLogger(logger_name)
        if not uvicorn_logger.handlers:
            uvicorn_logger.handlers = [InterceptHandler()]
            uvicorn_logger.setLevel(logging.INFO)
            uvicorn_logger.propagate = False

    # Only disable truly noisy loggers
    for logger_name in ["urllib3.connectionpool"]:
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
