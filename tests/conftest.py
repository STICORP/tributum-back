"""Shared test configuration and fixtures."""

import pathlib
from collections.abc import AsyncGenerator, Generator

import pytest
from httpx import ASGITransport, AsyncClient
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from src.api.main import app, create_app
from src.core.config import get_settings
from src.core.context import RequestContext
from src.infrastructure.database.dependencies import get_db
from src.infrastructure.database.session import _db_manager, close_database

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
    "client_with_db",
    "custom_app_env",
    "database_url",
    "database_url_base",
    "db_engine",
    "db_session",
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


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    """Enforce that all test items have appropriate markers based on their location.

    This hook ensures that:
    - All tests in tests/unit/ have @pytest.mark.unit
    - All tests in tests/integration/ have @pytest.mark.integration
    """
    errors = []

    for item in items:
        # Get the test file path relative to the project root
        test_path = pathlib.Path(item.fspath).relative_to(config.rootpath)
        test_path_str = str(test_path).replace("\\", "/")  # Normalize for Windows

        # Determine expected marker based on path
        expected_marker = None
        if test_path_str.startswith("tests/unit/"):
            expected_marker = "unit"
        elif test_path_str.startswith("tests/integration/"):
            expected_marker = "integration"

        if expected_marker:
            # Check if the test has the expected marker
            has_marker = any(
                marker.name == expected_marker for marker in item.iter_markers()
            )

            if not has_marker:
                # Get the test location for error message
                if hasattr(item, "cls") and item.cls:
                    location = f"{test_path}::{item.cls.__name__}::{item.name}"
                else:
                    location = f"{test_path}::{item.name}"

                errors.append(
                    f"{location} is missing @pytest.mark.{expected_marker} marker"
                )

    if errors:
        # Report all missing markers
        error_message = (
            "\n\nMissing pytest markers found:\n"
            + "\n".join(
                f"  - {error}" for error in sorted(errors)[:10]
            )  # Show first 10
            + (f"\n  ... and {len(errors) - 10} more" if len(errors) > 10 else "")
            + f"\n\nTotal: {len(errors)} missing markers\n"
            + "\nPlease add the appropriate @pytest.mark.unit or "
            + "@pytest.mark.integration decorator to your test classes or functions."
        )
        pytest.exit(error_message, returncode=1)


def _get_test_files(root_path: pathlib.Path) -> list[pathlib.Path]:
    """Get all Python test files to check for mock imports."""
    test_files: list[pathlib.Path] = []
    for test_dir in ["tests/unit", "tests/integration", "tests/fixtures"]:
        test_path = root_path / test_dir
        if test_path.exists():
            test_files.extend(test_path.rglob("*.py"))

    # Also check conftest.py files in test directories
    conftest_files = list(root_path.rglob("conftest.py"))
    test_files.extend([f for f in conftest_files if "tests" in str(f)])
    return test_files


def _check_file_for_mock_imports(
    test_file: pathlib.Path, root_path: pathlib.Path
) -> list[str]:
    """Check a single file for forbidden unittest.mock imports."""
    errors = []
    forbidden_patterns = [
        "import unittest.mock",
        "from unittest import mock",
        "from unittest.mock import",
    ]

    try:
        content = test_file.read_text(encoding="utf-8")
        lines = content.splitlines()
        in_docstring = False
        docstring_delimiter = None

        for line_num, line in enumerate(lines, 1):
            line_stripped = line.strip()

            # Track docstring state
            if '"""' in line_stripped or "'''" in line_stripped:
                if not in_docstring:
                    in_docstring = True
                    docstring_delimiter = '"""' if '"""' in line_stripped else "'''"
                    if line_stripped.count(docstring_delimiter) >= 2:
                        in_docstring = False
                elif docstring_delimiter and docstring_delimiter in line_stripped:
                    in_docstring = False
                    docstring_delimiter = None

            # Skip comments, strings, and content inside docstrings
            if line_stripped.startswith(("#", '"', "'")) or in_docstring:
                continue

            # Check for forbidden patterns
            for pattern in forbidden_patterns:
                if pattern in line_stripped:
                    relative_path = test_file.relative_to(root_path)
                    errors.append(f"{relative_path}:{line_num} uses '{pattern}'")
                    break

    except (OSError, UnicodeDecodeError):
        # Skip files that can't be read
        pass

    return errors


def pytest_sessionstart(session: pytest.Session) -> None:
    """Enforce pytest-mock usage instead of unittest.mock in test files.

    This hook ensures that all test files use pytest-mock instead of unittest.mock.
    Forbidden imports: unittest.mock, from unittest import mock, etc.
    """
    root_path = pathlib.Path(session.config.rootpath)
    test_files = _get_test_files(root_path)

    errors = []
    for test_file in test_files:
        errors.extend(_check_file_for_mock_imports(test_file, root_path))

    if errors:
        # Report all forbidden mock imports
        error_message = (
            "\n\nForbidden unittest.mock imports found:\n"
            + "\n".join(f"  - {error}" for error in sorted(errors)[:10])
            + (f"\n  ... and {len(errors) - 10} more" if len(errors) > 10 else "")
            + f"\n\nTotal: {len(errors)} forbidden imports\n"
            + "\nUse pytest-mock instead:\n"
            + "  def test_something(mocker): mock_obj = mocker.MagicMock()\n"
            + "\nSee: https://pytest-mock.readthedocs.io/"
        )
        pytest.exit(error_message, returncode=1)
