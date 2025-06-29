# Phase 6: Configuration and Integration

## Overview
This final phase integrates all components from previous phases, finalizes configuration, performs cleanup, and ensures everything works together seamlessly. We'll also create integration tests and update documentation.

## Prerequisites
- All previous phases completed
- Basic functionality working independently

## Objectives
1. Finalize configuration classes
2. Ensure all components integrate properly
3. Create comprehensive integration tests
4. Update documentation
5. Clean up any remaining TODOs
6. Verify cloud-agnostic operation

## Implementation

### Step 1: Finalize Configuration

Update `src/core/config.py` with final configuration:

```python
"""Configuration management module for Tributum application."""

import os
from functools import lru_cache
from typing import Literal

from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class LogConfig(BaseModel):
    """Simplified logging configuration."""

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


class ObservabilityConfig(BaseModel):
    """Cloud-agnostic observability configuration."""

    enable_tracing: bool = Field(
        default=True,
        description="Enable OpenTelemetry tracing",
    )
    exporter_type: Literal["console", "gcp", "aws", "otlp", "none"] = Field(
        default="console",
        description="Trace exporter type. Defaults to console for development.",
    )
    exporter_endpoint: str | None = Field(
        default=None,
        description="OTLP exporter endpoint (for OTLP/AWS exporters)",
    )
    gcp_project_id: str | None = Field(
        default=None,
        description="GCP project ID (only for GCP exporter)",
    )
    trace_sample_rate: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Trace sampling rate (0.0 to 1.0)",
    )


class DatabaseConfig(BaseModel):
    """Database configuration settings."""

    database_url: str = Field(
        default="postgresql+asyncpg://tributum:tributum_pass@localhost:5432/tributum_db",
        description="Database connection URL (postgresql+asyncpg://...)",
    )
    pool_size: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Number of connections to maintain in the pool",
    )
    max_overflow: int = Field(
        default=5,
        ge=0,
        le=50,
        description="Maximum overflow connections above pool_size",
    )
    pool_timeout: float = Field(
        default=30.0,
        gt=0,
        le=300,
        description="Timeout in seconds for acquiring a connection from the pool",
    )
    pool_pre_ping: bool = Field(
        default=True,
        description="Whether to test connections before using them",
    )
    echo: bool = Field(
        default=False,
        description="Whether to log SQL statements (use only for debugging)",
    )

    @field_validator("database_url", mode="after")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """Validate database URL uses the correct driver for async PostgreSQL."""
        if not v.startswith("postgresql+asyncpg://"):
            msg = "Database URL must use postgresql+asyncpg:// driver for async support"
            raise ValueError(msg)
        return v

    def get_test_database_url(self) -> str:
        """Get database URL for testing purposes."""
        if "/tributum_db" in self.database_url:
            return self.database_url.replace("/tributum_db", "/tributum_test")
        if "/tributum" in self.database_url:
            return self.database_url.replace("/tributum", "/tributum_test")

        parts = self.database_url.rsplit("/", 1)
        expected_parts = 2
        if len(parts) == expected_parts:
            base_url, db_name = parts
            db_name = db_name.split("?")[0]
            query_params = ""
            if "?" in parts[1]:
                query_params = "?" + parts[1].split("?", 1)[1]
            return f"{base_url}/{db_name}_test{query_params}"
        return self.database_url


class Settings(BaseSettings):
    """Main settings class for the application."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        validate_default=True,
        env_nested_delimiter="__",
    )

    # Application settings
    app_name: str = Field(default="Tributum", description="Application name")
    app_version: str = Field(default="0.3.0", description="Application version")
    environment: Literal["development", "staging", "production"] = Field(
        default="development",
        description="Environment the application is running in",
    )
    debug: bool = Field(default=True, description="Debug mode flag")

    # API settings
    api_host: str = Field(default="127.0.0.1", description="API host")
    api_port: int = Field(default=8000, description="API port")
    docs_url: str | None = Field(default="/docs", description="Swagger UI URL")
    redoc_url: str | None = Field(default="/redoc", description="ReDoc URL")
    openapi_url: str | None = Field(
        default="/openapi.json", description="OpenAPI schema URL"
    )

    # Logging configuration
    log_config: LogConfig = Field(
        default_factory=LogConfig, description="Logging configuration"
    )

    # Observability configuration
    observability_config: ObservabilityConfig = Field(
        default_factory=ObservabilityConfig, description="Observability configuration"
    )

    # Database configuration
    database_config: DatabaseConfig = Field(
        default_factory=DatabaseConfig, description="Database configuration"
    )

    def model_post_init(self, __context: object) -> None:
        """Post initialization to set environment-based defaults."""
        super().model_post_init(__context)

        # Auto-detect formatters and exporters if not specified
        if self.log_config.log_formatter_type is None:
            self.log_config.log_formatter_type = self._detect_formatter()

        if self.environment == "production":
            # Production defaults
            if self.observability_config.exporter_type == "console":
                self.observability_config.exporter_type = self._detect_exporter()
            if self.observability_config.trace_sample_rate == 1.0:
                self.observability_config.trace_sample_rate = 0.1

    def _detect_formatter(self) -> Literal["console", "json", "gcp", "aws"]:
        """Auto-detect log formatter based on environment."""
        if self.environment == "development":
            return "console"

        # Check for cloud environments
        if os.getenv("K_SERVICE"):  # Cloud Run
            return "gcp"
        elif os.getenv("AWS_EXECUTION_ENV"):  # AWS
            return "aws"
        else:
            return "json"  # Generic JSON for production

    def _detect_exporter(self) -> Literal["console", "gcp", "aws", "otlp", "none"]:
        """Auto-detect trace exporter based on environment."""
        if self.environment == "development":
            return "console"

        # Check for cloud environments
        if os.getenv("K_SERVICE"):  # Cloud Run
            return "gcp"
        elif os.getenv("AWS_EXECUTION_ENV"):  # AWS
            return "aws"
        else:
            return "otlp"  # Generic OTLP

    @field_validator("docs_url", "redoc_url", "openapi_url", mode="before")
    @classmethod
    def empty_str_to_none(cls, v: str | None) -> str | None:
        """Convert empty strings to None for nullable fields."""
        _ = cls  # Mark as used
        if v == "":
            return None
        return v


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Configuration helper for environment-based defaults
def get_config_defaults(environment: str) -> dict[str, Any]:
    """Get default configuration based on environment.

    Args:
        environment: The deployment environment.

    Returns:
        dict: Default configuration values.
    """
    if environment == "production":
        return {
            "log_config": {
                "log_formatter_type": "gcp",  # Or "aws" based on cloud provider
            },
            "observability_config": {
                "exporter_type": "gcp",  # Or "aws" based on cloud provider
            },
        }
    else:
        # Development defaults
        return {
            "log_config": {
                "log_formatter_type": "console",
            },
            "observability_config": {
                "exporter_type": "console",
                "trace_to_file": True,
            },
        }
```

