"""Docker fixtures for test execution.

This module provides fixtures that manage the PostgreSQL container lifecycle
for the entire test session.
"""

import os
import subprocess
import time
from collections.abc import Generator
from pathlib import Path

import pytest


@pytest.fixture(scope="session", autouse=True)
def ensure_postgres_container() -> Generator[None]:
    """Ensure PostgreSQL container is running for all tests.

    This session-scoped fixture:
    1. Starts the PostgreSQL container if not running
    2. Waits for it to be healthy
    3. Keeps it running for all tests
    4. Optionally cleans up after tests (configurable)
    """
    project_root = Path(__file__).parent.parent.parent
    compose_file = project_root / "docker-compose.test.yml"

    # Check if we should manage the container
    # This allows developers to manage the container manually if desired
    if not _should_manage_container():
        yield
        return

    # Start the container
    print("\nStarting PostgreSQL container for tests...")
    result = subprocess.run(
        ["docker", "compose", "-f", str(compose_file), "up", "-d"],
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        pytest.fail(f"Failed to start PostgreSQL container: {result.stderr}")

    # Wait for container to be healthy
    if not _wait_for_postgres_health(compose_file):
        # Stop container if it failed to become healthy
        subprocess.run(
            ["docker", "compose", "-f", str(compose_file), "down", "-v"],
            capture_output=True,
            check=False,
        )
        pytest.fail("PostgreSQL container did not become healthy in time")

    print("PostgreSQL container is ready!")

    yield

    # Cleanup is optional - developers might want to keep container running
    if _should_cleanup_container():
        print("\nStopping PostgreSQL container...")
        subprocess.run(
            ["docker", "compose", "-f", str(compose_file), "down", "-v"],
            capture_output=True,
            check=False,
        )


def _should_manage_container() -> bool:
    """Check if we should manage the container lifecycle."""
    # Allow override via environment variable
    return os.environ.get("PYTEST_MANAGE_CONTAINER", "true").lower() == "true"


def _should_cleanup_container() -> bool:
    """Check if we should cleanup the container after tests."""
    # By default, keep container running for faster subsequent test runs
    return os.environ.get("PYTEST_CLEANUP_CONTAINER", "false").lower() == "true"


def _wait_for_postgres_health(compose_file: Path, timeout: int = 30) -> bool:
    """Wait for PostgreSQL container to become healthy."""
    start_time = time.time()

    while time.time() - start_time < timeout:
        result = subprocess.run(
            ["docker", "compose", "-f", str(compose_file), "ps", "--format", "json"],
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode == 0 and "healthy" in result.stdout:
            return True

        time.sleep(1)

    return False
