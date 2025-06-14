"""Error response models for API error handling.

This module defines the standardized error response format used across
all API endpoints to ensure consistent error communication to clients.
"""

from typing import Any

from pydantic import BaseModel, Field


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
                },
                {
                    "error_code": "NOT_FOUND",
                    "message": "User with ID 123 not found",
                    "correlation_id": "550e8400-e29b-41d4-a716-446655440001",
                },
                {
                    "error_code": "UNAUTHORIZED",
                    "message": "Invalid API key",
                },
            ]
        }
    }