### Step 2: Type Safety Considerations

From the specification, here's how to handle Loguru's dynamic nature with type checkers:

#### Why `get_logger()` Returns `Any`

In the implementation, `get_logger()` returns `Any` to prevent circular imports:

```python
def get_logger(name: str) -> Any:  # Returns loguru.Logger but can't import at module level
    """Get a logger instance with the given name.

    The return type is Any to avoid circular imports when loguru
    needs to import from src.core.config during initialization.
    """
    return logger.bind(logger_name=name)
```

#### Handling MyPy/Pyright Warnings

If type checkers complain about untyped logger usage:

```python
# Option 1: Type assertion
from typing import TYPE_CHECKING, cast
if TYPE_CHECKING:
    from loguru import Logger

logger = cast("Logger", logger)  # Type assertion for type checkers

# Option 2: Type ignore comment (simpler)
logger.info("Message")  # type: ignore[attr-defined]

# Option 3: Create a typed protocol (most robust)
from typing import Protocol

class LoggerProtocol(Protocol):
    """Protocol matching Loguru's logger interface."""
    def info(self, message: str, **kwargs: Any) -> None: ...
    def error(self, message: str, **kwargs: Any) -> None: ...
    def bind(self, **kwargs: Any) -> "LoggerProtocol": ...
    # Add other methods as needed

# Use the protocol for type hints
def process_request(logger: LoggerProtocol) -> None:
    logger.info("Processing request")
```

### Step 3: Create Final .env.example

Create the final, clean .env.example that shows only the simplified configuration:

