"""Unit tests for configuration management."""

import os
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from src.core.config import Settings, get_settings


class TestSettings:
    """Test cases for Settings class."""

    def test_default_settings(self) -> None:
        """Test that default settings are loaded correctly."""
        settings = Settings()

        # Application settings
        assert settings.app_name == "Tributum"
        assert settings.app_version == "0.1.0"
        assert settings.environment == "development"
        assert settings.debug is True

        # API settings
        assert settings.api_host == "127.0.0.1"
        assert settings.api_port == 8000
        assert settings.docs_url == "/docs"
        assert settings.redoc_url == "/redoc"
        assert settings.openapi_url == "/openapi.json"

        # Logging
        assert settings.log_level == "INFO"

    def test_environment_variable_override(self) -> None:
        """Test that environment variables override default settings."""
        with patch.dict(
            os.environ,
            {
                "APP_NAME": "Test App",
                "APP_VERSION": "2.0.0",
                "ENVIRONMENT": "production",
                "DEBUG": "false",
                "API_PORT": "9000",
                "LOG_LEVEL": "DEBUG",
            },
        ):
            settings = Settings()

            assert settings.app_name == "Test App"
            assert settings.app_version == "2.0.0"
            assert settings.environment == "production"
            assert settings.debug is False
            assert settings.api_port == 9000
            assert settings.log_level == "DEBUG"

    def test_case_insensitive_env_vars(self) -> None:
        """Test that environment variables are case-insensitive."""
        with patch.dict(
            os.environ, {"app_name": "Lower Case App", "API_HOST": "127.0.0.1"}
        ):
            settings = Settings()

            assert settings.app_name == "Lower Case App"
            assert settings.api_host == "127.0.0.1"

    def test_invalid_environment_value(self) -> None:
        """Test that invalid environment values raise validation errors."""
        with (
            patch.dict(os.environ, {"ENVIRONMENT": "invalid_env"}),
            pytest.raises(
                ValidationError,
                match="Input should be 'development', 'staging' or 'production'",
            ),
        ):
            Settings()

    def test_invalid_log_level(self) -> None:
        """Test that invalid log levels raise validation errors."""
        with (
            patch.dict(os.environ, {"LOG_LEVEL": "INVALID"}),
            pytest.raises(
                ValidationError,
                match=(
                    "Input should be 'DEBUG', 'INFO', 'WARNING', 'ERROR' or 'CRITICAL'"
                ),
            ),
        ):
            Settings()

    def test_nullable_doc_urls(self) -> None:
        """Test that documentation URLs can be set to None."""
        with patch.dict(
            os.environ, {"DOCS_URL": "", "REDOC_URL": "", "OPENAPI_URL": ""}
        ):
            settings = Settings()

            assert settings.docs_url is None
            assert settings.redoc_url is None
            assert settings.openapi_url is None


class TestGetSettings:
    """Test cases for get_settings function."""

    def test_get_settings_caching(self) -> None:
        """Test that get_settings returns the same instance (cached)."""
        settings1 = get_settings()
        settings2 = get_settings()

        assert settings1 is settings2

    def test_get_settings_cache_clear(self) -> None:
        """Test that cache can be cleared to get new settings."""
        # Clear any existing cache first
        get_settings.cache_clear()

        # Get settings with default values
        with patch.dict(os.environ, {}, clear=True):
            settings1 = get_settings()

        # Clear the cache
        get_settings.cache_clear()

        # Modify environment and get new settings
        with patch.dict(os.environ, {"APP_NAME": "Modified App"}, clear=True):
            settings2 = get_settings()

        assert settings1 is not settings2
        assert settings1.app_name == "Tributum"
        assert settings2.app_name == "Modified App"
