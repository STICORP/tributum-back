"""Shared fixtures for unit tests."""

import os
import threading
from collections.abc import Generator
from pathlib import Path
from typing import Any, cast

import pytest
from pytest_mock import MockerFixture, MockType

from src.core.config import LogConfig, Settings, get_settings
from src.core.context import RequestContext
from src.core.error_context import _get_sensitive_fields


@pytest.fixture
def mock_settings(monkeypatch: pytest.MonkeyPatch) -> Settings:
    """Provide mock Settings object with required attributes.

    Returns:
        Settings: Mock settings object with test defaults.
    """
    # Set environment variables to create test settings
    monkeypatch.setenv("APP_NAME", "TestApp")
    monkeypatch.setenv("APP_VERSION", "1.0.0")
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("DEBUG", "false")
    monkeypatch.setenv("API_HOST", "127.0.0.1")
    monkeypatch.setenv("API_PORT", "3000")

    # Create a real Settings object with test values
    # This ensures type safety and all required attributes
    return Settings()


@pytest.fixture
def mock_app(mocker: MockerFixture) -> MockType:
    """Provide mock FastAPI app instance.

    Args:
        mocker: Pytest mocker fixture.

    Returns:
        MockType: Mock app that can be passed to uvicorn.run.
    """
    app = mocker.Mock()
    app.__name__ = "mock_app"
    app.__module__ = "tests.unit.conftest"
    return cast("MockType", app)


@pytest.fixture
def mock_uvicorn(mocker: MockerFixture) -> MockType:
    """Mock uvicorn.run to prevent server startup.

    Args:
        mocker: Pytest mocker fixture.

    Returns:
        MockType: The mock for assertion purposes.
    """
    return mocker.patch("uvicorn.run")


@pytest.fixture
def isolated_env(monkeypatch: pytest.MonkeyPatch) -> pytest.MonkeyPatch:
    """Isolate environment variables for testing.

    Args:
        monkeypatch: Pytest monkeypatch fixture.

    Returns:
        pytest.MonkeyPatch: The monkeypatch instance for env manipulation.
    """
    # Ensure PORT is not set unless explicitly required by test
    monkeypatch.delenv("PORT", raising=False)
    return monkeypatch


@pytest.fixture
def mock_main_dependencies(
    mocker: MockerFixture,
    mock_settings: Settings,
) -> dict[str, MockType]:
    """Mock common main.py dependencies.

    Args:
        mocker: Pytest mocker fixture.
        mock_settings: Mock settings fixture.

    Returns:
        dict[str, MockType]: Dictionary of mocked dependencies.
    """
    mocks = {
        "get_settings": mocker.patch("main.get_settings"),
        "setup_logging": mocker.patch("main.setup_logging"),
        "logger": mocker.patch("main.logger"),
        "uvicorn_run": mocker.patch("uvicorn.run"),
    }
    mocks["get_settings"].return_value = mock_settings
    return mocks