```bash
# ==========================================
# Tributum Backend Environment Configuration
# ==========================================
# Simplified observability configuration after migration

# Application Settings
# --------------------
APP_NAME=Tributum
APP_VERSION=0.3.0
ENVIRONMENT=development  # Options: development, staging, production
DEBUG=true              # Set to false in production

# API Settings
# ------------
API_HOST=127.0.0.1      # Use 0.0.0.0 for Docker/external access
API_PORT=8000           # Default FastAPI port
DOCS_URL=/docs          # Swagger UI endpoint (set to empty to disable)
REDOC_URL=/redoc        # ReDoc endpoint (set to empty to disable)
OPENAPI_URL=/openapi.json  # OpenAPI schema endpoint

# Logging Configuration (Simplified)
# ----------------------------------
LOG_CONFIG__LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_CONFIG__LOG_FORMATTER_TYPE=console  # console, json, gcp, aws (auto-detected if empty)
LOG_CONFIG__EXCLUDED_PATHS=["/health", "/metrics"]
LOG_CONFIG__SLOW_REQUEST_THRESHOLD_MS=1000
LOG_CONFIG__ENABLE_SQL_LOGGING=false
LOG_CONFIG__SLOW_QUERY_THRESHOLD_MS=100

# Observability Configuration (Simplified)
# ----------------------------------------
OBSERVABILITY_CONFIG__ENABLE_TRACING=true
OBSERVABILITY_CONFIG__EXPORTER_TYPE=console  # console, gcp, aws, otlp, none (auto-detected if empty)
OBSERVABILITY_CONFIG__EXPORTER_ENDPOINT=  # For OTLP/AWS exporters
OBSERVABILITY_CONFIG__GCP_PROJECT_ID=  # For GCP exporter only
OBSERVABILITY_CONFIG__TRACE_SAMPLE_RATE=1.0  # 0.0 to 1.0

# Database Configuration
# ---------------------
DATABASE_CONFIG__DATABASE_URL=postgresql+asyncpg://tributum:tributum_pass@localhost:5432/tributum_db
DATABASE_CONFIG__POOL_SIZE=10
DATABASE_CONFIG__MAX_OVERFLOW=5
DATABASE_CONFIG__POOL_TIMEOUT=30.0
DATABASE_CONFIG__POOL_PRE_PING=true
DATABASE_CONFIG__ECHO=false

# ==========================================
# Environment-Specific Examples
# ==========================================

# Development (current settings above)
# ------------------------------------
# - Console logging with colors
# - Console trace output
# - Full sampling (100%)
# - Debug enabled

# Production GCP
# --------------
# ENVIRONMENT=production
# DEBUG=false
# LOG_CONFIG__LOG_LEVEL=WARNING
# LOG_CONFIG__LOG_FORMATTER_TYPE=gcp
# OBSERVABILITY_CONFIG__EXPORTER_TYPE=gcp
# OBSERVABILITY_CONFIG__GCP_PROJECT_ID=your-project-id
# OBSERVABILITY_CONFIG__TRACE_SAMPLE_RATE=0.1

# Production AWS
# --------------
# ENVIRONMENT=production
# DEBUG=false
# LOG_CONFIG__LOG_LEVEL=WARNING
# LOG_CONFIG__LOG_FORMATTER_TYPE=aws
# OBSERVABILITY_CONFIG__EXPORTER_TYPE=aws
# OBSERVABILITY_CONFIG__EXPORTER_ENDPOINT=https://xray.region.amazonaws.com
# OBSERVABILITY_CONFIG__TRACE_SAMPLE_RATE=0.1

# Production Self-Hosted
# ----------------------
# ENVIRONMENT=production
# DEBUG=false
# LOG_CONFIG__LOG_LEVEL=WARNING
# LOG_CONFIG__LOG_FORMATTER_TYPE=json
# OBSERVABILITY_CONFIG__EXPORTER_TYPE=otlp
# OBSERVABILITY_CONFIG__EXPORTER_ENDPOINT=http://jaeger:4317
# OBSERVABILITY_CONFIG__TRACE_SAMPLE_RATE=0.5

# ==========================================
# Migration Notes
# ==========================================
# This configuration has been simplified from 40+ settings to 11 essential ones.
# Features removed:
# - Complex sanitization strategies (only redact now)
# - Performance processors (use cloud monitoring)
# - Memory tracking (use cloud monitoring)
# - Request/response body logging
# - Multiple log processors
#
# For advanced features, use your cloud provider's native tools.
```

### Step 4: Create Integration Tests

Create `tests/integration/test_observability_integration.py`:

