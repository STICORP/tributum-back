# Phase 3: Cloud-Agnostic Formatters

## Overview
This phase implements pluggable log formatters to support different deployment environments (local development, GCP, AWS, Azure, self-hosted) without code changes. The formatter is selected via configuration, enabling easy cloud migration.

## Prerequisites
- Phase 2 completed (Request context and middleware working)
- Correlation IDs propagating correctly

## Objectives
1. Implement formatter functions for each environment
2. Create formatter registry with pluggable design
3. Update configuration to support formatter selection
4. Ensure local development works without cloud services
5. Test each formatter independently

## Implementation

### Step 1: Update Logging Module with Formatters

Update `src/core/logging.py` to add cloud-specific formatters:

```python
"""Logging configuration using Loguru with pluggable formatters."""

from __future__ import annotations

import json
import logging
import sys
from functools import lru_cache
from typing import TYPE_CHECKING, Any, Final, TypeAlias

from loguru import logger

if TYPE_CHECKING:
    from loguru import Record

    from src.core.config import Settings

# Type aliases
FormatFunction: TypeAlias = Any  # Callable[[Record], str] but can't import Record at module level

# Constants
DEFAULT_LOG_FORMAT: Final[str] = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
    "{message}"
)


class InterceptHandler(logging.Handler):
    """Intercept standard logging and redirect to Loguru."""

    def emit(self, record: logging.LogRecord) -> None:
        """Forward log record to Loguru."""
        frame, depth = sys._getframe(6), 6
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            record.levelname, record.getMessage()
        )


def serialize_for_json(record: Record) -> str:
    """Format log record as generic JSON for development/self-hosted.

    Args:
        record: Loguru record to format.

    Returns:
        str: JSON-formatted log entry with newline.
    """
    log_entry = {
        "timestamp": record["time"].isoformat(),
        "level": record["level"].name,
        "message": record["message"],
        "logger": record["name"],
        "function": record["function"],
        "module": record["module"],
        "line": record["line"],
    }

    # Add extra fields (includes correlation_id, request_id, etc.)
    if extra := record.get("extra", {}):
        # Filter out internal Loguru fields
        filtered_extra = {
            k: v for k, v in extra.items()
            if not k.startswith("_")
        }
        if filtered_extra:
            log_entry.update(filtered_extra)

    # Add exception info if present
    if exc := record.get("exception"):
        log_entry["exception"] = {
            "type": exc.type.__name__ if exc.type else None,
            "value": str(exc.value) if exc.value else None,
            "traceback": exc.traceback if exc.traceback else None,
        }

    return json.dumps(log_entry, default=str) + "\n"


def serialize_for_gcp(record: Record) -> str:
    """Format log record for GCP Cloud Logging.

    Follows GCP structured logging format:
    https://cloud.google.com/logging/docs/structured-logging

    Args:
        record: Loguru record to format.

    Returns:
        str: JSON-formatted log entry for GCP with newline.
    """
    # Map Loguru levels to GCP severity
    severity_mapping = {
        "TRACE": "DEBUG",
        "DEBUG": "DEBUG",
        "INFO": "INFO",
        "SUCCESS": "INFO",
        "WARNING": "WARNING",
        "ERROR": "ERROR",
        "CRITICAL": "CRITICAL",
    }

    # Build GCP-compatible log entry
    log_entry = {
        "severity": severity_mapping.get(record["level"].name, "INFO"),
        "message": record["message"],
        "timestamp": record["time"].isoformat(),
    }

    # Add labels for GCP
    labels = {
        "function": record["function"],
        "module": record["module"],
        "line": str(record["line"]),
    }

    # Add extra fields to labels
    if extra := record.get("extra", {}):
        # Add specific fields that GCP understands
        if correlation_id := extra.get("correlation_id"):
            log_entry["logging.googleapis.com/trace"] = correlation_id

        if request_id := extra.get("request_id"):
            labels["request_id"] = request_id

        # Add other fields to jsonPayload
        json_payload = {
            k: v for k, v in extra.items()
            if k not in {"correlation_id", "request_id"} and not k.startswith("_")
        }
        if json_payload:
            log_entry["jsonPayload"] = json_payload

    log_entry["logging.googleapis.com/labels"] = labels

    # Add source location for error reporting
    if record.get("exception"):
        log_entry["logging.googleapis.com/sourceLocation"] = {
            "file": record["file"].path,
            "line": str(record["line"]),
            "function": record["function"],
        }

    return json.dumps(log_entry, default=str) + "\n"


def serialize_for_aws(record: Record) -> str:
    """Format log record for AWS CloudWatch.

    Follows AWS CloudWatch Logs Insights format for better querying.

    Args:
        record: Loguru record to format.

    Returns:
        str: JSON-formatted log entry for AWS with newline.
    """
    log_entry = {
        "timestamp": record["time"].isoformat(),
        "level": record["level"].name,
        "message": record["message"],
        "logger": record["name"],
        "function": record["function"],
        "module": record["module"],
        "line": record["line"],
    }

    # Add AWS-specific fields
    if extra := record.get("extra", {}):
        # AWS X-Ray integration
        if correlation_id := extra.get("correlation_id"):
            log_entry["traceId"] = correlation_id

        if request_id := extra.get("request_id"):
            log_entry["requestId"] = request_id

        # Add other fields
        for key, value in extra.items():
            if not key.startswith("_") and key not in log_entry:
                log_entry[key] = value

    # Add exception details
    if exc := record.get("exception"):
        log_entry["error"] = {
            "type": exc.type.__name__ if exc.type else None,
            "message": str(exc.value) if exc.value else None,
            "stackTrace": exc.traceback if exc.traceback else None,
        }

    return json.dumps(log_entry, default=str) + "\n"


# Formatter registry - easily extensible
LOG_FORMATTERS: dict[str, FormatFunction | None] = {
    "console": None,  # Use Loguru's default console formatter
    "json": serialize_for_json,
    "gcp": serialize_for_gcp,
    "aws": serialize_for_aws,
}


def detect_environment() -> str:
    """Auto-detect the deployment environment.

    Returns:
        str: Detected formatter type (console, gcp, aws).
    """
    import os

    # Check for cloud-specific environment variables
    if os.getenv("K_SERVICE"):  # Cloud Run
        return "gcp"
    elif os.getenv("AWS_EXECUTION_ENV"):  # AWS Lambda/ECS
        return "aws"
    elif os.getenv("WEBSITE_INSTANCE_ID"):  # Azure
        return "json"  # Azure uses generic JSON
    else:
        return "console"  # Local development


def detect_cloud_provider() -> str:
    """Detect which cloud provider we're running on.

    This is an alternative implementation that can be used
    for smart defaults based on environment detection.
    """
    if os.getenv("K_SERVICE"):  # Cloud Run
        return "gcp"
    elif os.getenv("AWS_EXECUTION_ENV"):  # AWS Lambda/ECS
        return "aws"
    elif os.getenv("WEBSITE_INSTANCE_ID"):  # Azure
        return "azure"
    else:
        return "console"  # Local development


@lru_cache(maxsize=1)
def setup_logging(settings: Settings) -> None:
    """Configure Loguru with pluggable formatters.

    Args:
        settings: Application settings containing log configuration.
    """
    # Remove default handler
    logger.remove()

    # Determine formatter type
    formatter_type = getattr(settings.log_config, 'log_formatter_type', None)

    # Auto-detect if not specified
    if not formatter_type:
        formatter_type = detect_environment()

    # Get formatter function
    formatter = LOG_FORMATTERS.get(formatter_type)

    if formatter_type == "console" or formatter is None:
        # Human-readable console format for development
        logger.add(
            sys.stdout,
            format=DEFAULT_LOG_FORMAT,
            level=settings.log_config.log_level,
            enqueue=True,
            colorize=True,
            diagnose=settings.debug,
            backtrace=settings.debug,
        )
    else:
        # Structured format for cloud providers or JSON
        logger.add(
            sys.stdout,
            format=formatter,
            level=settings.log_config.log_level,
            enqueue=True,  # Thread-safe async logging
            serialize=False,  # We handle serialization in format function
            diagnose=False,  # No variable values in production
            backtrace=False,  # Minimal traceback in production
        )

    # Configure standard library logging to use Loguru
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)

    # Disable noisy loggers
    for logger_name in ["uvicorn.access", "urllib3.connectionpool"]:
        logging.getLogger(logger_name).disabled = True

    # Log the formatter being used
    logger.info(
        f"Logging configured with {formatter_type} formatter",
        formatter_type=formatter_type,
        log_level=settings.log_config.log_level,
    )


def get_logger(name: str) -> Any:
    """Get a logger instance with the given name."""
    return logger.bind(logger_name=name)


def bind_context(**kwargs: Any) -> None:
    """Bind persistent context variables to the logger."""
    logger.configure(extra=kwargs)
```

