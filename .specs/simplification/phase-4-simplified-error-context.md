# Phase 4: Simplified Error Context

## Overview
This phase implements basic sensitive data sanitization for error logging. We're replacing 589 lines of complex pattern detection with ~50 lines that handle the common cases. For advanced needs (credit card validation, SSN detection), we recommend using cloud provider DLP APIs.

## Prerequisites
- Phase 3 completed (Cloud-agnostic formatters working)
- Logging infrastructure in place

## Objectives
1. Create simple sensitive field detection
2. Implement basic sanitization (redaction only)
3. Update error handler to use sanitization
4. Integrate with existing logging
5. Test sanitization functionality

## Implementation

### Step 1: Update Constants

Update `src/core/constants.py` to simplify sensitive patterns:
```python
# Remove the complex SENSITIVE_FIELD_PATTERNS list (19 patterns)
# It will be replaced with a simple regex in error_context.py

# Keep only:
REDACTED = "[REDACTED]"
```

Update `src/api/constants.py` (no changes needed):
```python
# Keep SENSITIVE_HEADERS as-is - will be used in error_context.py
SENSITIVE_HEADERS = {
    "authorization",
    "cookie",
    "x-api-key",
    # ... etc
}
```

### Step 2: Create Simplified Error Context Module

Create `src/core/error_context.py`:

```python
"""Error context management with basic sensitive data sanitization.

This simplified module provides basic protection against logging
sensitive data. For compliance-critical applications, use cloud
provider DLP APIs (GCP DLP, AWS Macie, Azure Purview).
"""

from __future__ import annotations

import re
from typing import Any, Final, Pattern

# Import constants from other modules
from src.api.constants import SENSITIVE_HEADERS
from src.core.constants import REDACTED

# Sensitive field patterns - covers common cases
SENSITIVE_FIELD_PATTERN: Final[Pattern[str]] = re.compile(
    r"(password|passwd|pwd|secret|token|api[_-]?key|apikey|auth|authorization|"
    r"credential|private[_-]?key|access[_-]?key|secret[_-]?key|session|"
    r"ssn|social[_-]?security|pin|cvv|cvc|card[_-]?number)",
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


def sanitize_value(value: Any, field_name: str = "", depth: int = 0) -> Any:
    """Sanitize a value if it appears to be sensitive.

    This function recursively sanitizes nested structures (dicts and lists)
    up to MAX_DEPTH to prevent infinite recursion.

    Args:
        value: The value to potentially sanitize.
        field_name: The field name for context.
        depth: Current recursion depth.

    Returns:
        Any: Sanitized value or original if not sensitive.
    """
    # Prevent infinite recursion
    if depth > MAX_DEPTH:
        return REDACTED

    # Check if field name indicates sensitive data
    if field_name and is_sensitive_field(field_name):
        return REDACTED

    # Recursively sanitize nested structures
    if isinstance(value, dict):
        return {
            k: sanitize_value(v, k, depth + 1)
            for k, v in value.items()
        }

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
    return {
        k: REDACTED if is_sensitive_header(k) else v
        for k, v in headers.items()
    }


def sanitize_error_context(error: Exception, context: dict[str, Any] | None = None) -> dict[str, Any]:
    """Create sanitized error context for logging.

    Args:
        error: The exception to create context for.
        context: Additional context to include (will be sanitized).

    Returns:
        dict[str, Any]: Sanitized error context safe for logging.
    """
    error_context = {
        "error_type": type(error).__name__,
        "error_message": str(error),
    }

    # Add sanitized additional context
    if context:
        error_context.update(sanitize_dict(context))

    # Add exception attributes if they exist (sanitized)
    if hasattr(error, "__dict__"):
        error_attrs = {
            k: v for k, v in error.__dict__.items()
            if not k.startswith("_")
        }
        if error_attrs:
            error_context["error_attributes"] = sanitize_dict(error_attrs)

    return error_context
```

### Step 2: Update Error Handler Middleware

Update `src/api/middleware/error_handler.py` to use sanitization:

```python
# Add import
from src.core.error_context import sanitize_error_context

# In exception handlers, update logging calls:
# Example for validation_error_handler
async def validation_error_handler(
    request: Request, exc: RequestValidationError
) -> ORJSONResponse:
    """Handle validation errors."""
    # ... existing code ...

    # Create sanitized error context
    error_context = sanitize_error_context(
        exc,
        {
            "path": request.url.path,
            "method": request.method,
            "errors": errors,  # Will be sanitized
        }
    )

    # Log with sanitized context
    logger.error(
        "Validation error",
        **error_context,
        correlation_id=correlation_id,
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
    )

    # ... rest of handler ...
```

### Step 3: Update Request Logging Middleware

Update `src/api/middleware/request_logging.py` to sanitize headers:

```python
# Add import
from src.core.error_context import sanitize_headers

# In dispatch method, when logging headers (if needed):
if self.log_config.log_headers:  # Add this config option
    sanitized_headers = sanitize_headers(dict(request.headers))
    logger.debug("Request headers", headers=sanitized_headers)
```