```python
"""Integration tests for the complete observability stack."""

import asyncio
import json
from io import StringIO

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from loguru import logger

from src.api.main import create_app
from src.core.config import Settings
from src.core.context import RequestContext


@pytest.fixture
def test_settings():
    """Test settings with all features enabled."""
    return Settings(
        environment="development",
        log_config={
            "log_level": "DEBUG",
            "log_formatter_type": "json",  # Use JSON for structured assertions
            "slow_request_threshold_ms": 50,
        },
        observability_config={
            "enable_tracing": True,
            "exporter_type": "console",  # No cloud dependencies
            "trace_sample_rate": 1.0,
        },
    )


@pytest.fixture
def test_app(test_settings):
    """Create test application with full observability."""
    return create_app(test_settings)


@pytest.fixture
def capture_json_logs():
    """Capture JSON-formatted logs."""
    output = StringIO()
    handler_id = logger.add(
        output,
        format=lambda record: json.dumps({
            "level": record["level"].name,
            "message": record["message"],
            "extra": record.get("extra", {}),
        }) + "\n",
        level="DEBUG",
    )

    yield output

    logger.remove(handler_id)


class TestFullStackIntegration:
    """Test full observability stack integration."""

    def test_request_flow_with_correlation_id(self, test_app, capture_json_logs):
        """Test complete request flow with correlation ID propagation."""
        client = TestClient(test_app)

        # Make request with correlation ID
        headers = {"X-Correlation-ID": "integration-test-123"}
        response = client.get("/", headers=headers)

        assert response.status_code == 200
        assert response.headers["X-Correlation-ID"] == "integration-test-123"
        assert "X-Request-ID" in response.headers

        # Parse logs
        logs = [
            json.loads(line)
            for line in capture_json_logs.getvalue().strip().split("\n")
            if line
        ]

        # Verify correlation ID in all relevant logs
        request_logs = [
            log for log in logs
            if log["message"] in ["Request started", "Request completed"]
        ]

        assert len(request_logs) >= 2
        for log in request_logs:
            assert log["extra"]["correlation_id"] == "integration-test-123"

    def test_slow_request_detection(self, test_app, capture_json_logs):
        """Test slow request detection and logging."""
        # Add slow endpoint
        @test_app.get("/slow-test")
        async def slow_endpoint():
            await asyncio.sleep(0.1)  # 100ms
            return {"status": "slow"}

        client = TestClient(test_app)
        response = client.get("/slow-test")

        assert response.status_code == 200

        # Check for slow request warning
        logs = [
            json.loads(line)
            for line in capture_json_logs.getvalue().strip().split("\n")
            if line
        ]

        slow_warnings = [
            log for log in logs
            if log["message"] == "Slow request detected"
        ]

        assert len(slow_warnings) == 1
        assert slow_warnings[0]["level"] == "WARNING"
        assert slow_warnings[0]["extra"]["duration_ms"] > 50

    def test_error_handling_with_sanitization(self, test_app, capture_json_logs):
        """Test error handling with sensitive data sanitization."""
        @test_app.post("/test-error")
        async def error_endpoint(data: dict):
            # Simulate error with sensitive data
            raise ValueError("Database error")

        client = TestClient(test_app)
        response = client.post(
            "/test-error",
            json={
                "username": "testuser",
                "password": "secret123",
                "api_key": "sk-12345",
            }
        )

        assert response.status_code == 500

        # Check logs don't contain sensitive data
        log_output = capture_json_logs.getvalue()
        assert "secret123" not in log_output
        assert "sk-12345" not in log_output
        assert "[REDACTED]" in log_output or "password" not in log_output

    @pytest.mark.asyncio
    async def test_context_propagation_async(self):
        """Test context propagation through async operations."""
        correlation_id = "async-test-456"

        async def nested_operation():
            # Context should be available
            assert RequestContext.get_correlation_id() == correlation_id
            logger.info("Nested operation")

        async def main_operation():
            RequestContext.set_correlation_id(correlation_id)

            with logger.contextualize(correlation_id=correlation_id):
                logger.info("Main operation")
                await nested_operation()

                # Concurrent operations
                await asyncio.gather(
                    nested_operation(),
                    nested_operation(),
                )

        await main_operation()


class TestCloudAgnosticOperation:
    """Test cloud-agnostic functionality."""

    def test_local_development_setup(self, test_settings):
        """Test complete setup works without cloud services."""
        # Should not require any authentication
        app = create_app(test_settings)
        client = TestClient(app)

        # Basic functionality should work
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] in ["healthy", "degraded"]

    def test_formatter_switching(self, capture_json_logs):
        """Test easy switching between formatters."""
        # Console formatter
        settings_console = Settings(
            log_config={"log_formatter_type": "console"}
        )
        app_console = create_app(settings_console)

        # JSON formatter
        settings_json = Settings(
            log_config={"log_formatter_type": "json"}
        )
        app_json = create_app(settings_json)

        # Both should work without code changes
        assert app_console is not None
        assert app_json is not None

    def test_exporter_switching(self):
        """Test easy switching between trace exporters."""
        # Console exporter
        settings_console = Settings(
            observability_config={"exporter_type": "console"}
        )
        app_console = create_app(settings_console)

        # OTLP exporter
        settings_otlp = Settings(
            observability_config={
                "exporter_type": "otlp",
                "exporter_endpoint": "http://localhost:4317",
            }
        )
        app_otlp = create_app(settings_otlp)

        # Both should initialize without errors
        assert app_console is not None
        assert app_otlp is not None


class TestEnvironmentDetection:
    """Test automatic environment detection."""

    def test_development_defaults(self):
        """Test development environment defaults."""
        settings = Settings(environment="development")

        # Should default to console for development
        if settings.log_config.log_formatter_type is None:
            settings.model_post_init(None)

        assert settings.log_config.log_formatter_type == "console"
        assert settings.observability_config.exporter_type == "console"

    def test_production_defaults(self, monkeypatch):
        """Test production environment defaults."""
        # Simulate GCP environment
        monkeypatch.setenv("K_SERVICE", "test-service")

        settings = Settings(environment="production")

        # Should auto-detect GCP
        assert settings.log_config.log_formatter_type == "gcp"
        assert settings.observability_config.trace_sample_rate == 0.1
```