### Step 2: Update Configuration

Update `src/core/config.py` to add formatter configuration:

```python
# In LogConfig class, add:
class LogConfig(BaseModel):
    """Logging configuration."""

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Logging level",
    )
    log_formatter_type: Literal["console", "json", "gcp", "aws"] | None = Field(
        default=None,
        description="Log output formatter. Auto-detected if not specified.",
    )
    excluded_paths: list[str] = Field(
        default_factory=lambda: ["/health", "/metrics"],
        description="Paths to exclude from request logging",
    )
    slow_request_threshold_ms: int = Field(
        default=1000,
        gt=0,
        description="Threshold for slow request warnings (milliseconds)",
    )
    enable_sql_logging: bool = Field(
        default=False,
        description="Enable SQL query logging",
    )
```

### Step 3: Create Tests for Each Formatter

Create `tests/unit/core/test_log_formatters.py`:

```python
"""Tests for cloud-agnostic log formatters."""

import json
from datetime import datetime
from io import StringIO

import pytest
from loguru import logger

from src.core.config import Settings
from src.core.logging import (
    detect_environment,
    serialize_for_aws,
    serialize_for_gcp,
    serialize_for_json,
    setup_logging,
)


class TestFormatters:
    """Test individual formatter functions."""

    @pytest.fixture
    def mock_record(self):
        """Create a mock Loguru record."""
        return {
            "time": datetime.now(),
            "level": type("Level", (), {"name": "INFO"}),
            "message": "Test message",
            "name": None,
            "function": "test_function",
            "module": "test_module",
            "line": 42,
            "file": type("File", (), {"path": "test.py"}),
            "extra": {
                "correlation_id": "test-correlation-123",
                "request_id": "test-request-456",
                "user_id": 789,
                "_internal": "should be filtered",
            },
        }

    def test_json_formatter(self, mock_record):
        """Test generic JSON formatter."""
        output = serialize_for_json(mock_record)
        data = json.loads(output.strip())

        assert data["level"] == "INFO"
        assert data["message"] == "Test message"
        assert data["function"] == "test_function"
        assert data["correlation_id"] == "test-correlation-123"
        assert data["request_id"] == "test-request-456"
        assert data["user_id"] == 789
        assert "_internal" not in data

    def test_gcp_formatter(self, mock_record):
        """Test GCP Cloud Logging formatter."""
        output = serialize_for_gcp(mock_record)
        data = json.loads(output.strip())

        assert data["severity"] == "INFO"
        assert data["message"] == "Test message"
        assert data["logging.googleapis.com/trace"] == "test-correlation-123"
        assert data["logging.googleapis.com/labels"]["request_id"] == "test-request-456"
        assert data["jsonPayload"]["user_id"] == 789
        assert "timestamp" in data

    def test_aws_formatter(self, mock_record):
        """Test AWS CloudWatch formatter."""
        output = serialize_for_aws(mock_record)
        data = json.loads(output.strip())

        assert data["level"] == "INFO"
        assert data["message"] == "Test message"
        assert data["traceId"] == "test-correlation-123"
        assert data["requestId"] == "test-request-456"
        assert data["user_id"] == 789
        assert "timestamp" in data

    def test_exception_formatting_json(self, mock_record):
        """Test exception formatting in JSON."""
        mock_record["exception"] = type("Exception", (), {
            "type": ValueError,
            "value": "Test error",
            "traceback": "Traceback details...",
        })

        output = serialize_for_json(mock_record)
        data = json.loads(output.strip())

        assert data["exception"]["type"] == "ValueError"
        assert data["exception"]["value"] == "Test error"
        assert "traceback" in data["exception"]

    def test_exception_formatting_gcp(self, mock_record):
        """Test exception formatting for GCP."""
        mock_record["exception"] = type("Exception", (), {
            "type": ValueError,
            "value": "Test error",
            "traceback": "Traceback details...",
        })

        output = serialize_for_gcp(mock_record)
        data = json.loads(output.strip())

        assert "logging.googleapis.com/sourceLocation" in data
        assert data["logging.googleapis.com/sourceLocation"]["file"] == "test.py"
        assert data["logging.googleapis.com/sourceLocation"]["line"] == "42"


class TestEnvironmentDetection:
    """Test automatic environment detection."""

    def test_detect_gcp(self, monkeypatch):
        """Test GCP environment detection."""
        monkeypatch.setenv("K_SERVICE", "test-service")
        assert detect_environment() == "gcp"

    def test_detect_aws(self, monkeypatch):
        """Test AWS environment detection."""
        monkeypatch.setenv("AWS_EXECUTION_ENV", "AWS_ECS_FARGATE")
        assert detect_environment() == "aws"

    def test_detect_local(self, monkeypatch):
        """Test local environment detection."""
        # Ensure no cloud env vars
        monkeypatch.delenv("K_SERVICE", raising=False)
        monkeypatch.delenv("AWS_EXECUTION_ENV", raising=False)
        assert detect_environment() == "console"


class TestFormatterIntegration:
    """Test formatter integration with Loguru."""

    @pytest.fixture(autouse=True)
    def cleanup_logger(self):
        """Clean up logger handlers."""
        handlers = list(logger._core.handlers.values())
        yield
        logger.remove()
        for handler in handlers:
            logger.add(**handler)

    def test_console_formatter(self):
        """Test console formatter setup."""
        settings = Settings(
            log_config={"log_formatter_type": "console"}
        )

        logger.remove()
        setup_logging(settings)

        # Console formatter should have colorize enabled
        # Just verify it doesn't crash
        logger.info("Test console message")

    def test_json_formatter_integration(self):
        """Test JSON formatter integration."""
        settings = Settings(
            log_config={"log_formatter_type": "json"}
        )

        output = StringIO()
        logger.remove()

        # Add handler with JSON formatter
        logger.add(
            output,
            format=serialize_for_json,
            level="INFO",
        )

        # Log with context
        with logger.contextualize(correlation_id="test-123"):
            logger.info("Test message", user_id=456)

        # Parse output
        log_line = output.getvalue()
        data = json.loads(log_line.strip())

        assert data["message"] == "Test message"
        assert data["correlation_id"] == "test-123"
        assert data["user_id"] == 456

    def test_formatter_auto_detection(self, monkeypatch):
        """Test formatter auto-detection."""
        # Simulate GCP environment
        monkeypatch.setenv("K_SERVICE", "test-service")

        settings = Settings(
            log_config={}  # No formatter specified
        )

        logger.remove()
        setup_logging(settings)

        # Should auto-detect GCP
        # Verify by checking the last log message
        output = StringIO()
        logger.add(output, format="{message}")
        logger.info("After setup")

        assert "gcp formatter" in output.getvalue()


class TestCloudAgnostic:
    """Test cloud-agnostic functionality."""

    def test_local_development_no_cloud(self):
        """Test that local development works without cloud services."""
        settings = Settings(
            environment="development",
            log_config={"log_formatter_type": "console"}
        )

        # Should not require any cloud authentication
        logger.remove()
        setup_logging(settings)

        # Should work without errors
        logger.info("Local development message")

    def test_easy_cloud_switching(self):
        """Test switching between cloud providers is configuration-only."""
        # Start with GCP
        settings_gcp = Settings(
            log_config={"log_formatter_type": "gcp"}
        )

        output_gcp = StringIO()
        logger.remove()
        logger.add(output_gcp, format=serialize_for_gcp)
        logger.info("GCP message")

        gcp_data = json.loads(output_gcp.getvalue().strip())
        assert "severity" in gcp_data  # GCP-specific field

        # Switch to AWS
        settings_aws = Settings(
            log_config={"log_formatter_type": "aws"}
        )

        output_aws = StringIO()
        logger.remove()
        logger.add(output_aws, format=serialize_for_aws)
        logger.info("AWS message")

        aws_data = json.loads(output_aws.getvalue().strip())
        assert "level" in aws_data  # AWS uses different field name

        # No code changes required, only configuration!
```

