"""Centralized configuration management with environment-aware defaults.

This module implements a comprehensive configuration system using Pydantic
Settings, providing type-safe configuration with validation, environment
variable support, and cloud provider auto-detection.

Features:
- **Type safety**: All configuration values are validated and typed
- **Environment variables**: Supports .env files and environment overrides
- **Nested configuration**: Uses __ delimiter for complex config structures
- **Auto-detection**: Automatically detects cloud environments (GCP, AWS)
- **Validation**: Built-in constraints and custom validators
- **Caching**: Configuration is cached for performance

Configuration sources (in order of precedence):
1. Environment variables
2. .env file in project root
3. Default values in model definitions
4. Environment-based defaults (production vs development)
"""

import os
from functools import lru_cache
from typing import Any, Literal

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
    slow_query_threshold_ms: int = Field(
        default=100,
        gt=0,
        description="Slow query threshold in milliseconds",
    )
    sensitive_fields: list[str] = Field(
        default_factory=lambda: [
            "password",
            "token",
            "secret",
            "api_key",
            "authorization",
        ],
        description="Field names to redact",
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

    @field_validator("exporter_endpoint", "gcp_project_id", mode="before")
    @classmethod
    def empty_str_to_none(cls, v: str | None) -> str | None:
        """Convert empty strings to None for nullable fields."""
        if v == "":
            return None
        return v


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
        # Check for cloud environments first (more authoritative)
        if os.getenv("K_SERVICE"):  # Cloud Run
            return "gcp"
        if os.getenv("AWS_EXECUTION_ENV"):  # AWS
            return "aws"

        # Fall back to environment-based defaults
        if self.environment == "development":
            return "console"
        return "json"  # Generic JSON for production

    def _detect_exporter(self) -> Literal["console", "gcp", "aws", "otlp", "none"]:
        """Auto-detect trace exporter based on environment."""
        # Check for cloud environments first (more authoritative)
        if os.getenv("K_SERVICE"):  # Cloud Run
            return "gcp"
        if os.getenv("AWS_EXECUTION_ENV"):  # AWS
            return "aws"

        # Fall back to environment-based defaults
        if self.environment == "development":
            return "console"
        return "otlp"  # Generic OTLP

    @field_validator("docs_url", "redoc_url", "openapi_url", mode="before")
    @classmethod
    def empty_str_to_none(cls, v: str | None) -> str | None:
        """Convert empty strings to None for nullable fields."""
        # cls is the Settings class, required by Pydantic validators
        _ = cls  # Mark as used to satisfy vulture
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
        dict[str, Any]: Default configuration values.
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
    # Development defaults
    return {
        "log_config": {
            "log_formatter_type": "console",
        },
        "observability_config": {
            "exporter_type": "console",
        },
    }
