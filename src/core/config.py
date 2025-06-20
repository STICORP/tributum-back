"""Configuration management module for Tributum application.

This module provides a centralized configuration management system using
Pydantic Settings. It supports environment variables and .env files.
"""

from functools import lru_cache
from typing import Literal

from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class LogConfig(BaseModel):
    """Logging configuration settings."""

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO", description="Logging level"
    )
    log_format: Literal["json", "console"] = Field(
        default="console", description="Log output format"
    )
    render_json_logs: bool = Field(
        default=False, description="Whether to render logs as JSON"
    )
    add_timestamp: bool = Field(
        default=True, description="Whether to add timestamp to logs"
    )
    timestamper_format: str = Field(
        default="iso", description="Timestamp format (iso or unix)"
    )


class ObservabilityConfig(BaseModel):
    """Observability configuration settings for OpenTelemetry."""

    enable_tracing: bool = Field(
        default=False, description="Whether to enable OpenTelemetry tracing"
    )
    service_name: str = Field(default="tributum", description="Service name for traces")
    gcp_project_id: str | None = Field(
        default=None, description="GCP project ID for Cloud Trace exporter"
    )
    trace_sample_rate: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Trace sampling rate (0.0 to 1.0)",
    )


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

    def model_post_init(self, __context: object) -> None:
        """Post initialization to adjust log configuration based on environment."""
        super().model_post_init(__context)
        # In production, default to JSON logs only if not explicitly set
        if (
            self.environment in ("production", "staging")
            and self.log_config.log_format == "console"
            and not self.log_config.render_json_logs
        ):
            self.log_config.log_format = "json"
            self.log_config.render_json_logs = True

        # Ensure render_json_logs matches log_format
        if self.log_config.log_format == "json":
            self.log_config.render_json_logs = True

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
