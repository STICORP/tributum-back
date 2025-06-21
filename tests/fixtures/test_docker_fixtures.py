"""Docker fixtures for test execution.

This module provides fixtures that manage the PostgreSQL container lifecycle
for the entire test session.
"""

import json
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

    Note: This fixture is not subject to the global pytest timeout
    as it needs more time to start containers in CI environments.
    """
    project_root = Path(__file__).parent.parent.parent
    compose_file = project_root / "docker-compose.test.yml"

    # Check if we should manage the container
    # This allows developers to manage the container manually if desired
    if not _should_manage_container():
        yield
        return

    # Check if container is already running and healthy
    print("\nChecking PostgreSQL container status...")
    if _is_container_healthy(compose_file):
        print("PostgreSQL container is already running and healthy!")
        yield
        return

    # Container not healthy, try to start it
    print("Starting PostgreSQL container for tests...")

    # Start container (don't force remove if it exists)
    result = subprocess.run(
        ["docker", "compose", "-f", str(compose_file), "up", "-d"],
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        # Only try to clean up if the start failed
        subprocess.run(
            ["docker", "compose", "-f", str(compose_file), "down", "-v"],
            capture_output=True,
            check=False,
        )
        pytest.fail(f"Failed to start PostgreSQL container: {result.stderr}")

    # Wait for container to be healthy
    print("Waiting for PostgreSQL to be ready...")
    if not _wait_for_postgres_health(compose_file):
        # Stop container if it failed to become healthy
        subprocess.run(
            ["docker", "compose", "-f", str(compose_file), "down", "-v"],
            capture_output=True,
            check=False,
        )
        pytest.fail("PostgreSQL container did not become healthy in time (60s timeout)")

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


def _is_container_healthy(compose_file: Path) -> bool:
    """Check if PostgreSQL container is currently healthy.

    Args:
        compose_file: Path to docker-compose file

    Returns:
        True if container is currently healthy, False otherwise
    """
    health_status, _ = _check_container_health(compose_file)
    return health_status


def _wait_for_postgres_health(compose_file: Path, timeout: int = 60) -> bool:
    """Wait for PostgreSQL container to become healthy.

    Args:
        compose_file: Path to docker-compose file
        timeout: Maximum time to wait in seconds (default: 60 for CI compatibility)

    Returns:
        True if container is healthy, False if timeout reached
    """
    start_time = time.time()
    last_error = None

    while time.time() - start_time < timeout:
        health_status, error = _check_container_health(compose_file)

        if health_status:
            return True

        if error:
            last_error = error

        # Print progress every 5 seconds
        elapsed = int(time.time() - start_time)
        if elapsed % 5 == 0 and elapsed > 0:
            print(f"  Still waiting for PostgreSQL... ({elapsed}s elapsed)")

        time.sleep(1)

    # Log the last error if timeout is reached
    if last_error:
        print(f"Last error while checking container health: {last_error}")

    return False


def _check_container_health(compose_file: Path) -> tuple[bool, str | None]:
    """Check the health status of PostgreSQL container.

    Args:
        compose_file: Path to docker-compose file

    Returns:
        Tuple of (is_healthy, error_message)
    """
    try:
        result = subprocess.run(
            [
                "docker",
                "compose",
                "-f",
                str(compose_file),
                "ps",
                "--format",
                "json",
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            return False, result.stderr

        if not result.stdout.strip():
            return False, "No container output"

        # Try JSON parsing first
        return _parse_json_health(result.stdout)
    except (subprocess.SubprocessError, OSError) as e:
        return False, str(e)


def _parse_json_health(output: str) -> tuple[bool, str | None]:
    """Parse JSON output to check container health.

    Args:
        output: JSON output from docker compose ps

    Returns:
        Tuple of (is_healthy, error_message)
    """
    is_healthy = False
    error_msg: str | None = "Container not yet healthy"

    try:
        data = json.loads(output)
        # Handle both single container (dict) and multiple containers (list)
        containers = [data] if isinstance(data, dict) else data

        if not containers:
            error_msg = "No containers found"
        else:
            # Check all containers
            for container in containers:
                health = container.get("Health", "").lower()
                state = container.get("State", "").lower()

                if state == "running" and health == "healthy":
                    is_healthy = True
                    error_msg = None
                    break

                if health == "unhealthy":
                    error_msg = "Container is unhealthy"
                    break

                if state != "running":
                    error_msg = f"Container is {state}"
                    break

    except json.JSONDecodeError:
        # Fallback to string search if JSON parsing fails
        if '"State":"running"' in output and '"Health":"healthy"' in output:
            is_healthy = True
            error_msg = None
        else:
            error_msg = "Unable to parse container status"

    return is_healthy, error_msg
