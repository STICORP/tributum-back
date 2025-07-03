"""Sensitive data sanitization for secure error logging and responses.

This module implements a comprehensive sanitization system that prevents
sensitive information from being exposed in logs, error messages, or API
responses. It provides automatic detection and redaction of sensitive fields
based on patterns and configuration.

Key features:
- **Pattern matching**: Regex-based detection of sensitive field names
- **Configurable fields**: Additional sensitive fields via configuration
- **Deep sanitization**: Recursive handling of nested data structures
- **Header protection**: Special handling for sensitive HTTP headers
- **SQL parameter safety**: Sanitization of database query parameters

Security considerations:
- This provides basic protection suitable for most applications
- For regulatory compliance (PCI, HIPAA), consider cloud DLP services
- Sanitization is applied at logging time, not storage time
- Original data remains unchanged, only logged copies are sanitized

The module is designed to be performant with caching and early returns,
suitable for high-throughput production environments.
"""

from __future__ import annotations

import re
from functools import lru_cache
from re import Pattern
from typing import Any, Final

# Import constants from other modules
from src.core.config import get_settings

# Type alias for values we can sanitize
SanitizableValue = (
    str | int | float | bool | None | dict[str, Any] | list[Any] | tuple[Any, ...]
)

SENSITIVE_HEADERS = {
    "authorization",
    "cookie",
    "x-api-key",
    "x-auth-token",
    "x-csrf-token",
    "set-cookie",
    "x-secret-key",
    "proxy-authorization",
}

REDACTED = "[REDACTED]"

# Default sensitive field patterns - covers common cases
DEFAULT_SENSITIVE_PATTERN: Final[Pattern[str]] = re.compile(
    r"(password|passwd|pwd|secret|token|api[_-]?key|apikey|auth|authorization|"
    r"credential|private[_-]?key|access[_-]?key|secret[_-]?key|session|"
    r"ssn|social[_-]?security|pin|cvv|cvc|card[_-]?number|connection[_-]?string)",
    re.IGNORECASE,
)

# Maximum depth for nested structure sanitization
MAX_DEPTH: Final[int] = 10


@lru_cache(maxsize=1)
def _get_sensitive_fields() -> list[str]:
    """Get the configured sensitive fields from settings.

    Returns:
        list[str]: List of sensitive field names to check.
    """
    settings = get_settings()
    return settings.log_config.sensitive_fields


def is_sensitive_field(field_name: str) -> bool:
    """Check if a field name indicates sensitive data.

    Checks against both the default regex pattern and the
    configured sensitive fields list.

    Args:
        field_name: The field name to check.

    Returns:
        bool: True if the field appears to contain sensitive data.
    """
    # First check against the default pattern
    if DEFAULT_SENSITIVE_PATTERN.search(field_name):
        return True

    # Then check against configured fields (case-insensitive)
    field_lower = field_name.lower()
    for sensitive_field in _get_sensitive_fields():
        if sensitive_field.lower() in field_lower:
            return True

    return False


def is_sensitive_header(header_name: str) -> bool:
    """Check if a header name is sensitive.

    Args:
        header_name: The header name to check (case-insensitive).

    Returns:
        bool: True if the header is sensitive.
    """
    return header_name.lower() in SENSITIVE_HEADERS


def sanitize_value(
    value: SanitizableValue, field_name: str = "", depth: int = 0
) -> SanitizableValue:
    """Sanitize a value if it appears to be sensitive.

    This function recursively sanitizes nested structures (dicts and lists)
    up to MAX_DEPTH to prevent infinite recursion.

    Args:
        value: The value to potentially sanitize.
        field_name: The field name for context.
        depth: Current recursion depth.

    Returns:
        SanitizableValue: Sanitized value or original if not sensitive.
    """
    # Prevent infinite recursion
    if depth > MAX_DEPTH:
        return REDACTED

    # Check if field name indicates sensitive data
    if field_name and is_sensitive_field(field_name):
        return REDACTED

    # Recursively sanitize nested structures
    if isinstance(value, dict):
        return {k: sanitize_value(v, k, depth + 1) for k, v in value.items()}

    if isinstance(value, list):
        return [sanitize_value(item, "", depth + 1) for item in value]

    if isinstance(value, tuple):
        return tuple(sanitize_value(item, "", depth + 1) for item in value)

    # Return original value if not sensitive
    return value


def sanitize_dict(data: dict[str, Any]) -> dict[str, Any]:
    """Sanitize a dictionary by redacting sensitive fields.

    Args:
        data: Dictionary to sanitize.

    Returns:
        dict[str, Any]: New dictionary with sensitive values redacted.
    """
    return {key: sanitize_value(value, key) for key, value in data.items()}


def sanitize_headers(headers: dict[str, str]) -> dict[str, str]:
    """Sanitize HTTP headers.

    Args:
        headers: Headers dictionary.

    Returns:
        dict[str, str]: Sanitized headers.
    """
    return {k: REDACTED if is_sensitive_header(k) else v for k, v in headers.items()}


def sanitize_error_context(
    error: Exception, context: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Create sanitized error context for logging.

    Args:
        error: The exception to create context for.
        context: Additional context to include (will be sanitized).

    Returns:
        dict[str, Any]: Sanitized error context safe for logging.
    """
    error_context: dict[str, Any] = {
        "error_type": type(error).__name__,
        "error_message": str(error),
    }

    # Add sanitized additional context
    if context:
        error_context.update(sanitize_dict(context))

    # Add exception attributes if they exist (sanitized)
    if hasattr(error, "__dict__"):
        error_attrs = {k: v for k, v in error.__dict__.items() if not k.startswith("_")}
        if error_attrs:
            sanitized_attrs = sanitize_dict(error_attrs)
            error_context["error_attributes"] = sanitized_attrs

    return error_context


def sanitize_sql_params(
    params: object,
) -> object:
    """Sanitize SQL query parameters for safe logging.

    This function handles the different parameter formats that SQLAlchemy
    might use (dict, list, tuple) and sanitizes them appropriately.

    Args:
        params: SQL query parameters in various formats.

    Returns:
        object: Sanitized parameters in the same format as input, or REDACTED string.
            The return type is object to handle all possible parameter types.
    """
    if params is None:
        return None

    if isinstance(params, dict):
        # Named parameters - sanitize by key name
        return sanitize_dict(params)
    if isinstance(params, (list, tuple)):
        # Positional parameters - can't determine sensitivity by name
        # Return as-is for now, but could be configured to redact all
        return params

    # Unknown format - be safe and redact
    return REDACTED