### Step 5: Validate Configuration Migration

Create `scripts/validate_configuration.py`:
```python
#!/usr/bin/env python3
"""Validate configuration migration is complete."""

from pathlib import Path
import sys

def validate_env_example():
    """Validate .env.example has been properly updated."""
    env_file = Path(".env.example")
    if not env_file.exists():
        return ["Missing .env.example file"]

    content = env_file.read_text()
    issues = []

    # Check for removed settings
    removed_settings = [
        "LOG_CONFIG__RENDER_JSON_LOGS",
        "LOG_CONFIG__ENABLE_PERFORMANCE_METRICS",
        "LOG_CONFIG__FIELD_SANITIZATION_STRATEGIES",
        "OBSERVABILITY_CONFIG__ENABLE_METRICS",
        "OBSERVABILITY_CONFIG__SERVICE_NAME",
    ]

    for setting in removed_settings:
        if setting in content:
            issues.append(f"Obsolete setting found: {setting}")

    # Check for new settings
    required_settings = [
        "LOG_CONFIG__LOG_FORMATTER_TYPE",
        "OBSERVABILITY_CONFIG__EXPORTER_TYPE",
    ]

    for setting in required_settings:
        if setting not in content:
            issues.append(f"Missing new setting: {setting}")

    return issues

def validate_constants():
    """Validate constants files have been updated."""
    issues = []

    # Check core constants
    core_constants = Path("src/core/constants.py")
    if core_constants.exists():
        content = core_constants.read_text()

        # Should not have these anymore
        if "SENSITIVE_FIELD_PATTERNS" in content and len(content.split("SENSITIVE_FIELD_PATTERNS")[1].split("]")[0]) > 100:
            issues.append("SENSITIVE_FIELD_PATTERNS should be removed from core constants")

        if "FINGERPRINT_MAX_PARTS" in content:
            issues.append("Old logging constants still present in core/constants.py")

    return issues

def main():
    """Run configuration validation."""
    print("Configuration Migration Validation")
    print("=" * 50)

    all_issues = []

    # Run validations
    all_issues.extend(validate_env_example())
    all_issues.extend(validate_constants())

    if all_issues:
        print("\n❌ Configuration issues found:")
        for issue in all_issues:
            print(f"  - {issue}")
        sys.exit(1)
    else:
        print("\n✅ Configuration migration validated!")

if __name__ == "__main__":
    main()
```

### Step 6: Create Migration Helper Script

Create `scripts/verify_migration.py`:

