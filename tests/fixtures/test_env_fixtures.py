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


@pytest.fixture
def debug_disabled_env(monkeypatch: pytest.MonkeyPatch) -> Generator[None]:
    """Disable debug mode for testing.

    This fixture sets debug mode to False to test production-like behavior.

    Args:
        monkeypatch: Pytest monkeypatch fixture for environment manipulation.
    """
    # Clear cache before modifying environment
    get_settings.cache_clear()

    # Disable debug mode
    monkeypatch.setenv("DEBUG", "false")

    yield

    # Clear cache after test to ensure clean state
    get_settings.cache_clear()


@pytest.fixture
def empty_docs_env(monkeypatch: pytest.MonkeyPatch) -> Generator[None]:
    """Set documentation URLs to empty strings for conversion testing.

    This fixture specifically tests the empty string to None conversion
    functionality in the configuration system.

    Args:
        monkeypatch: Pytest monkeypatch fixture for environment manipulation.
    """
    # Clear cache before modifying environment
    get_settings.cache_clear()

    # Set documentation URLs to empty strings
    monkeypatch.setenv("DOCS_URL", "")
    monkeypatch.setenv("REDOC_URL", "")
    monkeypatch.setenv("OPENAPI_URL", "")

    yield

    # Clear cache after test to ensure clean state
    get_settings.cache_clear()


@pytest.fixture
def custom_logging_env(monkeypatch: pytest.MonkeyPatch) -> Generator[None]:
    """Set custom logging configuration for testing nested configuration.

    This fixture tests the nested configuration functionality by setting
    various logging-related environment variables.

    Args:
        monkeypatch: Pytest monkeypatch fixture for environment manipulation.
    """
    # Clear cache before modifying environment
    get_settings.cache_clear()

    # Set custom logging configuration
    monkeypatch.setenv("LOG_CONFIG__LOG_LEVEL", "ERROR")
    monkeypatch.setenv("LOG_CONFIG__SLOW_REQUEST_THRESHOLD_MS", "2000")
    monkeypatch.setenv("LOG_CONFIG__LOG_FORMATTER_TYPE", "json")

    yield

    # Clear cache after test to ensure clean state
    get_settings.cache_clear()


@pytest.fixture
def console_formatter_env(monkeypatch: pytest.MonkeyPatch) -> Generator[None]:
    """Set console formatter configuration for testing.

    Args:
        monkeypatch: Pytest monkeypatch fixture for environment manipulation.
    """
    # Clear cache before modifying environment
    get_settings.cache_clear()

    # Set console formatter
    monkeypatch.setenv("LOG_CONFIG__LOG_FORMATTER_TYPE", "console")

    yield

    # Clear cache after test to ensure clean state
    get_settings.cache_clear()


@pytest.fixture
def json_formatter_env(monkeypatch: pytest.MonkeyPatch) -> Generator[None]:
    """Set JSON formatter configuration for testing.

    Args:
        monkeypatch: Pytest monkeypatch fixture for environment manipulation.
    """
    # Clear cache before modifying environment
    get_settings.cache_clear()

    # Set JSON formatter
    monkeypatch.setenv("LOG_CONFIG__LOG_FORMATTER_TYPE", "json")

    yield

    # Clear cache after test to ensure clean state
    get_settings.cache_clear()


@pytest.fixture
def console_exporter_env(monkeypatch: pytest.MonkeyPatch) -> Generator[None]:
    """Set console exporter configuration for testing.

    Args:
        monkeypatch: Pytest monkeypatch fixture for environment manipulation.
    """
    # Clear cache before modifying environment
    get_settings.cache_clear()

    # Set console exporter
    monkeypatch.setenv("OBSERVABILITY_CONFIG__EXPORTER_TYPE", "console")

    yield

    # Clear cache after test to ensure clean state
    get_settings.cache_clear()


