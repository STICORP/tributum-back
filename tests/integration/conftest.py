"""Shared fixtures for integration tests.

This module provides fixtures that are commonly needed across integration tests,
particularly for tests that need to verify configuration-dependent behavior.
"""

from collections.abc import AsyncGenerator, Awaitable, Callable

import pytest
from httpx import ASGITransport, AsyncClient

from src.api.main import create_app
from src.core.config import Settings, get_settings

ClientFactoryType = Callable[[], Awaitable[AsyncClient]]
SettingsClientFactoryType = Callable[[Settings], Awaitable[AsyncClient]]


@pytest.fixture
async def client_factory() -> AsyncGenerator[ClientFactoryType]:
    """Factory fixture for creating test clients with custom app instances.

    This factory is necessary because the main client fixture uses a module-level
    app instance that's created at import time and doesn't respect environment
    changes made by fixtures.

    Usage:
        async def test_something(client_factory, some_env_fixture):
            client = await client_factory()
            # client now has fresh app instance with current environment
    """
    clients = []

    async def _create_client() -> AsyncClient:
        app = create_app()
        transport = ASGITransport(app=app)
        client = AsyncClient(transport=transport, base_url="http://test")
        clients.append(client)
        return client

    yield _create_client

    # Cleanup all created clients
    for client in clients:
        await client.aclose()


@pytest.fixture
async def client_with_settings() -> AsyncGenerator[SettingsClientFactoryType]:
    """Factory fixture for creating test clients with custom settings.

    This allows tests to create app instances with specific settings
    without relying on environment variables.

    Usage:
        async def test_something(client_with_settings):
            settings = Settings(app_name="Test", debug=False)
            client = await client_with_settings(settings)
    """
    clients = []

    async def _create_client(settings: Settings) -> AsyncClient:
        app = create_app(settings)
        # Override the settings dependency
        app.dependency_overrides[get_settings] = lambda: settings

        transport = ASGITransport(app=app)
        client = AsyncClient(transport=transport, base_url="http://test")
        clients.append(client)
        return client

    yield _create_client

    # Cleanup all created clients
    for client in clients:
        await client.aclose()


# Specific pre-configured clients for common test scenarios
@pytest.fixture
async def client_no_docs(no_docs_env: None) -> AsyncGenerator[AsyncClient]:
    """Create a test client with documentation endpoints disabled.

    This fixture ensures the no_docs_env fixture runs first, then creates
    a fresh app instance that respects the environment settings.
    """
    _ = no_docs_env  # Ensure fixture runs first
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def client_production(production_env: None) -> AsyncGenerator[AsyncClient]:
    """Create a test client with production environment settings."""
    _ = production_env  # Ensure fixture runs first
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
