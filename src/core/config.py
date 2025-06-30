"""Configuration management module for Tributum application.

This module provides a centralized configuration management system using
Pydantic Settings. It supports environment variables and .env files.
"""

from functools import lru_cache
from typing import Literal

from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class LogConfig(BaseModel):
    """Minimal logging configuration for Phase 0."""

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
        description="Paths to exclude from logging",
    )
    slow_request_threshold_ms: int = Field(
        default=1000,
        gt=0,
        description="Log warning if request slower than this (ms)",
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
    """Minimal observability configuration for Phase 0."""

    enable_tracing: bool = Field(
        default=False,
        description="Tracing disabled in Phase 0",
    )
    gcp_project_id: str | None = Field(
        default=None,
        description="GCP project ID for Cloud Trace exporter",
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
        """Get database URL for testing purposes.

        Returns a modified database URL with '_test' suffix appended to the
        database name. This ensures tests run against a separate database.

        Returns:
            str: Test database URL
        """
        # Parse the database URL to replace the database name with test database
        if "/tributum_db" in self.database_url:
            return self.database_url.replace("/tributum_db", "/tributum_test")
        if "/tributum" in self.database_url:
            return self.database_url.replace("/tributum", "/tributum_test")
        # For other database names, parse and append _test
        # This handles cases where the database name might be different
        parts = self.database_url.rsplit("/", 1)
        expected_parts = 2
        if len(parts) == expected_parts:
            base_url, db_name = parts
            # Remove any query parameters from db_name
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
        """Post initialization to adjust log configuration based on environment."""
        super().model_post_init(__context)
        # In production, default to JSON logs
        if self.environment in ("production", "staging"):
            self.log_config.log_formatter_type = "json"

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
    """Get cached settings instance.

    This function uses lru_cache to ensure that the settings are only
    loaded once during the application lifecycle, improving performance.

    Returns:
        Settings: The application settings instance.
    """
    return Settings()
