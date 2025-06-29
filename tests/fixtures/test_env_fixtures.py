"""Environment-specific test fixtures."""

from collections.abc import Generator

import pytest

from src.core.config import get_settings


@pytest.fixture
def production_env(monkeypatch: pytest.MonkeyPatch) -> Generator[None]:
    """Set up production environment configuration.

    This fixture overrides the test environment to simulate production settings.
    It automatically clears the settings cache before and after the test.

    Args:
        monkeypatch: Pytest monkeypatch fixture for environment manipulation.
    """
    # Clear cache before modifying environment
    get_settings.cache_clear()

    # Set production environment variables
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("DEBUG", "false")
    monkeypatch.setenv("LOG_CONFIG__LOG_FORMATTER_TYPE", "json")

    yield

    # Clear cache after test to ensure clean state
    get_settings.cache_clear()


@pytest.fixture
def development_env(monkeypatch: pytest.MonkeyPatch) -> Generator[None]:
    """Set up development environment configuration.

    This fixture ensures development environment settings are applied.
    It automatically clears the settings cache before and after the test.

    Args:
        monkeypatch: Pytest monkeypatch fixture for environment manipulation.
    """
    # Clear cache before modifying environment
    get_settings.cache_clear()

    # Set development environment variables
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("DEBUG", "true")
    monkeypatch.setenv("LOG_CONFIG__LOG_FORMATTER_TYPE", "console")

    yield

    # Clear cache after test to ensure clean state
    get_settings.cache_clear()


@pytest.fixture
def staging_env(monkeypatch: pytest.MonkeyPatch) -> Generator[None]:
    """Set up staging environment configuration.

    This fixture configures staging environment settings.
    It automatically clears the settings cache before and after the test.

    Args:
        monkeypatch: Pytest monkeypatch fixture for environment manipulation.
    """
    # Clear cache before modifying environment
    get_settings.cache_clear()

    # Set staging environment variables
    monkeypatch.setenv("ENVIRONMENT", "staging")
    monkeypatch.setenv("DEBUG", "false")
    monkeypatch.setenv("LOG_CONFIG__LOG_FORMATTER_TYPE", "json")

    yield

    # Clear cache after test to ensure clean state
    get_settings.cache_clear()


@pytest.fixture
def custom_app_env(monkeypatch: pytest.MonkeyPatch) -> Generator[None]:
    """Set up custom application configuration for testing.

    This fixture provides a custom app name and version for tests that need
    to verify environment variable overrides.

    Args:
        monkeypatch: Pytest monkeypatch fixture for environment manipulation.
    """
    # Clear cache before modifying environment
    get_settings.cache_clear()

    # Set custom app configuration
    monkeypatch.setenv("APP_NAME", "Custom Test App")
    monkeypatch.setenv("APP_VERSION", "99.99.99")

    yield

    # Clear cache after test to ensure clean state
    get_settings.cache_clear()


@pytest.fixture
def no_docs_env(monkeypatch: pytest.MonkeyPatch) -> Generator[None]:
    """Disable all documentation endpoints.

    This fixture ensures all API documentation endpoints are disabled,
    which is the default for test environment but can be explicitly applied.

    Args:
        monkeypatch: Pytest monkeypatch fixture for environment manipulation.
    """
    # Clear cache before modifying environment
    get_settings.cache_clear()

    # Disable all documentation endpoints
    monkeypatch.setenv("DOCS_URL", "")
    monkeypatch.setenv("REDOC_URL", "")
    monkeypatch.setenv("OPENAPI_URL", "")

    yield

    # Clear cache after test to ensure clean state
    get_settings.cache_clear()
