"""Tests for docker-compose.test.yml configuration."""

from pathlib import Path
from typing import Any

import pytest
import pytest_check
import yaml


@pytest.mark.unit
class TestDockerComposeConfig:
    """Test docker-compose.test.yml configuration."""

    @pytest.fixture
    def project_root(self) -> Path:
        """Get the project root directory."""
        # Go up from tests/unit to project root
        return Path(__file__).parent.parent.parent

    @pytest.fixture
    def docker_compose_path(self, project_root: Path) -> Path:
        """Get the docker-compose.test.yml path."""
        return project_root / "docker-compose.test.yml"

    @pytest.fixture
    def docker_compose_config(self, docker_compose_path: Path) -> dict[str, Any]:
        """Load and parse the docker-compose.test.yml file."""
        with docker_compose_path.open() as f:
            result = yaml.safe_load(f)
            assert isinstance(result, dict)
            return result

    def test_docker_compose_file_exists(self, docker_compose_path: Path) -> None:
        """Test that docker-compose.test.yml exists."""
        assert docker_compose_path.exists(), "docker-compose.test.yml should exist"
        assert docker_compose_path.is_file(), "docker-compose.test.yml should be a file"

    def test_docker_compose_postgres_service_configuration(
        self, docker_compose_config: dict[str, Any]
    ) -> None:
        """Test that PostgreSQL service is properly configured."""
        assert "services" in docker_compose_config, (
            "docker-compose should have services"
        )
        assert "postgres" in docker_compose_config["services"], (
            "postgres service should be defined"
        )

        postgres_config = docker_compose_config["services"]["postgres"]

        # Check image
        with pytest_check.check:
            assert postgres_config.get("image") == "postgres:17-alpine", (
                "PostgreSQL should use version 17-alpine"
            )

        # Check environment variables
        env = postgres_config.get("environment", {})
        with pytest_check.check:
            assert env.get("POSTGRES_USER") == "tributum", (
                "POSTGRES_USER should be 'tributum'"
            )
        with pytest_check.check:
            assert env.get("POSTGRES_PASSWORD") == "tributum_pass", (
                "POSTGRES_PASSWORD should be 'tributum_pass'"
            )
        with pytest_check.check:
            assert env.get("POSTGRES_DB") == "tributum_db", (
                "POSTGRES_DB should be 'tributum_db'"
            )

        # Check ports
        ports = postgres_config.get("ports", [])
        with pytest_check.check:
            assert "5432:5432" in ports, "PostgreSQL should expose port 5432"

    def test_docker_compose_postgres_volumes(
        self, docker_compose_config: dict[str, Any]
    ) -> None:
        """Test that PostgreSQL volumes are properly configured."""
        postgres_config = docker_compose_config["services"]["postgres"]
        volumes = postgres_config.get("volumes", [])

        assert len(volumes) > 0, "PostgreSQL should have volumes configured"

        # Check init.sql volume
        init_sql_volume = None
        for volume in volumes:
            if "/docker-entrypoint-initdb.d/init.sql" in volume:
                init_sql_volume = volume
                break

        assert init_sql_volume is not None, (
            "init.sql should be mounted to /docker-entrypoint-initdb.d/init.sql"
        )
        assert "./docker/postgres/init.sql:" in init_sql_volume, (
            "init.sql should be mounted from ./docker/postgres/init.sql"
        )

    def test_docker_compose_postgres_healthcheck(
        self, docker_compose_config: dict[str, Any]
    ) -> None:
        """Test that PostgreSQL healthcheck is properly configured."""
        postgres_config = docker_compose_config["services"]["postgres"]
        healthcheck = postgres_config.get("healthcheck", {})

        assert healthcheck, "PostgreSQL should have healthcheck configured"

        # Check healthcheck test command
        test_cmd = healthcheck.get("test", [])
        with pytest_check.check:
            assert "CMD-SHELL" in test_cmd, "Healthcheck should use CMD-SHELL"
        with pytest_check.check:
            assert any("pg_isready" in str(cmd) for cmd in test_cmd), (
                "Healthcheck should use pg_isready"
            )
        with pytest_check.check:
            assert any("-U tributum" in str(cmd) for cmd in test_cmd), (
                "Healthcheck should check with tributum user"
            )
        with pytest_check.check:
            assert any("-d tributum_db" in str(cmd) for cmd in test_cmd), (
                "Healthcheck should check tributum_db database"
            )

        # Check healthcheck timings
        with pytest_check.check:
            assert healthcheck.get("interval") == "2s", (
                "Healthcheck interval should be 2s for fast startup"
            )
        with pytest_check.check:
            assert healthcheck.get("timeout") == "5s", (
                "Healthcheck timeout should be 5s"
            )
        with pytest_check.check:
            assert healthcheck.get("retries") == 15, (
                "Healthcheck should retry 15 times (30s total)"
            )

    def test_docker_compose_follows_best_practices(
        self, docker_compose_config: dict[str, Any]
    ) -> None:
        """Test that docker-compose.test.yml follows best practices."""
        # Should not have 'version' field (deprecated in modern Docker Compose)
        with pytest_check.check:
            assert "version" not in docker_compose_config, (
                "docker-compose.test.yml should not use deprecated 'version' field"
            )

        # Check that only expected services are defined
        services = docker_compose_config.get("services", {})
        with pytest_check.check:
            assert set(services.keys()) == {"postgres"}, (
                "Only postgres service should be defined in test compose file"
            )

        # Ensure no unnecessary configurations
        postgres_config = services.get("postgres", {})
        with pytest_check.check:
            assert "restart" not in postgres_config, (
                "Test containers should not have restart policy"
            )
        with pytest_check.check:
            assert "networks" not in docker_compose_config, (
                "Test compose should use default network"
            )
        with pytest_check.check:
            assert "volumes" not in docker_compose_config, (
                "Test compose should not define named volumes"
            )
