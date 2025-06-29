# Phase 1: Core Logging with Loguru

## Overview
This phase introduces Loguru as the core logging library and sets up basic logging functionality. We'll create a minimal `src/core/logging.py` module and update all imports throughout the codebase.

## Prerequisites
- Phase 0 completed (all old logging code removed)
- Standard library logging temporarily in use

## Objectives
1. Add Loguru dependency
2. Create minimal logging module with basic Loguru setup
3. Update all imports from standard logging to Loguru
4. Set up basic console logging for development
5. Ensure async safety with `enqueue=True`
6. Create basic tests for Loguru configuration

## Implementation

### Step 1: Add Loguru Dependency

Update `pyproject.toml`:
```toml
dependencies = [
    # ... existing dependencies ...
    "loguru>=0.7.2",  # Add this line
    # ... rest of dependencies ...
]
```

Run:
```bash
uv sync --all-extras --dev
```

### Step 2: Update Configuration

Update `.env.example` to use new setting names:
```bash
# Old (from Phase 0)
LOG_CONFIG__LOG_FORMAT=console

# New (Phase 1)
LOG_CONFIG__LOG_FORMATTER_TYPE=console  # Options: console, json, gcp, aws
```

### Step 3: Create Basic Logging Module

Create `src/core/logging.py` with the complete implementation:
```python
"""Logging configuration using Loguru with full type safety and GCP integration."""

from __future__ import annotations

import json
import logging
import sys
from collections.abc import Mapping
from functools import lru_cache
from typing import TYPE_CHECKING, Any, ClassVar, Final, TypeAlias

from loguru import logger

if TYPE_CHECKING:
    from loguru import FilterDict, FormatFunction, Record

    from src.core.config import Settings

# Type aliases for clarity
LogLevel: TypeAlias = str
CorrelationID: TypeAlias = str
LogContext: TypeAlias = dict[str, Any]

# Constants
DEFAULT_LOG_FORMAT: Final[str] = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
    "{message}"
)

class InterceptHandler(logging.Handler):
    """Intercept standard logging and redirect to Loguru.

    This handler captures logs from libraries using standard logging
    and forwards them to Loguru for consistent formatting.
    """

    def emit(self, record: logging.LogRecord) -> None:
        """Forward log record to Loguru.

        Args:
            record: Standard library LogRecord to forward.
        """
        # Find caller from where originated the logged message
        frame, depth = sys._getframe(6), 6
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            record.levelname, record.getMessage()
        )


def should_log_path(record: dict[str, Any]) -> bool:
    """Filter out excluded paths from logs.

    Args:
        record: Loguru record dictionary.

    Returns:
        bool: True if the path should be logged.
    """
    # Implementation would check against excluded_paths from settings
    return True


@lru_cache(maxsize=1)
def setup_logging(settings: Settings) -> None:
    """Configure Loguru for the application.

    This is a basic setup for Phase 1. Cloud-specific formatters
    will be added in Phase 3.

    Args:
        settings: Application settings containing log configuration.

    Note:
        This function uses lru_cache to ensure it's only called once.
    """
    # Remove default handler
    logger.remove()

    # Add console handler with development-friendly format
    logger.add(
        sys.stdout,
        format=DEFAULT_LOG_FORMAT,
        level=settings.log_config.log_level,
        enqueue=True,  # Thread-safe async logging
        colorize=True,  # Colored output for development
        diagnose=settings.debug,  # Include variable values in tracebacks
        backtrace=settings.debug,  # Include full traceback
    )

    # Configure standard library logging to use Loguru
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)

    # Disable noisy loggers
    for logger_name in ["uvicorn.access", "urllib3.connectionpool"]:
        logging.getLogger(logger_name).disabled = True


def bind_context(**kwargs: Any) -> None:
    """Bind context variables to the logger.

    Args:
        **kwargs: Context variables to bind.

    Example:
        >>> bind_context(user_id=123, request_id="abc")
    """
    logger.configure(extra=kwargs)


def get_logger(name: str) -> Any:  # Returns loguru.Logger but can't import at module level
    """Get a logger instance with the given name.

    Args:
        name: Logger name, typically __name__.

    Returns:
        Logger instance bound with the name.
    """
    return logger.bind(logger_name=name)
```

### Step 3: Update Application Initialization

Update `src/api/main.py`:
```python
# Add to imports
from src.core.logging import setup_logging

# In create_app function, before creating FastAPI instance:
def create_app(settings: Settings | None = None) -> FastAPI:
    """Create and configure the FastAPI application."""
    if settings is None:
        settings = get_settings()

    # Setup logging first
    setup_logging(settings)

    # ... rest of the function
```

Update `main.py` (root):
```python
# Add to imports
from src.core.logging import setup_logging

def main() -> None:
    """Main entry point for the Tributum application."""
    settings = get_settings()

    # Setup logging first
    setup_logging(settings)

    # ... rest of the function
```

### Step 4: Create Migration Script

