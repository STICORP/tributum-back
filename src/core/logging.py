"""Structured logging configuration for the Tributum application.

This module provides structured logging using structlog with support for
both development (console) and production (JSON) output formats.
"""

import asyncio
import hashlib
import logging
import os
import socket
import sys
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from copy import deepcopy
from enum import Enum
from pathlib import Path
from typing import Any

import orjson
import psutil
import structlog
from structlog.typing import EventDict, Processor

from src.core.config import get_settings
from src.core.constants import (
    EXCEPTION_TUPLE_MIN_LENGTH,
    MAX_CONTEXT_DEPTH,
    MAX_CONTEXT_SIZE,
    MAX_VALUE_SIZE,
    MIN_CONTAINER_ID_LENGTH,
    TRACEBACK_FRAMES_TO_INCLUDE,
)
from src.core.context import RequestContext
from src.core.error_context import sanitize_context
from src.core.exceptions import TributumError


def _auto_configure() -> None:
    """Automatically configure structlog on first import."""
    # Check if structlog has already been configured
    if not structlog.is_configured():
        configure_structlog()


class MergeStrategy(Enum):
    """Strategy for merging context values."""

    SHALLOW = "shallow"  # New values override existing
    DEEP = "deep"  # Deep merge of dictionaries


class ORJSONRenderer:
    """Custom JSON renderer using orjson for better performance.

    This renderer handles all types commonly used in logs including
    datetime, UUID, and exceptions, while providing significant
    performance improvements over the standard JSONRenderer.

    Args:
        **options: Additional options passed to orjson.dumps.
                  Default includes OPT_SORT_KEYS for consistency.
    """

    def __init__(self, **options: Any) -> None:  # noqa: ANN401 - orjson options are flexible
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
            str: JSON-encoded string of the event dictionary.
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
            dict[str, Any]: Processed dictionary safe for orjson serialization.
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
        EventDict: The modified event dictionary with uppercase log level.
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
        EventDict: The event dictionary with correlation ID if available.
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
    It also adds context depth indicator and filters out None values.

    Args:
        logger: The logger instance.
        method_name: The logging method name.
        event_dict: The event dictionary.

    Returns:
        EventDict: The event dictionary with additional context merged in.
    """
    _ = logger, method_name  # Required by structlog processor interface
    context = _logger_context_var.get()
    if context is not None:
        # Add context depth if using LogContextManager
        if hasattr(_context_manager, "depth") and _context_manager.depth > 0:
            event_dict["context_depth"] = _context_manager.depth

        # Merge context, with event_dict taking precedence
        total_size = 0
        for key, value in context.items():
            # Skip None values
            if value is None:
                continue

            # Skip if key already exists in event_dict
            if key in event_dict:
                continue

            # Apply size limits
            value_str = str(value)
            if len(value_str) > MAX_VALUE_SIZE:
                # Truncate large values
                truncated_value = value_str[: MAX_VALUE_SIZE - 3] + "..."
                event_dict[key] = truncated_value
                total_size += len(str(key)) + len(truncated_value)
            else:
                event_dict[key] = value
                total_size += len(str(key)) + len(str(value))

            # Check total context size
            if total_size > MAX_CONTEXT_SIZE:
                # Add truncation indicator and stop
                event_dict["context_truncated"] = True
                break
    return event_dict


# Cache for environment processor values
_environment_cache: dict[str, Any] = {}


def _get_container_id() -> str | None:
    """Extract container ID from cgroup file.

    Returns:
        str | None: Container ID (first 12 chars) or None if not in container.
    """
    try:
        cgroup_path = Path("/proc/self/cgroup")
        with cgroup_path.open(encoding="utf-8") as f:
            for line in f:
                # Look for Docker or containerd patterns
                if "/docker/" in line or "/containerd/" in line:
                    # Extract container ID (last part after last /)
                    parts = line.strip().split("/")
                    if len(parts) > 1:
                        # Container ID is typically 64 chars
                        potential_id = parts[-1]
                        if len(potential_id) >= MIN_CONTAINER_ID_LENGTH:
                            # Use first 12 chars
                            return potential_id[:MIN_CONTAINER_ID_LENGTH]
    except OSError:
        pass
    return None


def performance_processor(
    logger: logging.Logger, method_name: str, event_dict: EventDict
) -> EventDict:
    """Add performance metrics to log entries.

    This processor adds system performance information including process ID,
    thread ID, memory usage, and active asyncio tasks.

    Args:
        logger: The logger instance.
        method_name: The logging method name.
        event_dict: The event dictionary.

    Returns:
        EventDict: The event dictionary with performance metrics added.
    """
    _ = logger, method_name  # Required by structlog processor interface

    # Add process and thread information
    event_dict["process_id"] = os.getpid()
    event_dict["thread_id"] = str(threading.get_ident())

    # Try to get memory usage with psutil if available
    try:
        process = psutil.Process()
        memory_info = process.memory_info()
        event_dict["memory_mb"] = round(memory_info.rss / (1024 * 1024), 2)
    except (ImportError, AttributeError, OSError):
        # psutil not available or error getting memory info
        pass

    # Count active asyncio tasks if in async context
    try:
        # Try to get the current event loop
        loop = asyncio.get_running_loop()
        tasks = asyncio.all_tasks(loop)
        event_dict["active_tasks"] = len(tasks)
    except RuntimeError:
        # Not in async context or no running loop
        pass

    return event_dict


def environment_processor(
    logger: logging.Logger, method_name: str, event_dict: EventDict
) -> EventDict:
    """Add environment information to log entries.

    This processor adds hostname, container ID, and Kubernetes pod information
    when available. Values are cached as they don't change during runtime.

    Args:
        logger: The logger instance.
        method_name: The logging method name.
        event_dict: The event dictionary.

    Returns:
        EventDict: The event dictionary with environment information added.
    """
    _ = logger, method_name  # Required by structlog processor interface

    # Check if we've already cached the values
    if not _environment_cache:
        # Get hostname
        try:
            _environment_cache["hostname"] = socket.gethostname()
        except (OSError, AttributeError):
            _environment_cache["hostname"] = "unknown"

        # Try to get container ID from cgroup
        _environment_cache["container_id"] = _get_container_id()

        # Get Kubernetes information from environment
        _environment_cache["k8s_pod"] = os.environ.get("K8S_POD_NAME")
        _environment_cache["k8s_namespace"] = os.environ.get("K8S_NAMESPACE")

    # Add cached values to event dict
    event_dict["hostname"] = _environment_cache["hostname"]
    if _environment_cache["container_id"]:
        event_dict["container_id"] = _environment_cache["container_id"]
    if _environment_cache["k8s_pod"]:
        event_dict["k8s_pod"] = _environment_cache["k8s_pod"]
    if _environment_cache["k8s_namespace"]:
        event_dict["k8s_namespace"] = _environment_cache["k8s_namespace"]

    return event_dict


def error_context_processor(
    logger: logging.Logger, method_name: str, event_dict: EventDict
) -> EventDict:
    """Enhance exception logging with additional context.

    This processor adds exception fingerprint and module information when
    exc_info is present. It integrates with the existing error context
    sanitization.

    Args:
        logger: The logger instance.
        method_name: The logging method name.
        event_dict: The event dictionary.

    Returns:
        EventDict: The event dictionary with enhanced exception context.
    """
    _ = logger, method_name  # Required by structlog processor interface

    # Only process if there's exception info
    exc_info = event_dict.get("exc_info")
    if not exc_info:
        return event_dict

    # Extract exception details
    if isinstance(exc_info, tuple) and len(exc_info) >= EXCEPTION_TUPLE_MIN_LENGTH:
        exc_type, exc_value, exc_traceback = exc_info
    elif isinstance(exc_info, bool) and exc_info:
        # exc_info=True means get current exception
        exc_type, exc_value, exc_traceback = sys.exc_info()
    elif isinstance(exc_info, BaseException):
        # Direct exception object
        exc_type = type(exc_info)
        exc_value = exc_info
        exc_traceback = exc_info.__traceback__
    else:
        return event_dict

    if exc_type and exc_value:
        # Add exception module
        event_dict["exception_module"] = exc_type.__module__

        # Generate exception fingerprint
        # Use exception type name and key parts of the traceback
        fingerprint_parts = [exc_type.__name__]

        # Add key stack frame information
        if exc_traceback:
            tb_frame = exc_traceback
            frame_count = 0
            while tb_frame and frame_count < TRACEBACK_FRAMES_TO_INCLUDE:
                frame = tb_frame.tb_frame
                code = frame.f_code
                # Include filename (without path) and function name
                filename = Path(code.co_filename).name
                fingerprint_parts.extend(
                    [filename, code.co_name, str(tb_frame.tb_lineno)]
                )
                tb_frame = tb_frame.tb_next
                frame_count += 1

        # Create hash of the fingerprint parts
        fingerprint_str = "|".join(fingerprint_parts)
        # Use SHA256 and truncate for security
        fingerprint_hash = hashlib.sha256(fingerprint_str.encode()).hexdigest()[:8]
        event_dict["exception_fingerprint"] = fingerprint_hash

        # If there's error context, sanitize it
        if "error_context" in event_dict:
            event_dict["error_context"] = sanitize_context(event_dict["error_context"])

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
    ]

    # Conditionally add new processors based on config
    if log_config.enable_performance_processor:
        base_processors.append(performance_processor)
    if log_config.enable_environment_processor:
        base_processors.append(environment_processor)
    if log_config.enable_error_context_processor:
        base_processors.append(error_context_processor)

    # Add callsite info after other processors
    base_processors.append(
        structlog.processors.CallsiteParameterAdder(
            parameters=[
                structlog.processors.CallsiteParameter.FILENAME,
                structlog.processors.CallsiteParameter.LINENO,
                structlog.processors.CallsiteParameter.FUNC_NAME,
            ]
        )
    )

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
        # format_exc_info removed - ConsoleRenderer handles pretty exceptions
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


def get_logger(name: str | None = None, **initial_context: Any) -> Any:  # noqa: ANN401 - structlog.BoundLogger lacks stable typing
    """Get a structlog logger instance with automatic context binding.

    This function returns a logger that automatically includes any context
    stored in contextvars, ensuring context propagation across async boundaries.

    Args:
        name: The name of the logger. If None, uses the caller's module name.
        **initial_context: Initial key-value pairs to bind to this logger instance.

    Returns:
        Any: A bound structlog logger instance with context from contextvars.
    """
    # Ensure structlog is configured before creating loggers
    _auto_configure()

    logger = structlog.get_logger(name)
    if initial_context:
        logger = logger.bind(**initial_context)
    return logger


@contextmanager
def log_context(
    **bindings: Any,  # noqa: ANN401 - flexible context bindings
) -> Iterator[Any]:
    """Context manager for temporary log context bindings.

    This context manager maintains backward compatibility while using the enhanced
    LogContextManager. It yields a bound logger that includes the temporary context.

    Args:
        **bindings: Key-value pairs to bind to the logger context.

    Yields:
        Any: A bound logger with the temporary context.

    Example:
        with log_context(user_id=123, request_id="abc") as logger:
            logger.info("User action")  # Will include user_id and request_id
            with log_context(operation="delete") as nested_logger:
                nested_logger.info("Nested")  # Includes operation, but not user_id
    """
    # Get current logger and bind the context for backward compatibility
    logger = structlog.get_logger()
    bound_logger = logger.bind(**bindings)

    # Also push to context manager for enhanced features
    _context_manager.push(**bindings)

    try:
        yield bound_logger
    finally:
        # Pop the context layer when exiting
        _context_manager.pop()


def log_exception(
    logger: Any,  # noqa: ANN401 - structlog.BoundLogger lacks stable typing
    error: Exception,
    message: str | None = None,
    **extra_context: Any,  # noqa: ANN401 - flexible logging context
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


def bind_logger_context(**bindings: Any) -> None:  # noqa: ANN401 - flexible logging context
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


def get_logger_context() -> dict[str, Any]:
    """Get the current logger context without modification.

    Returns:
        dict[str, Any]: A copy of the current context, or empty dict if no context.

    Example:
        context = get_logger_context()
        print(f"Current context: {context}")
    """
    current_context = _logger_context_var.get()
    return dict(current_context) if current_context is not None else {}


def unbind_logger_context(*keys: str) -> None:
    """Remove specific keys from the logger context.

    This function removes one or more keys from the current logger context
    without clearing the entire context.

    Args:
        *keys: The keys to remove from the context.

    Example:
        bind_logger_context(user_id=123, session_id="abc", temp_value="xyz")
        unbind_logger_context("temp_value")  # Only removes temp_value
    """
    current_context = _logger_context_var.get()
    if current_context is not None:
        updated_context = {k: v for k, v in current_context.items() if k not in keys}
        # Set to None if context becomes empty
        _logger_context_var.set(updated_context if updated_context else None)


class LogContextManager:
    """Manager for advanced logger context operations with layering support.

    This class provides a more sophisticated context management system with
    support for nested contexts, merge strategies, and size limits.
    It initializes with an empty stack for layered contexts.
    """

    def __init__(self) -> None:
        self._context_stack: list[dict[str, Any]] = []

    def push(self, **bindings: Any) -> None:  # noqa: ANN401 - flexible context
        """Push a new context layer onto the stack.

        Args:
            **bindings: Key-value pairs to add as a new context layer.

        Raises:
            RuntimeError: If context depth exceeds MAX_CONTEXT_DEPTH.

        Example:
            context_manager.push(user_id=123)
            context_manager.push(action="delete")  # Nested context
        """
        if len(self._context_stack) >= MAX_CONTEXT_DEPTH:
            raise RuntimeError(f"Context depth exceeded maximum of {MAX_CONTEXT_DEPTH}")

        # Deep copy any dict values to prevent mutations
        copied_bindings = {}
        for key, value in bindings.items():
            if isinstance(value, dict):
                copied_bindings[key] = deepcopy(value)
            else:
                copied_bindings[key] = value

        # Add new layer
        self._context_stack.append(copied_bindings)
        self._update_context_var()

    def pop(self) -> dict[str, Any] | None:
        """Remove and return the top context layer.

        Returns:
            dict[str, Any] | None: The removed context layer, or None if stack is empty.

        Example:
            context_manager.push(temp="value")
            popped = context_manager.pop()  # Returns {"temp": "value"}
        """
        if not self._context_stack:
            return None

        popped = self._context_stack.pop()
        self._update_context_var()
        return popped

    def peek(self) -> dict[str, Any]:
        """Get the current merged context without modification.

        Returns:
            dict[str, Any]: The current merged context from all layers.
        """
        return self._merge_contexts()

    def merge(
        self,
        bindings: dict[str, Any],
        strategy: MergeStrategy = MergeStrategy.SHALLOW,
    ) -> None:
        """Merge new values into the current top context layer.

        Args:
            bindings: Dictionary of values to merge.
            strategy: Merge strategy to use (SHALLOW or DEEP).

        Example:
            context_manager.push(config={"a": 1})
            context_manager.merge({"config": {"b": 2}}, MergeStrategy.DEEP)
            # Result: config={"a": 1, "b": 2}
        """
        if not self._context_stack:
            # No existing context, just push new one
            self.push(**bindings)
            return

        top_layer = self._context_stack[-1]

        if strategy == MergeStrategy.SHALLOW:
            # Simple update - new values override
            top_layer.update(bindings)
        else:
            # Deep merge
            self._deep_merge(top_layer, bindings)

        self._update_context_var()

    def _deep_merge(self, target: dict[str, Any], source: dict[str, Any]) -> None:
        """Recursively merge source dict into target dict.

        Args:
            target: Dictionary to merge into (modified in place).
            source: Dictionary to merge from.
        """
        for key, value in source.items():
            if (
                key in target
                and isinstance(target[key], dict)
                and isinstance(value, dict)
            ):
                # Both are dicts, recurse
                self._deep_merge(target[key], value)
            else:
                # Simple assignment
                target[key] = deepcopy(value) if isinstance(value, dict) else value

    def _merge_contexts(self) -> dict[str, Any]:
        """Merge all context layers into a single dictionary.

        Returns:
            dict[str, Any]: Merged context from all layers.
        """
        result: dict[str, Any] = {}
        for layer in self._context_stack:
            result.update(layer)
        return result

    def _update_context_var(self) -> None:
        """Update the context var with the merged context."""
        merged = self._merge_contexts()
        _logger_context_var.set(merged if merged else None)

    @property
    def depth(self) -> int:
        """Get the current context stack depth.

        Returns:
            int: Number of context layers.
        """
        return len(self._context_stack)


# Global instance for convenient access
_context_manager = LogContextManager()
