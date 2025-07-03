"""Type aliases for dynamic data structures throughout the application.

This module centralizes type definitions for data that cannot be statically
typed, providing clear semantic meaning and documentation for these types.

The type aliases serve several purposes:
- **Documentation**: Clear intent about what kind of data is expected
- **Type safety**: Enable static type checkers to catch misuse
- **Maintainability**: Single source of truth for type definitions
- **IDE support**: Better autocomplete and type hints

All types defined here should be JSON-serializable to support logging,
API responses, and persistence layers.
"""

from typing import Any

# JSON-compatible type that represents any valid JSON value
# Used for API responses, request bodies, and serialization
type JsonValue = (
    dict[str, "JsonValue"] | list["JsonValue"] | str | int | float | bool | None
)

# Context dictionary for logging additional information
# Values must be JSON-serializable for structured logging
type LogContext = dict[str, Any]  # JSON-serializable values

# Context dictionary for error details and debugging information
# Values must be JSON-serializable for API responses
type ErrorContext = dict[str, Any]  # flexible error context

# ASGI scope type for middleware implementations
# Following ASGI spec: https://asgi.readthedocs.io/en/latest/specs/www.html
type AsgiScope = dict[str, Any]  # ASGI spec defines various types

# Performance thresholds configuration type
# Used for request monitoring and alerting
type PerformanceThresholds = dict[str, int | float]  # threshold values in ms
