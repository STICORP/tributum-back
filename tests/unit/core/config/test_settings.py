"""Unit tests for Settings class."""

import pytest
import pytest_check
from pydantic import ValidationError

from src.core.config import (
    DatabaseConfig,
    LogConfig,
    ObservabilityConfig,
    Settings,
    get_settings,
)


@pytest.mark.unit
class TestSettings:
    """Test cases for Settings class."""

    def test_default_application_settings(self) -> None:
        """Test default application settings."""
        settings = Settings()

        # Application settings
        with pytest_check.check:
            assert settings.app_name == "Tributum"
        with pytest_check.check:
            assert settings.app_version  # Just check it exists and is not empty
        with pytest_check.check:
            assert settings.environment == "development"  # pytest-env sets this
        with pytest_check.check:
            assert settings.debug is True

        # API settings
        with pytest_check.check:
            assert settings.api_host == "127.0.0.1"
        with pytest_check.check:
            assert settings.api_port == 8000
        with pytest_check.check:
            assert settings.docs_url == "/docs"
        with pytest_check.check:
            assert settings.redoc_url == "/redoc"
        with pytest_check.check:
            assert settings.openapi_url == "/openapi.json"

    def test_default_log_config(self) -> None:
        """Test default logging configuration."""
        settings = Settings()

        # Logging (with pytest-env overrides)
        with pytest_check.check:
            assert isinstance(settings.log_config, LogConfig)
        with pytest_check.check:
            assert settings.log_config.log_level == "WARNING"  # Set by pytest-env
        with pytest_check.check:
            assert (
                settings.log_config.log_formatter_type == "console"
            )  # Auto-detected as console for development

    def test_default_observability_config(self) -> None:
        """Test default observability configuration."""
        settings = Settings()

        # Observability
        with pytest_check.check:
            assert isinstance(settings.observability_config, ObservabilityConfig)
        with pytest_check.check:
            assert settings.observability_config.enable_tracing is True
        with pytest_check.check:
            assert settings.observability_config.exporter_type == "console"
        with pytest_check.check:
            assert settings.observability_config.exporter_endpoint is None
        with pytest_check.check:
            assert settings.observability_config.gcp_project_id is None
        with pytest_check.check:
            assert settings.observability_config.trace_sample_rate == 1.0

    def test_default_database_config(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test default database configuration."""
        # Clear the test environment database URL to test actual defaults
        monkeypatch.delenv("DATABASE_CONFIG__DATABASE_URL", raising=False)
        get_settings.cache_clear()

        settings = Settings()

        # Database
        with pytest_check.check:
            assert isinstance(settings.database_config, DatabaseConfig)
        with pytest_check.check:
            assert (
                settings.database_config.database_url
                == "postgresql+asyncpg://tributum:tributum_pass@localhost:5432/tributum_db"
            )
        with pytest_check.check:
            assert settings.database_config.pool_size == 10
        with pytest_check.check:
            assert settings.database_config.max_overflow == 5
        with pytest_check.check:
            assert settings.database_config.pool_timeout == 30.0
        with pytest_check.check:
            assert settings.database_config.pool_pre_ping is True
        with pytest_check.check:
            assert settings.database_config.echo is False

    def test_application_env_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test application environment variable overrides."""
        monkeypatch.setenv("APP_NAME", "Test App")
        monkeypatch.setenv("APP_VERSION", "2.0.0")
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("DEBUG", "false")
        monkeypatch.setenv("API_PORT", "9000")

        settings = Settings()

        with pytest_check.check:
            assert settings.app_name == "Test App"
        with pytest_check.check:
            assert settings.app_version == "2.0.0"
        with pytest_check.check:
            assert settings.environment == "production"
        with pytest_check.check:
            assert settings.debug is False
        with pytest_check.check:
            assert settings.api_port == 9000

    def test_log_config_env_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test log configuration environment variable overrides."""
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("LOG_CONFIG__LOG_LEVEL", "DEBUG")
        monkeypatch.setenv("LOG_CONFIG__LOG_FORMATTER_TYPE", "json")

        settings = Settings()

        with pytest_check.check:
            assert settings.log_config.log_level == "DEBUG"
        # In production, console format should be overridden to json
        with pytest_check.check:
            assert settings.log_config.log_formatter_type == "json"

    def test_case_insensitive_env_vars(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that environment variables are case-insensitive."""
        monkeypatch.setenv("app_name", "Lower Case App")
        monkeypatch.setenv("API_HOST", "127.0.0.1")

        settings = Settings()

        assert settings.app_name == "Lower Case App"
        assert settings.api_host == "127.0.0.1"

    def test_invalid_environment_value(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that invalid environment values raise validation errors."""
        monkeypatch.setenv("ENVIRONMENT", "invalid_env")

        with pytest.raises(
            ValidationError,
            match="Input should be 'development', 'staging' or 'production'",
        ):
            Settings()

    def test_invalid_log_level(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that invalid log levels raise validation errors."""
        monkeypatch.setenv("LOG_CONFIG__LOG_LEVEL", "INVALID")

        with pytest.raises(
            ValidationError,
            match=("Input should be 'DEBUG', 'INFO', 'WARNING', 'ERROR' or 'CRITICAL'"),
        ):
            Settings()

    def test_nullable_doc_urls(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that documentation URLs can be set to None."""
        monkeypatch.setenv("DOCS_URL", "")
        monkeypatch.setenv("REDOC_URL", "")
        monkeypatch.setenv("OPENAPI_URL", "")

        settings = Settings()

        assert settings.docs_url is None
        assert settings.redoc_url is None
        assert settings.openapi_url is None

    def test_production_environment_json_logs(self, production_env: None) -> None:
        """Test that production environment sets JSON logs.

        Uses the production_env fixture to set up production environment.
        """
        _ = production_env  # Fixture sets up environment
        settings = Settings()
        assert settings.environment == "production"
        assert settings.log_config.log_formatter_type == "json"

    def test_development_environment_console_logs(self, development_env: None) -> None:
        """Test that development environment keeps console logs.

        Uses the development_env fixture to set up development environment.
        """
        _ = development_env  # Fixture sets up environment
        settings = Settings()
        assert settings.environment == "development"
        assert settings.log_config.log_formatter_type == "console"
