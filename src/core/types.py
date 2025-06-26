"""Type aliases for common dynamic types used across the application.

This module provides type aliases for cases where dynamic typing is necessary,
such as JSON data, logging contexts, and error details. These aliases improve
code clarity by explicitly documenting the expected structure and constraints.
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
