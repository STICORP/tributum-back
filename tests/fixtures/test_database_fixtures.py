"""Database fixtures for parallel test execution.

This module provides fixtures that create isolated databases for each test worker,
enabling true parallel test execution against a single PostgreSQL container.
"""

import asyncio
import logging
import os
from collections.abc import AsyncGenerator, Generator
from pathlib import Path

import asyncpg
import pytest
from alembic import command as alembic_command
from alembic.config import Config
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from src.core.config import get_settings

logger = logging.getLogger(__name__)


async def run_migrations_on_database(database_url: str) -> None:
    """Run Alembic migrations on the specified database.

    Args:
        database_url: The database URL to run migrations on
    """
    # Find the alembic.ini file
    project_root = Path(__file__).parent.parent.parent
    alembic_ini_path = project_root / "alembic.ini"

    if not alembic_ini_path.exists():
        msg = f"alembic.ini not found at {alembic_ini_path}"
        raise FileNotFoundError(msg)

    # Create Alembic configuration
    alembic_cfg = Config(str(alembic_ini_path))

    # Override the database URL in the environment
    # This is necessary because our env.py reads from get_settings()
    # We need to temporarily override the DATABASE_CONFIG__DATABASE_URL
    original_db_url = os.environ.get("DATABASE_CONFIG__DATABASE_URL")
    try:
        os.environ["DATABASE_CONFIG__DATABASE_URL"] = database_url

        # Run migrations up to head
        # We need to run this in a thread because Alembic's command.upgrade
        # expects to manage its own event loop
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, alembic_command.upgrade, alembic_cfg, "head")

        logger.info("Migrations completed successfully on %s", database_url)
    finally:
        # Restore original environment variable
        if original_db_url is not None:
            os.environ["DATABASE_CONFIG__DATABASE_URL"] = original_db_url
        else:
            os.environ.pop("DATABASE_CONFIG__DATABASE_URL", None)


@pytest.fixture(scope="session")
def database_url_base() -> str:
    """Get the base database URL without a specific database name."""
    # Get database URL from settings (which uses DATABASE_CONFIG__DATABASE_URL)
    # The settings will automatically use the test database URL in test environment
    url = get_settings().database_config.database_url

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
    """Create a database for the current test worker and run migrations.

    This fixture:
    1. Connects to PostgreSQL using the tributum_test database
    2. Creates a new database for this worker
    3. Runs Alembic migrations to set up the schema
    4. Yields the database URL
    5. Drops the database after tests complete
    """
    # Connect to the test database to create our worker-specific test databases
    # The tributum user has CREATE DATABASE permissions
    # This keeps all test operations isolated from the main database
    # asyncpg expects postgresql:// not postgresql+asyncpg://
    admin_url = f"{database_url_base}/tributum_test".replace(
        "postgresql+asyncpg://", "postgresql://"
    )

    # Create the database
    logger.info("Creating test database: %s", worker_database_name)
    conn = await asyncpg.connect(admin_url)
    try:
        # Drop if exists and create fresh
        await conn.execute(f"DROP DATABASE IF EXISTS {worker_database_name}")
        await conn.execute(f"CREATE DATABASE {worker_database_name}")
    finally:
        await conn.close()

    # Yield the database URL for this worker
    database_url = f"{database_url_base}/{worker_database_name}"

    # Run migrations on the new database
    logger.info("Running migrations on database: %s", worker_database_name)
    await run_migrations_on_database(database_url)

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
