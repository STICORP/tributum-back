"""Unit tests for configuration management."""

import pytest
import pytest_check
from pydantic import ValidationError

from src.core.config import LogConfig, Settings, get_settings


class TestLogConfig:
    """Test cases for LogConfig class."""

    def test_default_values(self) -> None:
        """Test default values for LogConfig."""
        config = LogConfig()
        assert config.log_level == "INFO"
        assert config.log_format == "console"
        assert config.render_json_logs is False
        assert config.add_timestamp is True
        assert config.timestamper_format == "iso"

    def test_custom_values(self) -> None:
        """Test custom values for LogConfig."""
        config = LogConfig(
            log_level="DEBUG",
            log_format="json",
            render_json_logs=True,
            add_timestamp=False,
            timestamper_format="unix",
        )
        assert config.log_level == "DEBUG"
        assert config.log_format == "json"
        assert config.render_json_logs is True
        assert config.add_timestamp is False
        assert config.timestamper_format == "unix"


class TestSettings:
    """Test cases for Settings class."""

    def test_default_settings(self) -> None:
        """Test that default settings are loaded correctly."""
        settings = Settings()

        # Application settings
        with pytest_check.check:
            assert settings.app_name == "Tributum"
        with pytest_check.check:
            assert settings.app_version == "0.2.0"
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

        # Logging (with pytest-env overrides)
        with pytest_check.check:
            assert isinstance(settings.log_config, LogConfig)
        with pytest_check.check:
            assert settings.log_config.log_level == "WARNING"  # Set by pytest-env
        with pytest_check.check:
            assert settings.log_config.log_format == "console"
        with pytest_check.check:
            assert settings.log_config.render_json_logs is False
        with pytest_check.check:
            assert settings.log_config.add_timestamp is False  # Set by pytest-env
        with pytest_check.check:
            assert settings.log_config.timestamper_format == "iso"

    def test_environment_variable_override(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that environment variables override default settings."""
        monkeypatch.setenv("APP_NAME", "Test App")
        monkeypatch.setenv("APP_VERSION", "2.0.0")
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("DEBUG", "false")
        monkeypatch.setenv("API_PORT", "9000")
        monkeypatch.setenv("LOG_CONFIG__LOG_LEVEL", "DEBUG")
        monkeypatch.setenv("LOG_CONFIG__LOG_FORMAT", "json")

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
        with pytest_check.check:
            assert settings.log_config.log_level == "DEBUG"
        # In production, console format should be overridden to json
        with pytest_check.check:
            assert settings.log_config.log_format == "json"
        with pytest_check.check:
            assert settings.log_config.render_json_logs is True

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
        """Test that production environment automatically sets JSON logs.

        Uses the production_env fixture to set up production environment.
        """
        _ = production_env  # Fixture sets up environment
        settings = Settings()
        assert settings.environment == "production"
        assert settings.log_config.log_format == "json"
        assert settings.log_config.render_json_logs is True

    def test_development_environment_console_logs(self, development_env: None) -> None:
        """Test that development environment keeps console logs.

        Uses the development_env fixture to set up development environment.
        """
        _ = development_env  # Fixture sets up environment
        settings = Settings()
        assert settings.environment == "development"
        assert settings.log_config.log_format == "console"
        assert settings.log_config.render_json_logs is False


class TestGetSettings:
    """Test cases for get_settings function."""

    def test_get_settings_caching(self) -> None:
        """Test that get_settings returns the same instance (cached).

        Note: The clear_settings_cache fixture automatically clears cache
        before and after each test, so we test caching within a single test.
        """
        settings1 = get_settings()
        settings2 = get_settings()

        assert settings1 is settings2

    def test_get_settings_cache_clear(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that cache can be cleared to get new settings.

        The clear_settings_cache fixture handles automatic clearing,
        but we test manual clearing within a test.
        """
        # Get initial settings
        settings1 = get_settings()
        initial_name = settings1.app_name

        # Clear the cache manually
        get_settings.cache_clear()

        # Modify environment and get new settings
        monkeypatch.setenv("APP_NAME", "Modified App")
        settings2 = get_settings()

        assert settings1 is not settings2
        assert settings2.app_name == "Modified App"
        assert initial_name == "Tributum"  # Verify initial was default