@pytest.fixture
def otlp_exporter_env(monkeypatch: pytest.MonkeyPatch) -> Generator[None]:
    """Set OTLP exporter configuration for testing.

    Args:
        monkeypatch: Pytest monkeypatch fixture for environment manipulation.
    """
    # Clear cache before modifying environment
    get_settings.cache_clear()

    # Set OTLP exporter with endpoint
    monkeypatch.setenv("OBSERVABILITY_CONFIG__EXPORTER_TYPE", "otlp")
    monkeypatch.setenv(
        "OBSERVABILITY_CONFIG__EXPORTER_ENDPOINT", "http://localhost:4317"
    )

    yield

    # Clear cache after test to ensure clean state
    get_settings.cache_clear()


@pytest.fixture
def gcp_exporter_env(monkeypatch: pytest.MonkeyPatch) -> Generator[None]:
    """Set GCP exporter configuration for testing.

    Args:
        monkeypatch: Pytest monkeypatch fixture for environment manipulation.
    """
    # Clear cache before modifying environment
    get_settings.cache_clear()

    # Set GCP exporter
    monkeypatch.setenv("OBSERVABILITY_CONFIG__EXPORTER_TYPE", "gcp")

    yield

    # Clear cache after test to ensure clean state
    get_settings.cache_clear()


@pytest.fixture
def aws_formatter_env(monkeypatch: pytest.MonkeyPatch) -> Generator[None]:
    """Set AWS formatter configuration for testing.

    Args:
        monkeypatch: Pytest monkeypatch fixture for environment manipulation.
    """
    # Clear cache before modifying environment
    get_settings.cache_clear()

    # Set AWS formatter with production environment
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("LOG_CONFIG__LOG_FORMATTER_TYPE", "aws")

    yield

    # Clear cache after test to ensure clean state
    get_settings.cache_clear()


@pytest.fixture
def low_sampling_env(monkeypatch: pytest.MonkeyPatch) -> Generator[None]:
    """Set low trace sampling rate for testing.

    Args:
        monkeypatch: Pytest monkeypatch fixture for environment manipulation.
    """
    # Clear cache before modifying environment
    get_settings.cache_clear()

    # Set low sampling rate
    monkeypatch.setenv("OBSERVABILITY_CONFIG__TRACE_SAMPLE_RATE", "0.1")

    yield

    # Clear cache after test to ensure clean state
    get_settings.cache_clear()


@pytest.fixture
def high_sampling_env(monkeypatch: pytest.MonkeyPatch) -> Generator[None]:
    """Set high trace sampling rate for testing.

    Args:
        monkeypatch: Pytest monkeypatch fixture for environment manipulation.
    """
    # Clear cache before modifying environment
    get_settings.cache_clear()

    # Set high sampling rate
    monkeypatch.setenv("OBSERVABILITY_CONFIG__TRACE_SAMPLE_RATE", "1.0")

    yield

    # Clear cache after test to ensure clean state
    get_settings.cache_clear()


class DynamicConfigHelper:
    """Helper class for dynamic configuration switching with proper cache management."""

    def __init__(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Initialize with a monkeypatch instance.

        Args:
            monkeypatch: Pytest monkeypatch fixture for environment manipulation.
        """
        self._monkeypatch = monkeypatch

    def switch_config(self, env_var: str, value: str) -> None:
        """Safely switch configuration with proper cache clearing.

        Args:
            env_var: Environment variable name to set.
            value: Value to set for the environment variable.
        """
        self._monkeypatch.setenv(env_var, value)
        get_settings.cache_clear()


@pytest.fixture
def dynamic_config_env(
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[DynamicConfigHelper]:
    """Provide a helper for testing dynamic configuration switching.

    Enables testing of dynamic configuration switching.

    This fixture enables testing configuration changes within a single test
    while maintaining proper isolation and cache management.

    Args:
        monkeypatch: Pytest monkeypatch fixture for environment manipulation.

    Yields:
        DynamicConfigHelper: Helper instance for configuration switching.
    """
    # Clear cache before test starts
    get_settings.cache_clear()

    yield DynamicConfigHelper(monkeypatch)

    # Clear cache after test to ensure clean state
    get_settings.cache_clear()