```python
#!/usr/bin/env python3
"""Verify the observability migration is complete."""

import subprocess
import sys
from pathlib import Path


def check_old_imports():
    """Check for any remaining old imports."""
    print("Checking for old imports...")

    old_patterns = [
        "from src.core.logging import get_logger",
        "from src.core.error_context import",
        "from src.core.observability import",
        "import structlog",
    ]

    issues = []
    for pattern in old_patterns:
        result = subprocess.run(
            ["grep", "-r", pattern, "src/", "tests/"],
            capture_output=True,
            text=True,
        )
        if result.stdout:
            issues.append(f"Found old pattern '{pattern}':\n{result.stdout}")

    return issues


def check_removed_files():
    """Check that old files are removed."""
    print("Checking for removed files...")

    removed_files = [
        "src/core/logging_old.py",
        "src/core/error_context_old.py",
        "src/core/observability_old.py",
    ]

    issues = []
    for file_path in removed_files:
        if Path(file_path).exists():
            issues.append(f"Old file still exists: {file_path}")

    return issues


def check_dependencies():
    """Check dependencies are updated."""
    print("Checking dependencies...")

    pyproject = Path("pyproject.toml").read_text()

    issues = []
    if "structlog" in pyproject:
        issues.append("structlog still in dependencies")

    if "loguru" not in pyproject:
        issues.append("loguru not in dependencies")

    return issues


def run_quality_checks():
    """Run code quality checks."""
    print("Running quality checks...")

    checks = [
        ("Linting", ["make", "lint"]),
        ("Type checking", ["make", "type-check"]),
        ("Tests", ["make", "test"]),
    ]

    issues = []
    for name, command in checks:
        print(f"  Running {name}...")
        result = subprocess.run(command, capture_output=True)
        if result.returncode != 0:
            issues.append(f"{name} failed")

    return issues


def main():
    """Run all verification checks."""
    print("Tributum Observability Migration Verification")
    print("=" * 50)

    all_issues = []

    # Run checks
    all_issues.extend(check_old_imports())
    all_issues.extend(check_removed_files())
    all_issues.extend(check_dependencies())
    all_issues.extend(run_quality_checks())

    # Report results
    if all_issues:
        print("\n❌ Issues found:")
        for issue in all_issues:
            print(f"  - {issue}")
        sys.exit(1)
    else:
        print("\n✅ Migration verified successfully!")
        print("\nNext steps:")
        print("1. Test in development: make dev")
        print("2. Test different formatters:")
        print("   LOG_CONFIG__LOG_FORMATTER_TYPE=json make dev")
        print("3. Deploy to staging environment")
        print("4. Monitor logs and traces")


if __name__ == "__main__":
    main()
```

### Step 4: Update Documentation

Create `docs/OBSERVABILITY.md`:

```markdown
# Observability Guide

## Overview

Tributum uses a simplified, cloud-agnostic observability stack:
- **Loguru** for structured logging
- **OpenTelemetry** for distributed tracing
- **Pluggable backends** for easy cloud migration

## Configuration

### Local Development

```yaml
# .env.development (default)
LOG_CONFIG__LOG_FORMATTER_TYPE=console
OBSERVABILITY_CONFIG__EXPORTER_TYPE=console
```

Provides:
- Colored console logs
- Traces printed to console
- No cloud dependencies

### Production Environments

#### Google Cloud Platform
```yaml
# .env.production.gcp
LOG_CONFIG__LOG_FORMATTER_TYPE=gcp
OBSERVABILITY_CONFIG__EXPORTER_TYPE=gcp
OBSERVABILITY_CONFIG__GCP_PROJECT_ID=your-project-id
OBSERVABILITY_CONFIG__TRACE_SAMPLE_RATE=0.1
```

#### Amazon Web Services
```yaml
# .env.production.aws
LOG_CONFIG__LOG_FORMATTER_TYPE=aws
OBSERVABILITY_CONFIG__EXPORTER_TYPE=aws
OBSERVABILITY_CONFIG__EXPORTER_ENDPOINT=https://xray.region.amazonaws.com
OBSERVABILITY_CONFIG__TRACE_SAMPLE_RATE=0.1
```

#### Self-Hosted (Kubernetes)
```yaml
# .env.production.k8s
LOG_CONFIG__LOG_FORMATTER_TYPE=json
OBSERVABILITY_CONFIG__EXPORTER_TYPE=otlp
OBSERVABILITY_CONFIG__EXPORTER_ENDPOINT=http://jaeger:4317
OBSERVABILITY_CONFIG__TRACE_SAMPLE_RATE=0.5
```

## Usage

### Logging

```python
from loguru import logger