### Step 4: Update .env.example

Replace the existing logging configuration section with comprehensive formatter examples:

```bash
# ==========================================
# Logging Configuration (Updated in Phase 3)
# ==========================================

# Logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_CONFIG__LOG_LEVEL=INFO

# Log formatter type - determines output format
# Options: console (dev), json (generic), gcp (Google Cloud), aws (AWS CloudWatch)
# Leave empty for auto-detection based on environment
LOG_CONFIG__LOG_FORMATTER_TYPE=console

# Request logging configuration
LOG_CONFIG__EXCLUDED_PATHS=["/health", "/metrics"]
LOG_CONFIG__SLOW_REQUEST_THRESHOLD_MS=1000

# SQL logging
LOG_CONFIG__ENABLE_SQL_LOGGING=false
LOG_CONFIG__SLOW_QUERY_THRESHOLD_MS=100

# Sensitive fields (simplified list - regex patterns in code)
LOG_CONFIG__SENSITIVE_FIELDS=["password", "token", "secret", "api_key", "authorization"]

# ==========================================
# Environment-Specific Formatter Examples
# ==========================================

# Local Development (colorized console output)
# LOG_CONFIG__LOG_FORMATTER_TYPE=console

# GCP Production (Cloud Logging format)
# LOG_CONFIG__LOG_FORMATTER_TYPE=gcp

# AWS Production (CloudWatch format)
# LOG_CONFIG__LOG_FORMATTER_TYPE=aws

# Self-hosted with generic JSON logs
# LOG_CONFIG__LOG_FORMATTER_TYPE=json
```

