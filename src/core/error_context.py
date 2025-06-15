"""Utilities for error context management and sanitization.

This module provides functions to enrich errors with additional context
and sanitize sensitive data from error contexts before logging or display.
"""

import re
from copy import deepcopy
from typing import Any, TypeVar, overload

from src.core.exceptions import TributumError

T = TypeVar("T")

# Patterns for identifying sensitive field names
SENSITIVE_FIELD_PATTERNS = [
    r".*password.*",
    r".*passwd.*",
    r".*pwd.*",
    r".*secret.*",
    r".*token.*",
    r".*key.*",
    r".*auth.*",
    r".*credential.*",
    r".*api[-_]?key.*",
    r".*access[-_]?token.*",
    r".*refresh[-_]?token.*",
    r".*private.*",
    r".*ssn.*",
    r".*social[-_]?security.*",
    r".*credit[-_]?card.*",
    r".*cvv.*",
    r".*pin.*",
    r".*session.*",
    r".*bearer.*",
]

# Replacement value for sensitive data
REDACTED = "[REDACTED]"


def is_sensitive_field(field_name: str) -> bool:
    """Check if a field name matches sensitive patterns.

    Args:
        field_name: The field name to check

    Returns:
        True if the field name matches any sensitive pattern
    """
    field_lower = field_name.lower()
    return any(re.match(pattern, field_lower) for pattern in SENSITIVE_FIELD_PATTERNS)


@overload
def sanitize_context(context: dict[str, Any]) -> dict[str, Any]: ...


@overload
def sanitize_context(context: T) -> T: ...


def sanitize_context(context: Any) -> Any:
    """Remove sensitive data from a context dictionary.

    Creates a deep copy of the context and replaces any sensitive values
    with a redacted placeholder. Handles nested dictionaries recursively.

    Args:
        context: The context dictionary to sanitize

    Returns:
        A new dictionary with sensitive values replaced
    """
    if not isinstance(context, dict):
        return context

    # Create a deep copy to avoid modifying the original
    sanitized = deepcopy(context)

    def _sanitize_dict(data: dict[str, Any]) -> None:
        """Recursively sanitize a dictionary in place."""
        for key in list(data.keys()):  # Use list() to avoid mutation during iteration
            value = data[key]
            if is_sensitive_field(key):
                data[key] = REDACTED
            elif isinstance(value, dict):
                _sanitize_dict(value)
            elif isinstance(value, list):
                _sanitize_list(value)

    def _sanitize_list(data: list[Any]) -> None:
        """Recursively sanitize items in a list."""
        for item in data:
            if isinstance(item, dict):
                _sanitize_dict(item)
            elif isinstance(item, list):
                _sanitize_list(item)

    _sanitize_dict(sanitized)
    return sanitized


def enrich_error(
    error: TributumError, additional_context: dict[str, Any]
) -> TributumError:
    """Add additional context to a TributumError instance.

    Merges the additional context with the error's existing context.
    The additional context takes precedence for duplicate keys.

    Args:
        error: The error to enrich
        additional_context: Additional context to add

    Returns:
        The same error instance with enriched context
    """
    if not isinstance(error, TributumError):
        raise TypeError("Error must be an instance of TributumError")

    if additional_context:
        # Merge contexts, with additional_context taking precedence
        error.context = {**error.context, **additional_context}

    return error
