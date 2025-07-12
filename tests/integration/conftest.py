"""Shared fixtures for integration tests.

This module provides fixtures that are commonly needed across integration tests,
particularly for tests that need to verify configuration-dependent behavior.
"""

from collections.abc import AsyncGenerator, Awaitable, Callable, Generator

import pytest
from httpx import ASGITransport, AsyncClient
from loguru import logger
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from src.api.main import app, create_app
from src.core.config import Settings, get_settings
from src.core.context import RequestContext
from src.core.logging import _state
from src.infrastructure.database.dependencies import get_db
from src.infrastructure.database.session import _db_manager, close_database

# Import database and docker fixtures for parallel test execution
from tests.integration.fixtures.test_database_fixtures import (
    database_url,
    database_url_base,
    db_engine,
    setup_worker_database,
    worker_database_name,
)
from tests.integration.fixtures.test_docker_fixtures import ensure_postgres_container

# Import environment fixtures to make them available to all tests
from tests.integration.fixtures.test_env_fixtures import (
    aws_formatter_env,
    console_exporter_env,
    console_formatter_env,
    custom_app_env,
    custom_logging_env,
    debug_disabled_env,
    development_env,
    dynamic_config_env,
    empty_docs_env,
    empty_observability_env,
    gcp_exporter_env,
    high_sampling_env,
    json_formatter_env,
    low_sampling_env,
    no_docs_env,
    otlp_exporter_env,
    production_env,
    staging_env,
)

# Re-export fixtures for pytest discovery
__all__ = [
    "aws_formatter_env",
    "clean_request_context",
    "clear_settings_cache",
    "client",
    "client_with_db",
    "console_exporter_env",
    "console_formatter_env",
    "custom_app_env",
    "custom_logging_env",
    "database_url",
    "database_url_base",
    "db_engine",
    "db_session",
    "debug_disabled_env",
    "development_env",
    "dynamic_config_env",
    "empty_docs_env",
    "empty_observability_env",
    "ensure_postgres_container",
    "gcp_exporter_env",
    "high_sampling_env",
    "json_formatter_env",
    "low_sampling_env",
    "no_docs_env",
    "otlp_exporter_env",
    "production_env",
    "setup_worker_database",
    "staging_env",
    "worker_database_name",
]

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


@pytest.fixture(autouse=True)
def reset_logging_and_tracing_state() -> Generator[None]:
    """Automatically reset logging and tracing state before and after each test.

    This ensures that each test can configure logging and tracing independently
    and prevents configuration from leaking between tests. This fixes:
    - Flaky coverage issues where console formatter code is only covered when
    tests run in certain orders
    - OpenTelemetry warnings about "Overriding of current TracerProvider"
    - "Attempting to instrument while already instrumented" errors
    - Log output leaking to stdout during tests
    """
    # Remove all existing logger handlers to ensure clean state
    logger.remove()

    # Clear the settings cache to ensure fresh settings for each test
    # This is crucial because settings determine which formatter is used
    get_settings.cache_clear()

    # CRITICAL: Keep logging marked as configured during tests
    # This prevents app creation from calling setup_logging() and adding stdout handlers
    _state.configured = True

    # Uninstrument OpenTelemetry to prevent "already instrumented" warnings
    try:
        if FastAPIInstrumentor().is_instrumented_by_opentelemetry:
            FastAPIInstrumentor().uninstrument()
    except (AttributeError, RuntimeError) as e:
        # Log at trace level - expected during test setup
        logger.trace(f"FastAPI uninstrumentation skipped: {e}")

    try:
        if SQLAlchemyInstrumentor().is_instrumented_by_opentelemetry:
            SQLAlchemyInstrumentor().uninstrument()
    except (AttributeError, RuntimeError) as e:
        # Log at trace level - expected during test setup
        logger.trace(f"SQLAlchemy uninstrumentation skipped: {e}")

    yield

    # Keep logging state as configured to prevent re-initialization
    _state.configured = True

    # Remove all handlers again to ensure clean state for next test
    logger.remove()

    # Uninstrument again after test to ensure clean state
    try:
        if FastAPIInstrumentor().is_instrumented_by_opentelemetry:
            FastAPIInstrumentor().uninstrument()
    except (AttributeError, RuntimeError) as e:
        # Log at trace level - expected during test cleanup
        logger.trace(f"FastAPI uninstrumentation skipped during cleanup: {e}")

    try:
        if SQLAlchemyInstrumentor().is_instrumented_by_opentelemetry:
            SQLAlchemyInstrumentor().uninstrument()
    except (AttributeError, RuntimeError) as e:
        # Log at trace level - expected during test cleanup
        logger.trace(f"SQLAlchemy uninstrumentation skipped during cleanup: {e}")