# Basic logging
logger.info("User logged in", user_id=123, ip_address="192.168.1.1")

# Error logging with context
try:
    process_payment()
except Exception as e:
    logger.exception("Payment failed", order_id=456)
```

### Tracing

```python
from src.core.observability import trace_operation, add_span_attributes

# Custom operation tracing
async def process_order(order_id: int):
    with trace_operation("order_processing", order_id=order_id):
        # Your code here
        result = await validate_order(order_id)

        # Add attributes to current span
        add_span_attributes(
            valid=result.is_valid,
            total_amount=result.amount,
        )
```

### Sensitive Data Protection

```python
from src.core.error_context import sanitize_dict

# Sanitize before logging
user_data = get_user_data()
logger.info("User updated", **sanitize_dict(user_data))
# Passwords, tokens, etc. are automatically redacted
```

## Migration Between Clouds

Switching cloud providers requires only configuration changes:

1. Update environment variables
2. Deploy
3. Done!

No code changes required.

## Monitoring

### Logs
- **Development**: Console output
- **GCP**: Cloud Logging console
- **AWS**: CloudWatch Logs
- **Self-hosted**: Your logging solution

### Traces
- **Development**: Console output
- **GCP**: Cloud Trace console
- **AWS**: X-Ray console
- **Self-hosted**: Jaeger/Zipkin UI

## Best Practices

1. **Always include context** in logs (IDs, user info, etc.)
2. **Use structured logging** - avoid string concatenation
3. **Create spans** for significant operations
4. **Set sampling rate** appropriately for production
5. **Sanitize sensitive data** before logging

## Troubleshooting

### No logs appearing
- Check `LOG_CONFIG__LOG_LEVEL` setting
- Verify formatter configuration
- Check if path is in `excluded_paths`

### No traces appearing
- Verify `OBSERVABILITY_CONFIG__ENABLE_TRACING=true`
- Check exporter configuration
- Verify sampling rate > 0
- Look for startup errors

### Performance impact
- Reduce trace sampling rate
- Increase slow request threshold
- Use `enqueue=True` for async logging (default)
```

### Step 5: Common Test Patterns

From the specification, here are essential test patterns for Loguru:

#### Basic Testing with pytest

```python
import pytest
from loguru import logger

def test_with_caplog(caplog):
    """Test logging with pytest's caplog fixture."""
    # caplog works with Loguru via InterceptHandler
    with caplog.at_level("INFO"):
        logger.info("Test message")

    assert "Test message" in caplog.text
    assert caplog.records[0].levelname == "INFO"
```

#### Creating a Test Sink

```python
import pytest
from loguru import logger

@pytest.fixture
def capture_logs():
    """Fixture to capture Loguru logs."""
    # Remove default handlers
    logger.remove()

    # Create list to capture logs
    logs = []

    # Add handler that captures to list
    handler_id = logger.add(
        lambda msg: logs.append(msg),
        format="{time} | {level} | {message} | {extra}",
        level="DEBUG"
    )

    yield logs

    # Cleanup
    logger.remove(handler_id)
    # Re-add default handler for other tests
    logger.add(sys.stderr)

def test_with_capture(capture_logs):
    """Test using custom log capture."""
    logger.info("Test message", user_id=123)

    assert len(capture_logs) == 1
    assert "Test message" in capture_logs[0]
    assert "user_id" in capture_logs[0]
```

#### Testing Async Code

```python
@pytest.mark.asyncio
async def test_async_logging(capture_logs):
    """Test logging in async functions."""
    async def async_operation():
        logger.info("Starting async operation")
        await asyncio.sleep(0.1)
        logger.info("Completed async operation")

    await async_operation()

    assert len(capture_logs) == 2
    assert "Starting async operation" in capture_logs[0]
    assert "Completed async operation" in capture_logs[1]
```

#### Testing Context Propagation

```python
@pytest.mark.asyncio
async def test_context_propagation(capture_logs):
    """Test that context propagates through async calls."""
    async def nested_operation():
        logger.info("Nested operation")

    with logger.contextualize(request_id="test-123"):
        logger.info("Main operation")
        await nested_operation()

    # Both logs should have request_id
    for log in capture_logs:
        assert "request_id" in log
        assert "test-123" in log
```

#### Testing Structured Data