### Step 4: Create Tests

Create `tests/unit/core/test_error_context_simplified.py`:

```python
"""Tests for simplified error context sanitization."""

import pytest

from src.core.error_context import (
    REDACTED,
    is_sensitive_field,
    is_sensitive_header,
    sanitize_dict,
    sanitize_error_context,
    sanitize_headers,
    sanitize_value,
)


class TestSensitiveFieldDetection:
    """Test sensitive field detection."""

    @pytest.mark.parametrize("field_name,expected", [
        # Sensitive fields
        ("password", True),
        ("PASSWORD", True),
        ("user_password", True),
        ("passwordHash", True),
        ("secret", True),
        ("api_key", True),
        ("apiKey", True),
        ("api-key", True),
        ("authorization", True),
        ("auth_token", True),
        ("private_key", True),
        ("access_key", True),
        ("session_id", True),
        ("ssn", True),
        ("social_security", True),
        ("card_number", True),
        ("cvv", True),
        # Non-sensitive fields
        ("username", False),
        ("email", False),
        ("name", False),
        ("id", False),
        ("timestamp", False),
        ("message", False),
    ])
    def test_field_detection(self, field_name, expected):
        """Test field name detection."""
        assert is_sensitive_field(field_name) == expected

    def test_header_detection(self):
        """Test header name detection."""
        assert is_sensitive_header("Authorization")
        assert is_sensitive_header("AUTHORIZATION")
        assert is_sensitive_header("cookie")
        assert is_sensitive_header("X-API-Key")
        assert not is_sensitive_header("Content-Type")
        assert not is_sensitive_header("User-Agent")


class TestSanitization:
    """Test value sanitization."""

    def test_sanitize_simple_values(self):
        """Test sanitizing simple values."""
        # Sensitive field names cause redaction
        assert sanitize_value("my-secret-123", "password") == REDACTED
        assert sanitize_value("token123", "api_key") == REDACTED

        # Non-sensitive fields pass through
        assert sanitize_value("john@example.com", "email") == "john@example.com"
        assert sanitize_value(42, "user_id") == 42

    def test_sanitize_dict(self):
        """Test dictionary sanitization."""
        data = {
            "username": "john",
            "password": "secret123",
            "email": "john@example.com",
            "api_key": "sk-1234567890",
            "metadata": {
                "ip": "192.168.1.1",
                "session_token": "sess-abc123",
            }
        }

        sanitized = sanitize_dict(data)

        assert sanitized["username"] == "john"
        assert sanitized["password"] == REDACTED
        assert sanitized["email"] == "john@example.com"
        assert sanitized["api_key"] == REDACTED
        assert sanitized["metadata"]["ip"] == "192.168.1.1"
        assert sanitized["metadata"]["session_token"] == REDACTED

    def test_sanitize_list(self):
        """Test list sanitization."""
        data = {
            "users": [
                {"name": "John", "password": "secret1"},
                {"name": "Jane", "password": "secret2"},
            ]
        }

        sanitized = sanitize_dict(data)

        assert sanitized["users"][0]["name"] == "John"
        assert sanitized["users"][0]["password"] == REDACTED
        assert sanitized["users"][1]["name"] == "Jane"
        assert sanitized["users"][1]["password"] == REDACTED

    def test_sanitize_nested_structures(self):
        """Test deeply nested structure sanitization."""
        data = {
            "level1": {
                "level2": {
                    "level3": {
                        "secret_key": "very-secret",
                        "public_data": "visible",
                    }
                }
            }
        }

        sanitized = sanitize_dict(data)

        assert sanitized["level1"]["level2"]["level3"]["secret_key"] == REDACTED
        assert sanitized["level1"]["level2"]["level3"]["public_data"] == "visible"

    def test_max_depth_protection(self):
        """Test maximum depth protection."""
        # Create circular reference
        data: dict[str, Any] = {"name": "test"}
        data["self"] = data

        # Should not crash, should handle gracefully
        sanitized = sanitize_dict(data)
        assert sanitized["name"] == "test"

    def test_sanitize_headers(self):
        """Test header sanitization."""
        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer token123",
            "X-API-Key": "sk-secret",
            "User-Agent": "Mozilla/5.0",
            "Cookie": "session=abc123",
        }

        sanitized = sanitize_headers(headers)

        assert sanitized["Content-Type"] == "application/json"
        assert sanitized["Authorization"] == REDACTED
        assert sanitized["X-API-Key"] == REDACTED
        assert sanitized["User-Agent"] == "Mozilla/5.0"
        assert sanitized["Cookie"] == REDACTED


class TestErrorContext:
    """Test error context sanitization."""

    def test_basic_error_context(self):
        """Test basic error context creation."""
        error = ValueError("Something went wrong")
        context = sanitize_error_context(error)

        assert context["error_type"] == "ValueError"
        assert context["error_message"] == "Something went wrong"

    def test_error_context_with_additional_context(self):
        """Test error context with additional data."""
        error = ValueError("Invalid input")
        additional = {
            "user_id": 123,
            "password": "should-be-hidden",
            "action": "login",
        }

        context = sanitize_error_context(error, additional)

        assert context["error_type"] == "ValueError"
        assert context["user_id"] == 123
        assert context["password"] == REDACTED
        assert context["action"] == "login"

    def test_error_with_attributes(self):
        """Test error with custom attributes."""
        class CustomError(Exception):
            def __init__(self, message, code, secret_data):
                super().__init__(message)
                self.code = code
                self.secret_data = secret_data

        error = CustomError("Custom error", "ERR001", "sensitive")
        context = sanitize_error_context(error)

        assert context["error_type"] == "CustomError"
        assert context["error_attributes"]["code"] == "ERR001"
        assert context["error_attributes"]["secret_data"] == REDACTED


class TestIntegration:
    """Test integration with logging."""

    def test_logging_with_sanitization(self, caplog):
        """Test that sanitization works with logging."""
        from loguru import logger

        # Create error with sensitive context
        try:
            raise ValueError("Database connection failed")
        except ValueError as e:
            context = sanitize_error_context(
                e,
                {
                    "database_url": "postgresql://user:password@localhost/db",
                    "connection_string": "should-be-hidden",
                }
            )

            logger.error("Operation failed", **context)

        # Sensitive data should not appear in logs
        log_output = caplog.text
        assert "password" not in log_output
        assert REDACTED in log_output
```