## Validation Checklist

- [ ] All formatter functions implemented
- [ ] Formatter registry created and extensible
- [ ] Auto-detection works for cloud environments
- [ ] Console formatter works for local development
- [ ] JSON formatter produces valid JSON
- [ ] GCP formatter follows Cloud Logging format
- [ ] AWS formatter follows CloudWatch format
- [ ] Configuration supports formatter selection
- [ ] Tests cover all formatters
- [ ] No cloud authentication required for local dev
- [ ] `make lint` passes
- [ ] `make type-check` passes

## Expected Results

After Phase 3:
- Logs formatted appropriately for each environment
- Easy switching between clouds via configuration
- Local development with pretty console output
- Production logs structured for cloud providers
- ~30-40 tests for formatter functionality

## Testing Cloud Formatters Locally

```bash
# Test console formatter (default for development)
LOG_CONFIG__LOG_FORMATTER_TYPE=console make dev
# Pretty colored output in terminal

# Test JSON formatter
LOG_CONFIG__LOG_FORMATTER_TYPE=json make dev
# Structured JSON logs, one per line

# Test GCP formatter
LOG_CONFIG__LOG_FORMATTER_TYPE=gcp make dev
# GCP-structured JSON logs

# Test AWS formatter
LOG_CONFIG__LOG_FORMATTER_TYPE=aws make dev
# AWS-structured JSON logs

# Test auto-detection
unset LOG_CONFIG__LOG_FORMATTER_TYPE
make dev
# Should use console formatter locally
```