Create `scripts/phase1_migrate_imports.py`:
```python
#!/usr/bin/env python3
"""Phase 1: Migrate from standard logging to Loguru."""

import re
from pathlib import Path

def update_imports(file_path: Path) -> bool:
    """Update imports to use Loguru."""
    content = file_path.read_text()
    original = content

    # Replace standard logging imports with loguru
    content = re.sub(
        r'import logging\s*\n\s*logger = logging\.getLogger\(__name__\)',
        'from loguru import logger',
        content,
        flags=re.MULTILINE
    )

    # Also handle any remaining get_logger patterns from TODO comments
    content = re.sub(
        r'# TODO: Will be replaced with loguru in Phase 1\s*\n\s*import logging\s*\n\s*logger = logging\.getLogger\(__name__\)',
        'from loguru import logger',
        content,
        flags=re.MULTILINE
    )

    # Clean up TODO comments from Phase 0
    content = re.sub(
        r'# TODO: Remove this import - Phase 0 cleanup\s*\n',
        '',
        content,
        flags=re.MULTILINE
    )

    if content != original:
        file_path.write_text(content)
        return True
    return False

def main():
    """Run Phase 1 import migration."""
    print("Phase 1: Loguru Import Migration")
    print("=" * 50)

    # Update imports in src
    updated = 0
    for file_path in Path("src").rglob("*.py"):
        if file_path.name == "logging.py":
            continue  # Skip our logging module
        if update_imports(file_path):
            print(f"Updated: {file_path}")
            updated += 1

    # Update imports in tests
    for file_path in Path("tests").rglob("*.py"):
        if update_imports(file_path):
            print(f"Updated: {file_path}")
            updated += 1

    print(f"\nTotal files updated: {updated}")

if __name__ == "__main__":
    main()
```

### Step 5: Create Basic Tests

Create `tests/unit/core/test_logging_basic.py`:
```python
"""Basic tests for Loguru logging configuration."""

import sys
from io import StringIO
from unittest.mock import patch

import pytest
from loguru import logger

from src.core.config import Settings
from src.core.logging import setup_logging, get_logger


class TestLoggingSetup:
    """Test basic logging setup."""

    @pytest.fixture(autouse=True)
    def cleanup_logger(self):
        """Clean up logger handlers after each test."""
        # Store current handlers
        handlers = list(logger._core.handlers.values())
        yield
        # Remove all handlers and restore
        logger.remove()
        for handler in handlers:
            logger.add(**handler)

    def test_setup_logging_basic(self):
        """Test basic logging setup."""
        settings = Settings(
            log_config={"log_level": "INFO"}
        )

        # Remove existing handlers
        logger.remove()

        # Setup logging
        setup_logging(settings)

        # Create string buffer to capture output
        output = StringIO()

        # Add test handler
        logger.add(output, format="{level} | {message}", level="INFO")

        # Test logging
        logger.info("Test message")

        # Check output
        assert "INFO | Test message" in output.getvalue()

    def test_get_logger_compatibility(self):
        """Test get_logger function for backward compatibility."""
        test_logger = get_logger("test.module")

        # Should return a bound logger
        assert hasattr(test_logger, "info")
        assert hasattr(test_logger, "error")
        assert hasattr(test_logger, "debug")

    def test_log_levels(self):
        """Test different log levels."""
        settings = Settings(
            log_config={"log_level": "WARNING"}
        )

        logger.remove()
        setup_logging(settings)

        # Create string buffer
        output = StringIO()
        logger.add(output, format="{level} | {message}", level="WARNING")

        # Test different levels
        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")

        output_text = output.getvalue()

        # Only WARNING and ERROR should appear
        assert "Debug message" not in output_text
        assert "Info message" not in output_text
        assert "WARNING | Warning message" in output_text
        assert "ERROR | Error message" in output_text

    def test_exception_logging(self):
        """Test exception logging."""
        output = StringIO()
        logger.remove()
        logger.add(output, format="{level} | {message}", level="ERROR")

        try:
            raise ValueError("Test error")
        except ValueError:
            logger.exception("Error occurred")

        output_text = output.getvalue()
        assert "ERROR | Error occurred" in output_text
        assert "ValueError: Test error" in output_text

    @pytest.mark.asyncio
    async def test_async_logging(self):
        """Test logging in async context."""
        output = StringIO()
        logger.remove()
        logger.add(output, format="{message}", level="INFO", enqueue=True)

        async def async_function():
            logger.info("Async log message")

        await async_function()

        # Allow time for enqueued message
        import asyncio
        await asyncio.sleep(0.1)

        assert "Async log message" in output.getvalue()


class TestInterceptHandler:
    """Test standard library logging interception."""

    def test_standard_library_interception(self):
        """Test that standard library logs are captured."""
        import logging as std_logging

        # Setup logging
        settings = Settings()
        logger.remove()
        setup_logging(settings)

        # Create string buffer
        output = StringIO()
        logger.add(output, format="{message}", level="INFO")

        # Use standard library logger
        std_logger = std_logging.getLogger("test.stdlib")
        std_logger.info("Standard library message")

        assert "Standard library message" in output.getvalue()
```

