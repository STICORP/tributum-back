"""Integration tests for docker-compose.test.yml that verify actual functionality."""

import os
import subprocess  # nosec B404 - Required for Docker commands
import time
from pathlib import Path

import pytest


@pytest.mark.integration
class TestDockerComposeIntegration:
    """Integration tests that verify Docker Compose actually works."""

    @pytest.fixture
    def project_root(self) -> Path:
        """Get the project root directory."""
        return Path(__file__).parent.parent.parent

    @pytest.fixture
    def docker_compose_command(self, project_root: Path) -> list[str]:
        """Get the base docker-compose command."""
        compose_file = project_root / "docker-compose.test.yml"
        # Try to find docker in PATH first, fallback to common locations
        docker_cmd = "docker"
        for path in ["/usr/bin/docker", "/usr/local/bin/docker"]:
            if Path(path).exists():
                docker_cmd = path
                break
        return [docker_cmd, "compose", "-f", str(compose_file)]

    @pytest.fixture
    def ensure_container_running(self, docker_compose_command: list[str]) -> None:
        """Ensure container is running for tests.

        Note: With the single container approach, we don't stop/start
        the container for each test. The ensure_postgres_container
        session fixture handles the container lifecycle.
        """
        # Check if container is already running
        result = subprocess.run(  # nosec B603 - Controlled input from fixture
            [*docker_compose_command, "ps", "--format", "json"],
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0 or "healthy" not in result.stdout:
            # Container not running or not healthy, start it
            subprocess.run(  # nosec B603 - Controlled input from fixture
                [*docker_compose_command, "up", "-d"],
                capture_output=True,
                check=False,
            )
            # Wait for health
            time.sleep(5)

    @pytest.mark.skipif(
        os.environ.get("CI") == "true"
        or subprocess.run(
            ["/usr/bin/docker", "version"]
            if Path("/usr/bin/docker").exists()
            else ["docker", "version"],
            capture_output=True,
            check=False,
        ).returncode
        != 0,
        reason="Docker not available or running in CI",
    )
    def test_docker_compose_postgres_starts_and_becomes_healthy(
        self,
        docker_compose_command: list[str],
        ensure_container_running: None,  # noqa: ARG002
    ) -> None:
        """Test that PostgreSQL container starts and becomes healthy."""
        # With single container approach, container should already be running
        # Just verify it's healthy

        # Wait for container to become healthy (max 30 seconds)
        max_wait = 30
        start_time = time.time()
        healthy = False

        while time.time() - start_time < max_wait:
            result = subprocess.run(  # nosec B603 - Controlled input
                [*docker_compose_command, "ps", "--format", "json"],
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode == 0 and "healthy" in result.stdout:
                healthy = True
                break

            time.sleep(1)

        assert healthy, "Container did not become healthy within 30 seconds"

        # Verify we can connect to the database
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
                "SELECT 1;",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, f"Failed to connect to database: {result.stderr}"
        assert "(1 row)" in result.stdout, "Query did not return expected result"

    @pytest.mark.skipif(
        os.environ.get("CI") == "true"
        or subprocess.run(
            ["/usr/bin/docker", "version"]
            if Path("/usr/bin/docker").exists()
            else ["docker", "version"],
            capture_output=True,
            check=False,
        ).returncode
        != 0,
        reason="Docker not available or running in CI",
    )
    def test_docker_compose_creates_test_database(
        self,
        docker_compose_command: list[str],
        ensure_container_running: None,  # noqa: ARG002
    ) -> None:
        """Test that init.sql creates the test database."""
        # With single container approach, container should already be running
        # Just verify the databases exist

        # Check that both databases exist
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
        )

        assert result.returncode == 0, f"Failed to query databases: {result.stderr}"
        assert "tributum_db" in result.stdout, "tributum_db database not found"
        assert "tributum_test" in result.stdout, "tributum_test database not found"

        # Verify we can connect to the test database
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
        )

        assert result.returncode == 0, (
            f"Failed to connect to test database: {result.stderr}"
        )
        assert "tributum_test" in result.stdout, "Not connected to test database"
