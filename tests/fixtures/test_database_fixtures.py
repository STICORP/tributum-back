"""Database fixtures for parallel test execution.

This module provides fixtures that create isolated databases for each test worker,
enabling true parallel test execution against a single PostgreSQL container.
"""

import asyncio
import os
from collections.abc import AsyncGenerator, Generator

import asyncpg
import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from src.core.config import get_settings


@pytest.fixture(scope="session")
def database_url_base() -> str:
    """Get the base database URL without a specific database name."""
    # First try to get TEST_DATABASE_URL from environment
    # Then fall back to DATABASE_URL or use configured value
    url = (
        os.environ.get("TEST_DATABASE_URL")
        or os.environ.get("DATABASE_URL")
        or get_settings().database_config.database_url
    )

    # Remove the database name to get base URL
    return url.rsplit("/", 1)[0]


@pytest.fixture(scope="session")
def worker_database_name(worker_id: str) -> str:
    """Generate a unique database name for each test worker."""
    if worker_id == "master":
        # When not using pytest-xdist, create a different database
        # to avoid trying to drop the admin database
        return "tributum_test_main"
    return f"tributum_test_{worker_id}"


@pytest.fixture(scope="session")
async def setup_worker_database(
    database_url_base: str, worker_database_name: str
) -> AsyncGenerator[str]:
    """Create a database for the current test worker.

    This fixture:
    1. Connects to PostgreSQL using the tributum_test database
    2. Creates a new database for this worker
    3. Yields the database URL
    4. Drops the database after tests complete
    """
    # Connect to the test database to create our worker-specific test databases
    # The tributum user has CREATE DATABASE permissions
    # This keeps all test operations isolated from the main database
    # asyncpg expects postgresql:// not postgresql+asyncpg://
    admin_url = f"{database_url_base}/tributum_test".replace(
        "postgresql+asyncpg://", "postgresql://"
    )

    # Create the database
    conn = await asyncpg.connect(admin_url)
    try:
        # Drop if exists and create fresh
        await conn.execute(f"DROP DATABASE IF EXISTS {worker_database_name}")
        await conn.execute(f"CREATE DATABASE {worker_database_name}")
    finally:
        await conn.close()

    # Yield the database URL for this worker
    database_url = f"{database_url_base}/{worker_database_name}"
    yield database_url

    # Cleanup: drop the database
    admin_url_clean = admin_url.replace("postgresql+asyncpg://", "postgresql://")
    conn = await asyncpg.connect(admin_url_clean)
    try:
        # Terminate any connections to the database
        # Use parameterized query to avoid SQL injection
        await conn.execute(
            "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
            "WHERE datname = $1 AND pid <> pg_backend_pid()",
            worker_database_name,
        )
        await conn.execute("DROP DATABASE IF EXISTS " + worker_database_name)
    finally:
        await conn.close()


@pytest.fixture
async def database_url(setup_worker_database: str) -> str:
    """Get the database URL for the current worker."""
    return setup_worker_database


@pytest.fixture
async def db_engine(database_url: str) -> AsyncGenerator[AsyncEngine]:
    """Create an async SQLAlchemy engine for the test database."""
    engine = create_async_engine(
        database_url,
        echo=False,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=0,
    )

    yield engine

    # Cleanup
    await engine.dispose()


@pytest.fixture(scope="session")
def event_loop_policy() -> asyncio.AbstractEventLoopPolicy:
    """Use the async loop policy for the session."""
    return asyncio.get_event_loop_policy()


@pytest.fixture(scope="session")
def event_loop(
    event_loop_policy: asyncio.AbstractEventLoopPolicy,
) -> Generator[asyncio.AbstractEventLoop]:
    """Create an event loop for the test session."""
    loop = event_loop_policy.new_event_loop()
    yield loop
    loop.close()
