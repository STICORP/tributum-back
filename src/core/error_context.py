"""Error context management with basic sensitive data sanitization.

This simplified module provides basic protection against logging
sensitive data. For compliance-critical applications, use cloud
provider DLP APIs (GCP DLP, AWS Macie, Azure Purview).
"""

from __future__ import annotations

import re
from re import Pattern
from typing import Any, Final

# Import constants from other modules
from src.api.constants import SENSITIVE_HEADERS
from src.core.constants import REDACTED

# Type alias for values we can sanitize
SanitizableValue = (
    str | int | float | bool | None | dict[str, Any] | list[Any] | tuple[Any, ...]
)

# Sensitive field patterns - covers common cases
SENSITIVE_FIELD_PATTERN: Final[Pattern[str]] = re.compile(
    r"(password|passwd|pwd|secret|token|api[_-]?key|apikey|auth|authorization|"
    r"credential|private[_-]?key|access[_-]?key|secret[_-]?key|session|"
    r"ssn|social[_-]?security|pin|cvv|cvc|card[_-]?number|connection[_-]?string)",
    re.IGNORECASE,
)

# Maximum depth for nested structure sanitization
MAX_DEPTH: Final[int] = 10


def is_sensitive_field(field_name: str) -> bool:
    """Check if a field name indicates sensitive data.

    Args:
        field_name: The field name to check.

    Returns:
        bool: True if the field appears to contain sensitive data.
    """
    return bool(SENSITIVE_FIELD_PATTERN.search(field_name))


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