```python
import json

@pytest.fixture
def json_logs():
    """Capture logs as JSON."""
    logger.remove()
    logs = []

    def sink(message):
        # Parse the JSON log entry
        logs.append(json.loads(message))

    handler_id = logger.add(sink, serialize=True, level="DEBUG")

    yield logs

    logger.remove(handler_id)
    logger.add(sys.stderr)

def test_structured_logging(json_logs):
    """Test structured logging output."""
    logger.info("User action", user_id=123, action="login")

    assert len(json_logs) == 1
    log_entry = json_logs[0]

    assert log_entry["text"] == "User action"
    assert log_entry["record"]["extra"]["user_id"] == 123
    assert log_entry["record"]["extra"]["action"] == "login"
```

#### Best Practices for Testing with Loguru

1. **Always clean up handlers** in fixtures to avoid interference between tests
2. **Use `logger.remove()` carefully** - it removes ALL handlers
3. **Test both message and context** - Loguru excels at structured logging
4. **Mock sparingly** - Loguru is fast enough for most integration tests
5. **Test async context propagation** - Critical for correlation IDs

### Step 6: Final Cleanup Checklist

Create `MIGRATION_COMPLETE.md`:

```markdown
# Observability Migration Complete! 🎉

## What Changed

### Before (3,052 lines)
- Complex structlog configuration
- Custom observability module
- Advanced error context
- Extensive request logging
- 30+ configuration options
- GCP-only implementation

### After (~300 lines)
- Simple Loguru setup
- Native OpenTelemetry
- Basic sanitization
- Lightweight middleware
- 11 configuration options
- Cloud-agnostic design

## Key Improvements

1. **90% code reduction** - Easier to maintain
2. **Cloud portability** - Switch providers via config
3. **Local development** - No cloud dependencies
4. **Better performance** - Less overhead
5. **Simpler testing** - Fewer mocks needed

## Verification Steps

- [x] All old modules removed
- [x] Dependencies updated
- [x] All imports migrated
- [x] Tests passing
- [x] Lint/type checks passing
- [x] Documentation updated
- [x] Integration tests added

## Configuration Summary

### Essential Settings
- `LOG_CONFIG__LOG_LEVEL` - Logging verbosity
- `LOG_CONFIG__LOG_FORMATTER_TYPE` - Output format
- `OBSERVABILITY_CONFIG__EXPORTER_TYPE` - Trace backend
- `OBSERVABILITY_CONFIG__TRACE_SAMPLE_RATE` - Sampling

### Auto-Detection
If not specified, the system auto-detects:
- Console formatter for development
- Cloud formatter for production
- Appropriate trace exporter

## Next Steps

1. Deploy to staging
2. Monitor performance
3. Adjust sampling rates
4. Consider cloud DLP APIs for compliance

## Rollback Plan

If issues arise:
```bash
git checkout pre-observability-migration
```

But with 100% test coverage, this is unlikely.
```

## Validation Checklist

- [ ] All configuration finalized
- [ ] **Final .env.example created with only 11 settings**
- [ ] **Configuration validation script passes**
- [ ] **All obsolete settings removed**
- [ ] **Constants files properly cleaned**
- [ ] Integration tests created and passing
- [ ] Environment detection working
- [ ] Cloud-agnostic operation verified
- [ ] Documentation updated
- [ ] Migration verification script created
- [ ] All components integrated
- [ ] No old imports remaining
- [ ] **Docker-compose.yml environment cleaned**
- [ ] **CI/CD workflows updated**
- [ ] `make all-checks` passes
- [ ] Ready for deployment

## Expected Results

After Phase 6:
- Complete observability stack working
- Easy cloud migration via configuration
- Comprehensive integration tests
- Full documentation
- 90% code reduction achieved
- Cloud-agnostic implementation

## Final Testing

```bash
# Run verification script
python scripts/verify_migration.py

# Test all formatters
for formatter in console json gcp aws; do
    echo "Testing $formatter formatter..."
    LOG_CONFIG__LOG_FORMATTER_TYPE=$formatter make dev &
    sleep 5
    curl http://localhost:8000/
    kill %1
done

# Run all tests
make test

# Check code quality
make all-checks
```

## Summary

The migration is complete! The new observability stack:

1. **Works anywhere** - Local, GCP, AWS, self-hosted
2. **Simple to use** - Standard Loguru + OpenTelemetry
3. **Easy to maintain** - 90% less code
4. **Fast to migrate** - Change config, not code
5. **Well tested** - 100% coverage maintained

The system is now ready for deployment to any environment.
