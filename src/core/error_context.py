"""Utilities for error context management and sanitization.

This module provides functions to enrich errors with additional context
and sanitize sensitive data from error contexts before logging or display.
"""

import re
from copy import deepcopy
from typing import TYPE_CHECKING, Any, TypeVar, overload

from src.core.constants import REDACTED, SENSITIVE_FIELD_PATTERNS, SENSITIVE_HEADERS
from src.core.exceptions import TributumError

if TYPE_CHECKING:  # pragma: no cover
    # TYPE_CHECKING is False at runtime; used only for static type analysis
    from fastapi import Request

T = TypeVar("T")


def is_sensitive_field(field_name: str) -> bool:
    """Check if a field name matches sensitive patterns.

    Args:
        field_name: The field name to check

    Returns:
        bool: True if the field name matches any sensitive pattern
    """
    field_lower = field_name.lower()
    return any(re.match(pattern, field_lower) for pattern in SENSITIVE_FIELD_PATTERNS)


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


@overload
def sanitize_context(context: dict[str, Any]) -> dict[str, Any]: ...


@overload
def sanitize_context[T2](context: T2) -> T2: ...


def sanitize_context(context: Any) -> Any:
    """Remove sensitive data from a context dictionary.

    Creates a deep copy of the context and replaces any sensitive values
    with a redacted placeholder. Handles nested dictionaries recursively.

    Args:
        context: The context dictionary to sanitize

    Returns:
        Any: A new dictionary with sensitive values replaced
    """
    if not isinstance(context, dict):
        return context

    # Create a deep copy to avoid modifying the original
    sanitized = deepcopy(context)
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
        TributumError: The same error instance with enriched context

    Raises:
        TypeError: If error is not an instance of TributumError
    """
    if not isinstance(error, TributumError):
        raise TypeError("Error must be an instance of TributumError")

    if additional_context:
        # Merge contexts, with additional_context taking precedence
        error.context = {**error.context, **additional_context}

    return error


def capture_request_context(request: "Request | None") -> dict[str, Any]:
    """Capture HTTP request context for error reporting.

    Extracts relevant information from a FastAPI Request object,
    filtering out sensitive headers and sanitizing query parameters.

    Args:
        request: The FastAPI Request object, or None if not in HTTP context

    Returns:
        dict[str, Any]: Dictionary containing request context:
            - method: HTTP method
            - path: Request path
            - headers: Sanitized headers (sensitive headers removed)
            - query_params: Sanitized query parameters
            - client: Client information (host, port)
            Returns empty dict if request is None
    """
    if request is None:
        return {}

    context: dict[str, Any] = {}

    try:
        # Extract basic request info
        context["method"] = request.method
        context["path"] = str(request.url.path)

        # Extract and sanitize headers
        headers = {}
        for key, value in request.headers.items():
            if key.lower() not in SENSITIVE_HEADERS:
                headers[key] = value
            else:
                headers[key] = REDACTED
        context["headers"] = headers

        # Extract and sanitize query parameters
        if request.query_params:
            query_params = dict(request.query_params)
            context["query_params"] = sanitize_context({"params": query_params})[
                "params"
            ]

        # Extract client information
        if request.client:
            context["client"] = {
                "host": request.client.host,
                "port": request.client.port,
            }

        # Add URL information
        context["url"] = {
            "scheme": request.url.scheme,
            "hostname": request.url.hostname,
            "port": request.url.port,
            "path": request.url.path,
        }

    except (AttributeError, KeyError, TypeError):
        # If we can't extract request context due to missing attributes,
        # return what we have so far
        pass

    return context
