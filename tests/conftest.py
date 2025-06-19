"""Shared test configuration and fixtures."""

from collections.abc import AsyncGenerator, Generator

import pytest
from httpx import ASGITransport, AsyncClient

from src.api.main import app
from src.core.config import get_settings

# Import environment fixtures to make them available to all tests
from tests.fixtures.test_env_fixtures import (
    custom_app_env,
    development_env,
    no_docs_env,
    production_env,
    staging_env,
)

# Re-export fixtures for pytest discovery
__all__ = [
    "clear_settings_cache",
    "client",
    "custom_app_env",
    "development_env",
    "no_docs_env",
    "production_env",
    "staging_env",
]


@pytest.fixture(autouse=True)
def clear_settings_cache() -> Generator[None]:
    """Automatically clear settings cache before and after each test.

    This ensures that each test starts with a fresh settings instance
    and that any environment changes made during the test don't affect
    other tests. With pytest-env, this ensures the configured test
    environment is properly loaded for each test.
    """
    # Clear cache before test to ensure fresh settings with pytest-env config
    get_settings.cache_clear()

    yield

    # Clear cache after test to ensure clean state
    get_settings.cache_clear()


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient]:
    """Create test client for FastAPI app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
