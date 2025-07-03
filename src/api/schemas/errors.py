"""Standardized error response schemas for consistent API error handling.

This module defines Pydantic models that structure all error responses
returned by the API, ensuring clients receive predictable, well-documented
error information regardless of the error type.

Key models:
- **ErrorResponse**: Main error response with all metadata fields
- **ServiceInfo**: Service identification for multi-service debugging

The error schema supports:
- Machine-readable error codes for programmatic handling
- Human-readable messages for user display
- Correlation IDs for distributed tracing
- Debug information in development environments
- Field-level validation error details

All timestamp fields include timezone information for proper
internationalization support.
"""

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class ServiceInfo(BaseModel):
    """Service information for error context.

    Provides metadata about the service that generated the error,
    useful for debugging in multi-service environments.
    """

    name: str = Field(
        ...,
        description="Name of the service",
        examples=["Tributum", "PaymentService"],
    )

    version: str = Field(
        ...,
        description="Version of the service",
        examples=["0.1.0", "1.2.3"],
    )

    environment: str = Field(
        ...,
        description="Environment where the service is running",
        examples=["development", "staging", "production"],
    )


class ErrorResponse(BaseModel):
    """Standardized error response model for API errors.

    This model ensures all API errors follow a consistent structure,
    making it easier for clients to handle errors programmatically.
    """

    error_code: str = Field(
        ...,
        description="Unique error code identifying the error type",
        examples=["VALIDATION_ERROR", "NOT_FOUND", "UNAUTHORIZED"],
    )

    message: str = Field(
        ...,
        description="Human-readable error message",
        examples=["Invalid email format", "User not found", "Invalid credentials"],
    )

    details: dict[str, Any] | None = Field(
        default=None,
        description="Additional error details (e.g., field-specific validation errors)",
        examples=[{"field": "email", "reason": "Invalid format"}],
    )

    correlation_id: str | None = Field(
        default=None,
        description="Request correlation ID for tracing and debugging",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )

    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp when the error occurred (with timezone)",
        examples=["2024-06-14T12:00:00+00:00"],
    )

    severity: str | None = Field(
        default=None,
        description="Error severity level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
        examples=["ERROR", "WARNING"],
    )

    service_info: ServiceInfo | None = Field(
        default=None,
        description="Information about the service that generated the error",
        examples=[
            {
                "name": "Tributum",
                "version": "0.1.0",
                "environment": "production",
            }
        ],
    )

    request_id: str | None = Field(
        default=None,
        description=(
            "Unique request identifier (different from correlation_id "
            "which can span multiple services)"
        ),
        examples=["req-550e8400-e29b-41d4-a716-446655440000"],
    )

    debug_info: dict[str, Any] | None = Field(
        default=None,
        description="Debug information (only populated in development environments)",
        examples=[
            {
                "stack_trace": ["File 'main.py', line 123, in function_name"],
                "error_context": {"user_id": 123, "action": "create_order"},
                "exception_type": "ValidationError",
            }
        ],
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "error_code": "VALIDATION_ERROR",
                    "message": "Invalid input data",
                    "details": {
                        "email": "Invalid email format",
                        "age": "Must be a positive integer",
                    },
                    "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
                    "request_id": "req-660e8400-e29b-41d4-a716-446655440000",
                    "timestamp": "2024-06-14T12:00:00+00:00",
                    "severity": "WARNING",
                    "service_info": {
                        "name": "Tributum",
                        "version": "0.1.0",
                        "environment": "production",
                    },
                },
                {
                    "error_code": "NOT_FOUND",
                    "message": "User with ID 123 not found",
                    "correlation_id": "550e8400-e29b-41d4-a716-446655440001",
                    "request_id": "req-660e8400-e29b-41d4-a716-446655440001",
                    "timestamp": "2024-06-14T12:00:01+00:00",
                    "severity": "WARNING",
                    "service_info": {
                        "name": "Tributum",
                        "version": "0.1.0",
                        "environment": "staging",
                    },
                },
                {
                    "error_code": "UNAUTHORIZED",
                    "message": "Invalid API key",
                    "timestamp": "2024-06-14T12:00:02+00:00",
                    "severity": "ERROR",
                },
                {
                    "error_code": "INTERNAL_ERROR",
                    "message": "Internal server error: ValueError",
                    "correlation_id": "550e8400-e29b-41d4-a716-446655440002",
                    "request_id": "req-660e8400-e29b-41d4-a716-446655440002",
                    "timestamp": "2024-06-14T12:00:03+00:00",
                    "severity": "CRITICAL",
                    "debug_info": {
                        "stack_trace": [
                            "Traceback (most recent call last):",
                            "  File '/app/main.py', line 123, in process_request",
                            "    result = calculate_value(data)",
                            "ValueError: Invalid calculation parameters",
                        ],
                        "error_context": {"user_id": 456, "action": "calculate_tax"},
                        "exception_type": "ValueError",
                    },
                    "service_info": {
                        "name": "Tributum",
                        "version": "0.1.0",
                        "environment": "development",
                    },
                },
            ]
        }
    }