### Step 6: Update Error Handler

Update `src/api/middleware/error_handler.py` to use Loguru:
```python
# Update import
from loguru import logger

# Update error logging (example)
logger.error(
    f"Handled {type(exc).__name__}",
    error_code=error_response.error_code,
    status_code=status_code,
    correlation_id=error_response.correlation_id,
)
```

## Import Migration Patterns

From the specification, here are the key import changes:

### Logging Imports
```python
# Old imports
from src.core.logging import get_logger
logger = get_logger(__name__)

# New imports
from loguru import logger
# No need to create a logger instance - Loguru provides a global logger
```

### Context Binding
```python
# Old context binding
from src.core.logging import bind_logger_context, layered_context
bind_logger_context(user_id=123, request_id="abc")
with layered_context(operation="database_query"):
    # do something

# New context binding
from loguru import logger
logger.bind(user_id=123, request_id="abc")
with logger.contextualize(operation="database_query"):
    # do something
```

### Error Logging
```python
# Old way
logger.error("Operation failed", exc_info=True, error_context=error_dict)

# New way
logger.exception("Operation failed", **error_dict)
# or
logger.error("Operation failed", exception=True, **error_dict)
```

### Exception Logging Utility
```python
# Old way - using utility function
from src.core.logging import log_exception
log_exception(logger, exc, "Operation failed", extra_context={"user_id": 123})

# New way - use logger.exception directly
logger.exception("Operation failed", user_id=123)
# The exception is automatically captured from the current context
```

### Structured Logging
```python
# Old way
logger.info("User action", user_id=123, action="login", duration_ms=150)

# New way (identical!)
logger.info("User action", user_id=123, action="login", duration_ms=150)
```

### Getting Logger Context
```python
# Old way
from src.core.logging import get_logger_context
context = get_logger_context()

# New way
# Context is automatically included in log records
# Access via record["extra"] in format functions
```

## Validation Checklist

- [ ] Loguru added to dependencies
- [ ] `src/core/logging.py` created with basic setup
- [ ] All imports updated from standard logging to Loguru
- [ ] Application initialization updated to setup logging
- [ ] Basic tests created and passing
- [ ] Console output shows colored, formatted logs
- [ ] Standard library logs are intercepted
- [ ] Async logging works correctly
- [ ] **.env.example updated with LOG_FORMATTER_TYPE**
- [ ] **All .env files updated to use new setting name**
- [ ] `make lint` passes
- [ ] `make type-check` passes
- [ ] `make test` passes

## Expected Results

After Phase 1:
- Basic logging functionality restored with Loguru
- Colored console output for development
- All modules using `from loguru import logger`
- Standard library logs captured and formatted
- ~10-15 basic logging tests passing

## Migration Commands

```bash
# Add dependency
uv sync --all-extras --dev

# Run migration script
python scripts/phase1_migrate_imports.py

# Run tests
make test-unit

# Check code quality
make lint
make type-check
```

## Notes for Next Phases

- Phase 2 will integrate with RequestContextMiddleware for correlation IDs
- Phase 3 will add cloud-specific formatters (GCP, AWS, etc.)
- Current setup is console-only, perfect for development
- No cloud dependencies required yet

## Troubleshooting

### Import Errors
If you see import errors:
```bash
# Ensure Loguru is installed
uv sync --all-extras --dev

# Check for circular imports
python -c "from src.core.logging import setup_logging"
```

### Type Checking Issues
Loguru has dynamic attributes, so MyPy might complain:
```python
# Add type ignore if needed
logger.info("Message")  # type: ignore[attr-defined]
```

### Test Failures
If tests fail due to logger handlers:
- Ensure cleanup fixture is used
- Use `logger.remove()` before adding test handlers
- Don't modify global logger state without cleanup

## Common Pitfalls to Avoid

From the specification, here are important anti-patterns and their solutions:

### 1. Context Manager Misuse
**Wrong**:
```python
# This creates a new logger instance, doesn't affect global logger
logger = logger.bind(request_id="123")
```

**Right**:
```python
# Use contextualize for request-scoped data
with logger.contextualize(request_id="123"):
    process_request()
```

### 2. Handler Cleanup in Tests
**Wrong**:
```python
def test_something():
    logger.add(custom_handler)
    # Forgot to remove handler - affects other tests
```

**Right**:
```python
def test_something():
    handler_id = logger.add(custom_handler)
    try:
        # test code
    finally:
        logger.remove(handler_id)
```

### 3. Forgetting InterceptHandler
**Wrong**:
```python
# Standard library logs won't be captured
setup_logging()
```

**Right**:
```python
# Configure standard logging to use Loguru
logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
```

### 4. Import Order Issues
**Wrong**:
```python
# Configure logging after imports
from src.api.main import app
setup_logging()  # Too late!
```

**Right**:
```python
# Configure logging before other imports
setup_logging()
from src.api.main import app
```
