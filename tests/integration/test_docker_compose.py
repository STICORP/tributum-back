"""Integration tests for docker-compose.test.yml that verify actual functionality."""

import os
import subprocess  # nosec B404 - Required for Docker commands
import time
from collections.abc import Generator
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
    def docker_compose_command(self, project_root: Path, worker_id: str) -> list[str]:
        """Get the base docker-compose command with unique project name per worker."""
        # Use parallel-safe compose file when running with xdist workers
        if worker_id != "master":
            compose_file = project_root / "docker-compose.test-parallel.yml"
            project_name = f"tributum-test-{worker_id}"
        else:
            compose_file = project_root / "docker-compose.test.yml"
            project_name = "tributum-test"

        # Try to find docker in PATH first, fallback to common locations
        docker_cmd = "docker"
        for path in ["/usr/bin/docker", "/usr/local/bin/docker"]:
            if Path(path).exists():
                docker_cmd = path
                break

        return [docker_cmd, "compose", "-f", str(compose_file), "-p", project_name]

    @pytest.fixture
    def ensure_container_stopped(
        self, docker_compose_command: list[str]
    ) -> Generator[None]:
        """Ensure container is stopped before and after test."""
        # Stop any existing container before test
        subprocess.run(  # nosec B603 - Controlled input from fixture
            [*docker_compose_command, "down", "-v"],
            capture_output=True,
            check=False,
        )

        yield

        # Stop container after test
        subprocess.run(  # nosec B603 - Controlled input from fixture
            [*docker_compose_command, "down", "-v"],
            capture_output=True,
            check=False,
        )

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
        ensure_container_stopped: None,  # noqa: ARG002
    ) -> None:
        """Test that PostgreSQL container starts and becomes healthy."""
        # Start the container
        result = subprocess.run(  # nosec B603 - Controlled input
            [*docker_compose_command, "up", "-d"],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, f"Failed to start container: {result.stderr}"

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
        ensure_container_stopped: None,  # noqa: ARG002
    ) -> None:
        """Test that init.sql creates the test database."""
        # Start the container
        result = subprocess.run(  # nosec B603 - Controlled input
            [*docker_compose_command, "up", "-d"],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, f"Failed to start container: {result.stderr}"

        # Wait for container to be ready
        time.sleep(5)

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
