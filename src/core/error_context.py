"""Utilities for error context management and sanitization.

This module provides functions to enrich errors with additional context
and sanitize sensitive data from error contexts before logging or display.
"""

import re
from copy import deepcopy
from typing import TYPE_CHECKING, Any, TypeVar, overload

from src.api.constants import SENSITIVE_HEADERS
from src.core.constants import REDACTED, SENSITIVE_FIELD_PATTERNS
from src.core.exceptions import TributumError

# Constants for credit card validation
_MIN_CREDIT_CARD_LENGTH = 13
_LUHN_SINGLE_DIGIT_MAX = 9

# Compiled regex patterns for sensitive value detection (for performance)
_CREDIT_CARD_PATTERN = re.compile(r"\b(?:\d[ -]*?){13,19}\b", re.IGNORECASE)
_EMAIL_PATTERN = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", re.IGNORECASE
)
_PHONE_PATTERN = re.compile(
    r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b", re.IGNORECASE
)
_UUID_PATTERN = re.compile(
    r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b",
    re.IGNORECASE,
)
_JWT_PATTERN = re.compile(
    r"\b[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+\b", re.IGNORECASE
)

if TYPE_CHECKING:  # pragma: no cover
    # TYPE_CHECKING is False at runtime; used only for static type analysis
    from fastapi import Request

    from src.core.config import LogConfig

T = TypeVar("T")


def _get_log_config() -> "LogConfig":
    """Get the current logging configuration.

    Returns:
        LogConfig: Current logging configuration instance
    """
    # Import here to avoid circular imports with the global config module
    # This is acceptable as it's only called when sanitization is needed
    from src.core.config import get_settings  # noqa: PLC0415

    return get_settings().log_config


def _luhn_check(card_number: str) -> bool:
    """Validate a credit card number using the Luhn algorithm.

    Args:
        card_number: Credit card number string (may contain spaces/dashes)

    Returns:
        bool: True if the number passes Luhn validation
    """
    # Remove all non-digit characters
    digits = re.sub(r"\D", "", card_number)

    # Need at least minimum digits for a valid credit card
    if len(digits) < _MIN_CREDIT_CARD_LENGTH:
        return False

    # Reject obviously invalid patterns
    if digits == "0" * len(digits):  # All zeros
        return False
    if len(set(digits)) == 1:  # All same digit
        return False

    # Luhn algorithm implementation
    total = 0
    reverse_digits = digits[::-1]

    for i, digit in enumerate(reverse_digits):
        n = int(digit)
        if i % 2 == 1:  # Every second digit from right
            n *= 2
            if n > _LUHN_SINGLE_DIGIT_MAX:
                n = n // 10 + n % 10
        total += n

    return total % 10 == 0


def detect_sensitive_value(value: str) -> bool:
    """Detect if a string value contains sensitive data patterns.

    Checks for common sensitive data formats including credit cards (with Luhn
    validation), emails, phone numbers, UUIDs, and JWTs.

    Args:
        value: String value to check for sensitive patterns

    Returns:
        bool: True if the value matches any sensitive pattern
    """
    if not isinstance(value, str) or not value.strip():
        return False

    # Check for credit card pattern and validate with Luhn
    if _CREDIT_CARD_PATTERN.search(value):
        # Extract potential card numbers and validate each
        potential_cards = _CREDIT_CARD_PATTERN.findall(value)
        for card in potential_cards:
            if _luhn_check(card):
                return True

    # Check other patterns and return immediately if found
    return bool(
        _EMAIL_PATTERN.search(value)
        or _PHONE_PATTERN.search(value)
        or _UUID_PATTERN.search(value)
        or _JWT_PATTERN.search(value)
    )


def is_sensitive_field(field_name: str) -> bool:
    """Check if a field name matches sensitive patterns.

    Args:
        field_name: The field name to check

    Returns:
        bool: True if the field name matches any sensitive pattern
    """
    field_lower = field_name.lower()
    return any(re.match(pattern, field_lower) for pattern in SENSITIVE_FIELD_PATTERNS)


def _sanitize_dict(data: dict[str, Any], log_config: "LogConfig | None" = None) -> None:
    """Recursively sanitize a dictionary in place.

    Args:
        data: Dictionary to sanitize in place
        log_config: Optional logging configuration for enhanced sanitization
    """
    if log_config is None:
        log_config = _get_log_config()

    for key in list(data.keys()):  # Use list() to avoid mutation during iteration
        value = data[key]

        # Check if field is excluded from sanitization
        if key in log_config.excluded_fields_from_sanitization:
            continue

        # Primary detection: field name patterns (existing behavior)
        if is_sensitive_field(key):  # noqa: SIM114
            data[key] = REDACTED
        # Secondary detection: value patterns (new behavior)
        elif (
            log_config.sensitive_value_detection
            and isinstance(value, str)
            and detect_sensitive_value(value)
        ):
            data[key] = REDACTED
        elif isinstance(value, dict):
            _sanitize_dict(value, log_config)
        elif isinstance(value, list):
            _sanitize_list(value, log_config)


def _sanitize_list(data: list[Any], log_config: "LogConfig | None" = None) -> None:
    """Recursively sanitize items in a list.

    Args:
        data: List to sanitize recursively
        log_config: Optional logging configuration for enhanced sanitization
    """
    if log_config is None:
        log_config = _get_log_config()

    for item in data:
        if isinstance(item, dict):
            _sanitize_dict(item, log_config)
        elif isinstance(item, list):
            _sanitize_list(item, log_config)


@overload
def sanitize_context(context: dict[str, Any]) -> dict[str, Any]: ...


@overload
def sanitize_context[T2](context: T2) -> T2: ...


def sanitize_context(context: Any) -> Any:
    """Remove sensitive data from a context dictionary.

    Creates a deep copy of the context and replaces any sensitive values
    with a redacted placeholder. Handles nested dictionaries recursively.

    Enhanced to detect sensitive data in values (credit cards, emails, etc.)
    in addition to field name patterns. Configuration is automatically
    loaded from the current application settings.

    Args:
        context: The context dictionary to sanitize

    Returns:
        Any: A new dictionary with sensitive values replaced
    """
    if not isinstance(context, dict):
        return context

    # Create a deep copy to avoid modifying the original
    sanitized = deepcopy(context)

    # Get current configuration for enhanced sanitization
    log_config = _get_log_config()
    _sanitize_dict(sanitized, log_config)

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
