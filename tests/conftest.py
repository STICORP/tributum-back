"""Shared test configuration and fixtures."""

from collections.abc import AsyncGenerator, Generator

import pytest
from httpx import ASGITransport, AsyncClient

from src.api.main import app
from src.core.config import get_settings
from src.core.context import RequestContext

# Import database and docker fixtures for parallel test execution
from tests.fixtures.test_database_fixtures import (
    database_url,
    database_url_base,
    db_engine,
    setup_worker_database,
    worker_database_name,
)
from tests.fixtures.test_docker_fixtures import ensure_postgres_container

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
    "clean_request_context",
    "clear_settings_cache",
    "client",
    "custom_app_env",
    "database_url",
    "database_url_base",
    "db_engine",
    "development_env",
    "ensure_postgres_container",
    "no_docs_env",
    "production_env",
    "setup_worker_database",
    "staging_env",
    "worker_database_name",
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


@pytest.fixture(autouse=True)
def clean_request_context() -> Generator[None]:
    """Automatically clear RequestContext before and after each test.

    This ensures that each test starts with a clean RequestContext
    and prevents correlation IDs or other context data from leaking
    between tests. This is especially important with pytest-randomly
    which runs tests in random order.
    """
    # Clear before test
    RequestContext.clear()

    yield

    # Clear after test
    RequestContext.clear()


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient]:
    """Create test client for FastAPI app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