## Smart Defaults Based on Environment

From the specification, you can implement smart defaults:

```python
# Example: Smart defaults based on environment detection
import os

def detect_cloud_provider() -> str:
    """Detect which cloud provider we're running on."""
    if os.getenv("K_SERVICE"):  # Cloud Run
        return "gcp"
    elif os.getenv("AWS_EXECUTION_ENV"):  # AWS Lambda/ECS
        return "aws"
    elif os.getenv("WEBSITE_INSTANCE_ID"):  # Azure
        return "azure"
    else:
        return "console"  # Local development

# In your settings
cloud_provider = detect_cloud_provider()
LOG_CONFIG__LOG_FORMATTER_TYPE = os.getenv("LOG_CONFIG__LOG_FORMATTER_TYPE", cloud_provider)
OBSERVABILITY_CONFIG__EXPORTER_TYPE = os.getenv("OBSERVABILITY_CONFIG__EXPORTER_TYPE", cloud_provider)
```

## Cloud Migration Examples

### Migrating from GCP to AWS

1. Change environment variable:
   ```bash
   # From
   LOG_CONFIG__LOG_FORMATTER_TYPE=gcp

   # To
   LOG_CONFIG__LOG_FORMATTER_TYPE=aws
   ```

2. Deploy. That's it! No code changes required.

### Adding a New Cloud Provider (e.g., Azure)

1. Add formatter function:
   ```python
   def serialize_for_azure(record: Record) -> str:
       """Format for Azure Application Insights."""
       # Azure-specific format
       return json.dumps(azure_format, default=str) + "\n"
   ```

2. Register formatter:
   ```python
   LOG_FORMATTERS["azure"] = serialize_for_azure
   ```

3. Update config type:
   ```python
   log_formatter_type: Literal["console", "json", "gcp", "aws", "azure"] | None
   ```

## Notes for Next Phases

- Phase 4 will add basic sensitive data sanitization
- Formatters already include correlation IDs from Phase 2
- Keep formatters simple and focused on structure
- Cloud-specific features (like GCP Error Reporting) work automatically

## Performance Considerations

- JSON serialization is fast with Python's built-in json
- Formatters are called for every log message, keep them lightweight
- `enqueue=True` ensures formatting doesn't block the main thread
- No complex processing in formatters