### Step 5: Update Configuration (Optional)

If you want to make sensitive patterns configurable, update `src/core/config.py`:

```python
# In LogConfig class, optionally add:
additional_sensitive_patterns: list[str] = Field(
    default_factory=list,
    description="Additional regex patterns for sensitive field detection",
)
```

## Validation Checklist

- [ ] **Constants updated in src/core/constants.py**
- [ ] **SENSITIVE_FIELD_PATTERNS removed from constants**
- [ ] **REDACTED constant imported from core.constants**
- [ ] **SENSITIVE_HEADERS imported from api.constants**
- [ ] Error context module created (~50 lines)
- [ ] Basic sensitive field detection working
- [ ] Nested structure sanitization implemented
- [ ] Headers sanitization working
- [ ] Error handler updated to use sanitization
- [ ] No complex patterns (credit cards, SSN, etc.)
- [ ] Tests cover all sanitization cases
- [ ] Integration with logging verified
- [ ] `make lint` passes
- [ ] `make type-check` passes

## Expected Results

After Phase 4:
- Basic protection against logging passwords, tokens, keys
- Simple redaction strategy (no masking/hashing)
- Clean integration with existing logging
- ~40-50 tests for sanitization
- 91% reduction in code (50 lines vs 589)

## Testing Sanitization

```python
# Example: Test in development
from loguru import logger
from src.core.error_context import sanitize_dict

# This should redact sensitive fields
data = {
    "user": "john",
    "password": "secret123",
    "api_key": "sk-12345",
}

logger.info("User data", **sanitize_dict(data))
# Output: User data | user=john password=[REDACTED] api_key=[REDACTED]
```

## Cloud Provider DLP Integration (Future)

For compliance-critical applications, integrate cloud DLP APIs:

### GCP DLP API Example
```python
# Future enhancement - not part of Phase 4
from google.cloud import dlp_v2

def sanitize_with_dlp(text: str) -> str:
    """Use GCP DLP API for advanced detection."""
    dlp = dlp_v2.DlpServiceClient()

    # Detect credit cards, SSNs, etc.
    response = dlp.inspect_content(
        request={
            "parent": f"projects/{project_id}/locations/global",
            "inspect_config": {
                "info_types": [
                    {"name": "CREDIT_CARD_NUMBER"},
                    {"name": "US_SOCIAL_SECURITY_NUMBER"},
                    {"name": "EMAIL_ADDRESS"},
                ]
            },
            "item": {"value": text},
        }
    )

    # Redact findings
    for finding in response.result.findings:
        # Implement redaction logic
        pass
```

## Notes for Next Phases

- Phase 5 will add OpenTelemetry tracing
- Current sanitization is sufficient for most applications
- Keep it simple - avoid over-engineering
- Cloud DLP APIs available when needed

## Performance Considerations

- Regex compilation happens once (module level)
- Recursion limited by MAX_DEPTH
- No expensive operations (Luhn algorithm, etc.)
- Sanitization is fast enough for synchronous use

## Common Patterns to Remember

```python
# Always sanitize error context
try:
    risky_operation()
except Exception as e:
    context = sanitize_error_context(e, {"request": request_data})
    logger.error("Operation failed", **context)

# Sanitize before logging user data
user_data = get_user_data()
logger.info("User updated", **sanitize_dict(user_data))

# Sanitize headers when logging
headers = sanitize_headers(request.headers)
logger.debug("Request headers", headers=headers)
```