@pytest.fixture(autouse=True)
async def clean_database_connections() -> AsyncGenerator[None]:
    """Automatically clean database connections after each test.

    This ensures that database connections are properly closed and
    the database manager is reset between tests. This prevents
    asyncpg event loop issues when tests run in random order.
    """
    yield

    # Only try to close the database if we have a real engine
    if _db_manager._engine is not None:
        # Check if this is a mock object (from unit tests)
        if hasattr(_db_manager._engine, "_mock_name"):
            # It's a mock, just reset without closing
            _db_manager.reset()
        else:
            # It's a real engine, try to close it properly
            try:
                await close_database()
            except (RuntimeError, ConnectionError, OSError) as e:
                # These specific errors are expected during test cleanup:
                # - RuntimeError: Event loop is closed
                # - ConnectionError/OSError: Connection already closed
                # Log them for debugging but don't fail the test
                logger.debug(
                    "Expected error during database cleanup",
                    error_type=type(e).__name__,
                    error_message=str(e),
                )
                # Still reset the manager to clear references
                _db_manager.reset()
    else:
        # No engine to close, just reset
        _db_manager.reset()


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient]:
    """Create test client for FastAPI app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def db_session(db_engine: AsyncEngine) -> AsyncGenerator[AsyncSession]:
    """Provide a database session with automatic transaction rollback.

    This fixture creates a database session that automatically rolls back
    all changes after each test, ensuring test isolation. It uses a
    connection-level transaction that wraps the entire test.

    Important: This fixture rolls back DML operations (INSERT, UPDATE, DELETE)
    but not DDL operations (CREATE TABLE, ALTER TABLE, etc.) when they are
    explicitly committed. For complete DDL isolation, use temporary tables
    or separate test databases.

    The pattern works as follows:
    1. Begin a database transaction at the connection level
    2. Create a session bound to that connection
    3. Yield the session for the test to use
    4. Roll back the transaction after the test completes
    """
    # Start a connection-level transaction
    async with db_engine.connect() as connection:
        # Start a transaction
        transaction = await connection.begin()

        # Configure the session to use our connection with the transaction
        async_session = AsyncSession(
            bind=connection,
            expire_on_commit=False,
        )

        try:
            # Provide the session to the test
            async with async_session:
                yield async_session
        finally:
            # Always rollback, even if the test fails
            await transaction.rollback()


@pytest.fixture
async def client_with_db(
    db_session: AsyncSession,
) -> AsyncGenerator[AsyncClient]:
    """Create a test client with database session injection.

    This fixture provides a test client that uses the transactional
    db_session fixture for all database operations. This ensures that:
    1. All database operations in API endpoints use the test transaction
    2. Changes are automatically rolled back after each test
    3. Tests remain isolated from each other

    The fixture overrides the default get_db dependency to use our
    transactional session instead of creating new sessions.
    """
    # Create a new app instance for this test
    test_app = create_app()

    # Override the database dependency to use our transactional session
    async def override_get_db() -> AsyncGenerator[AsyncSession]:
        """Override database dependency to use the test session."""
        yield db_session

    test_app.dependency_overrides[get_db] = override_get_db

    # Create the test client
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    # Clear the dependency override
    test_app.dependency_overrides.clear()
