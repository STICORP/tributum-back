"""Integration tests for docker-compose.test.yml that verify actual functionality.

These tests verify that Docker Compose can:
1. Start PostgreSQL containers successfully
2. Create and configure databases correctly
3. Allow connections to both main and test databases

The tests use the ensure_postgres_container fixture for proper container lifecycle
management and are designed to work with the project's parallel testing setup.
"""

import os
import subprocess  # nosec B404 - Required for Docker commands
import time
from pathlib import Path

import pytest


def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent.parent


def get_docker_command() -> str:
    """Get the docker command path.

    Returns:
        str: Path to docker executable.
    """
    # Try to find docker in PATH first, fallback to common locations
    docker_cmd = "docker"
    for path in ["/usr/bin/docker", "/usr/local/bin/docker"]:
        if Path(path).exists():
            docker_cmd = path
            break
    return docker_cmd


def get_docker_compose_command() -> list[str]:
    """Get the base docker-compose command.

    Returns:
        list[str]: Docker compose command with test configuration file.
    """
    project_root = get_project_root()
    compose_file = project_root / "docker-compose.test.yml"
    docker_cmd = get_docker_command()
    return [docker_cmd, "compose", "-f", str(compose_file)]


# Note: The ensure_postgres_container fixture handles container lifecycle.
# We import it above to ensure it's available for tests that need it.


def is_docker_available() -> bool:
    """Check if Docker is available and accessible.

    Returns:
        bool: True if Docker is available and working, False otherwise.

    Note:
        Returns False in CI environments to avoid Docker-in-Docker complexity.
    """
    if os.environ.get("CI") == "true":
        return False

    docker_cmd = get_docker_command()
    result = subprocess.run(
        [docker_cmd, "version"],
        capture_output=True,
        check=False,
        timeout=10,  # Don't hang indefinitely
    )
    return result.returncode == 0


@pytest.mark.integration
@pytest.mark.skipif(
    not is_docker_available(),
    reason="Docker not available or running in CI",
)
class TestDockerComposeIntegration:
    """Integration tests that verify Docker Compose actually works."""

    def test_docker_compose_postgres_starts_and_becomes_healthy(
        self, ensure_postgres_container: None
    ) -> None:
        """Test that PostgreSQL container starts and becomes healthy.

        Args:
            ensure_postgres_container: Fixture that ensures container is running.

        Verifies:
        - Container starts and reaches healthy status
        - Database accepts connections
        - Basic SQL queries work correctly
        """
        # ensure_postgres_container fixture has already started the container
        assert (
            ensure_postgres_container is None
        )  # Fixture returns None but ensures container

        docker_compose_command = get_docker_compose_command()

        # Wait for container to become healthy
        healthy = self._wait_for_container_health(docker_compose_command)
        assert healthy, "Container did not become healthy within 30 seconds"

        # Verify database connectivity
        self._verify_database_connection(docker_compose_command, "postgres")

    def _wait_for_container_health(
        self, docker_compose_command: list[str], max_wait: int = 30
    ) -> bool:
        """Wait for container to become healthy.

        Args:
            docker_compose_command: Docker compose command prefix.
            max_wait: Maximum time to wait in seconds.

        Returns:
            bool: True if container becomes healthy, False if timeout.
        """
        start_time = time.time()

        while time.time() - start_time < max_wait:
            result = subprocess.run(  # nosec B603 - Controlled input
                [*docker_compose_command, "ps", "--format", "json"],
                capture_output=True,
                text=True,
                check=False,
                timeout=5,
            )

            if result.returncode == 0 and "healthy" in result.stdout:
                return True

            time.sleep(1)

        return False

    def _verify_database_connection(
        self, docker_compose_command: list[str], database: str
    ) -> None:
        """Verify database connection with a simple query.

        Args:
            docker_compose_command: Docker compose command prefix.
            database: Database name to connect to.

        Raises:
            AssertionError: If connection fails or query doesn't work.
        """
        result = subprocess.run(  # nosec B603 - Controlled input
            [
                *docker_compose_command,
                "exec",
                "postgres",
                "psql",
                "-U",
                "tributum",
                "-d",
                database,
                "-c",
                "SELECT 1;",
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
        assert result.returncode == 0, f"Failed to connect to database: {result.stderr}"
        assert "(1 row)" in result.stdout, "Query did not return expected result"

    def test_docker_compose_creates_test_database(
        self, ensure_postgres_container: None
    ) -> None:
        """Test that init.sql creates the test database.

        Args:
            ensure_postgres_container: Fixture that ensures container is running.

        Verifies:
        - Both tributum_db and tributum_test databases exist
        - Can connect to test database
        - Database queries work correctly
        """
        # ensure_postgres_container fixture has already started the container
        assert (
            ensure_postgres_container is None
        )  # Fixture returns None but ensures container

        docker_compose_command = get_docker_compose_command()

        # Verify both databases exist
        databases = self._get_database_list(docker_compose_command)
        assert "tributum_db" in databases, "tributum_db database not found"
        assert "tributum_test" in databases, "tributum_test database not found"

        # Verify test database connectivity
        self._verify_test_database_connection(docker_compose_command)

    def _get_database_list(self, docker_compose_command: list[str]) -> list[str]:
        """Get list of user databases from PostgreSQL.

        Args:
            docker_compose_command: Docker compose command prefix.

        Returns:
            list[str]: List of database names.

        Raises:
            AssertionError: If query fails.
        """
        query = (
            "SELECT datname FROM pg_database "
            "WHERE datistemplate = false ORDER BY datname;"
        )
        result = subprocess.run(  # nosec B603 - Controlled input
            [
                *docker_compose_command,
                "exec",
                "postgres",
                "psql",
                "-U",
                "tributum",
                "-d",
                "postgres",
                "-c",
                query,
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )

        assert result.returncode == 0, f"Failed to query databases: {result.stderr}"

        # Parse database names from psql output
        # psql output includes headers and formatting, we need just the database names
        lines = result.stdout.splitlines()
        databases = []
        for raw_line in lines:
            line = raw_line.strip()
            # Skip headers, separators, and summary lines
            if (
                line
                and not line.startswith("-")
                and not line.startswith("datname")
                and not line.endswith("rows)")
                and not line.startswith("(")
            ):
                databases.append(line)
        return databases

    def _verify_test_database_connection(
        self, docker_compose_command: list[str]
    ) -> None:
        """Verify connection to the test database.

        Args:
            docker_compose_command: Docker compose command prefix.

        Raises:
            AssertionError: If connection fails or query doesn't work.
        """
        result = subprocess.run(  # nosec B603 - Controlled input
            [
                *docker_compose_command,
                "exec",
                "postgres",
                "psql",
                "-U",
                "tributum",
                "-d",
                "tributum_test",
                "-c",
                "SELECT current_database();",
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )

        assert result.returncode == 0, (
            f"Failed to connect to test database: {result.stderr}"
        )
        assert "tributum_test" in result.stdout, "Not connected to test database"