@pytest.fixture(autouse=True)
def clean_lru_cache() -> Generator[None]:
    """Clear the LRU cache before and after each test to ensure isolation.

    This fixture is autouse to ensure all tests start with a fresh cache
    and don't interfere with each other.
    """
    # Clear cache before test
    get_settings.cache_clear()
    yield
    # Clear cache after test
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def clean_env(
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[pytest.MonkeyPatch]:
    """Backup and restore environment variables to prevent test interference.

    This fixture ensures complete isolation of environment variables
    between tests. It's autouse to guarantee clean state for all tests.

    Args:
        monkeypatch: Pytest monkeypatch fixture.

    Returns:
        pytest.MonkeyPatch: The monkeypatch instance for env manipulation.
    """
    # Save current environment
    original_env = os.environ.copy()

    # Clear any app-specific env vars that might interfere
    # Don't clear cloud environment variables as they're needed for detection tests
    env_prefixes = [
        "APP_",
        "API_",
        "ENVIRONMENT",
        "DEBUG",
        "LOG_CONFIG__",
        "OBSERVABILITY_CONFIG__",
        "DATABASE_CONFIG__",
    ]
    for key in list(os.environ.keys()):
        if any(key.startswith(prefix) for prefix in env_prefixes):
            monkeypatch.delenv(key, raising=False)

    yield monkeypatch

    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def temp_env_file(tmp_path: Path) -> Path:
    """Create temporary .env files for testing file-based configuration.

    Args:
        tmp_path: Pytest tmp_path fixture for temporary directories.

    Returns:
        Path: Path to the temporary .env file.
    """
    return tmp_path / ".env"


@pytest.fixture
def mock_cloud_env(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Mock cloud environment detection (GCP/AWS).

    Args:
        monkeypatch: Pytest monkeypatch fixture.

    Returns:
        dict[str, Any]: Dictionary with helper methods for setting cloud environments.
    """

    def set_gcp() -> None:
        """Set GCP Cloud Run environment variables."""
        monkeypatch.setenv("K_SERVICE", "test-service")
        monkeypatch.setenv("K_REVISION", "test-revision")

    def set_aws() -> None:
        """Set AWS environment variables."""
        monkeypatch.setenv("AWS_EXECUTION_ENV", "AWS_Lambda_python3.13")
        monkeypatch.setenv("AWS_REGION", "us-east-1")

    def set_both() -> None:
        """Set both GCP and AWS environment variables (for conflict testing)."""
        set_gcp()
        set_aws()

    def clear_all() -> None:
        """Clear all cloud environment variables."""
        for key in ["K_SERVICE", "K_REVISION", "AWS_EXECUTION_ENV", "AWS_REGION"]:
            monkeypatch.delenv(key, raising=False)

    return {
        "set_gcp": set_gcp,
        "set_aws": set_aws,
        "set_both": set_both,
        "clear_all": clear_all,
    }


@pytest.fixture
def mock_get_settings(mocker: MockerFixture) -> MockType:
    """Mock get_settings function with customizable sensitive_fields.

    This fixture is used for error_context tests to control sensitive field detection.

    Args:
        mocker: Pytest mocker fixture.

    Returns:
        MockType: Mock get_settings function.
    """
    mock_settings = mocker.Mock(spec=Settings)
    mock_log_config = mocker.Mock(spec=LogConfig)
    mock_log_config.sensitive_fields = ["custom_secret", "my_password", "api_token"]
    mock_settings.log_config = mock_log_config

    mock_get_settings_fn = mocker.patch("src.core.error_context.get_settings")
    mock_get_settings_fn.return_value = mock_settings

    # Clear cache before returning
    _get_sensitive_fields.cache_clear()

    return mock_get_settings_fn


@pytest.fixture
def sample_sensitive_data() -> dict[str, Any]:
    """Provide test data structures with sensitive fields for sanitization.

    Returns:
        dict[str, Any]: Nested data with sensitive fields at various depths.
    """
    return {
        "username": "john_doe",
        "password": "secret123",
        "user_data": {
            "email": "john@example.com",
            "api_key": "sk-1234567890",
            "profile": {
                "name": "John Doe",
                "secret_token": "bearer-xyz",
                "preferences": {
                    "theme": "dark",
                    "private_key": "rsa_private_key_placeholder",
                },
            },
        },
        "metadata": {
            "created_at": "2024-01-01",
            "session_id": "sess_abc123",
            "tags": ["user", "premium"],
            "credentials": {"auth_token": "auth_xyz", "refresh_token": "refresh_abc"},
        },
        "items": [
            {"id": 1, "name": "Item 1", "token": "item_token_1"},
            {"id": 2, "name": "Item 2", "access_key": "item_key_2"},
        ],
        "tuple_data": ("public", "password123", {"secret": "hidden"}),
    }


@pytest.fixture
def thread_test_context(thread_sync: dict[str, Any]) -> dict[str, Any]:
    """Extend thread_sync specifically for error_context thread safety tests.

    Provides pre-configured barriers and result collectors for thread safety tests.

    Args:
        thread_sync: Base thread synchronization fixture.

    Returns:
        dict[str, Any]: Extended thread test utilities.
    """
    return {
        **thread_sync,
        "results": thread_sync["create_results"](),
        "errors": thread_sync["create_results"](),
    }


@pytest.fixture
def thread_sync() -> dict[str, Any]:
    """Provide thread synchronization utilities for thread safety tests.

    Returns:
        dict[str, Any]: Dictionary with threading utilities.
    """

    def create_barrier(n: int) -> threading.Barrier:
        """Create a barrier for n threads."""
        return threading.Barrier(n)

    def create_results() -> list[Any]:
        """Create a new thread-safe results list."""
        return []

    return {
        "barrier": create_barrier,
        "event": threading.Event,
        "lock": threading.Lock,
        "create_results": create_results,
    }


@pytest.fixture(autouse=True)
def clean_context() -> Generator[None]:
    """Clear context before and after each test to ensure isolation.

    This fixture is autouse to ensure all tests start with a clean context
    and don't interfere with each other.
    """
    # Clear context before test
    RequestContext.clear()
    yield
    # Clear context after test
    RequestContext.clear()
