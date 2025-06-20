"""Tests for Task 6.2a.1: Docker directory structure and configuration files."""

from pathlib import Path

import pytest
import pytest_check


class TestDockerStructure:
    """Test Docker directory structure and configuration files."""

    @pytest.fixture
    def project_root(self) -> Path:
        """Get the project root directory."""
        # Go up from tests/unit to project root
        return Path(__file__).parent.parent.parent

    def test_docker_directory_structure_exists(self, project_root: Path) -> None:
        """Test that Docker directory structure follows best practices."""
        docker_dir = project_root / "docker"
        postgres_dir = docker_dir / "postgres"
        scripts_dir = docker_dir / "scripts"

        with pytest_check.check:
            assert docker_dir.exists(), "docker/ directory should exist"
        with pytest_check.check:
            assert docker_dir.is_dir(), "docker/ should be a directory"
        with pytest_check.check:
            assert postgres_dir.exists(), "docker/postgres/ directory should exist"
        with pytest_check.check:
            assert postgres_dir.is_dir(), "docker/postgres/ should be a directory"
        with pytest_check.check:
            assert scripts_dir.exists(), "docker/scripts/ directory should exist"
        with pytest_check.check:
            assert scripts_dir.is_dir(), "docker/scripts/ should be a directory"

    def test_postgres_init_sql_exists_and_valid(self, project_root: Path) -> None:
        """Test that init.sql creates test database successfully."""
        init_sql_path = project_root / "docker" / "postgres" / "init.sql"

        assert init_sql_path.exists(), "docker/postgres/init.sql should exist"
        assert init_sql_path.is_file(), "init.sql should be a file"

        # Read and validate SQL content
        content = init_sql_path.read_text()

        # Check for required SQL statements
        with pytest_check.check:
            assert "CREATE DATABASE tributum_test" in content, (
                "init.sql should create tributum_test database"
            )
        with pytest_check.check:
            assert "WITH TEMPLATE tributum_db" in content, (
                "test database should be created from tributum_db template"
            )
        with pytest_check.check:
            assert (
                "GRANT ALL PRIVILEGES ON DATABASE tributum_test TO tributum" in content
            ), "tributum user should have privileges on test database"
        with pytest_check.check:
            assert "\\c tributum_test" in content, (
                "init.sql should connect to test database"
            )
        with pytest_check.check:
            assert "GRANT ALL ON SCHEMA public TO tributum" in content, (
                "tributum user should have schema privileges"
            )

        # Basic SQL syntax validation - check for common issues
        with pytest_check.check:
            # Each statement should end with semicolon (except psql commands)
            sql_lines = [
                line.strip()
                for line in content.split("\n")
                if (
                    line.strip()
                    and not line.strip().startswith("--")
                    and not line.strip().startswith("\\")
                )
            ]
            for line in sql_lines:
                assert line.endswith(";"), (
                    f"SQL statement should end with semicolon: {line}"
                )

    def test_dockerignore_exists_and_follows_patterns(self, project_root: Path) -> None:
        """Test that .dockerignore exists and follows gitignore patterns."""
        dockerignore_path = project_root / ".dockerignore"
        gitignore_path = project_root / ".gitignore"

        assert dockerignore_path.exists(), ".dockerignore should exist"
        assert dockerignore_path.is_file(), ".dockerignore should be a file"

        # Read both files
        dockerignore_content = dockerignore_path.read_text()
        _ = gitignore_path.read_text()  # Ensure gitignore exists

        # Check that dockerignore includes key patterns from gitignore
        key_patterns = [
            "__pycache__/",
            "*.py[cod]",
            ".venv",
            ".env",
            "*.log",
            ".pytest_cache/",
            ".coverage",
            "htmlcov/",
        ]

        for pattern in key_patterns:
            with pytest_check.check:
                assert pattern in dockerignore_content, (
                    f".dockerignore should include pattern from .gitignore: {pattern}"
                )

        # Check Docker-specific exclusions
        docker_specific = [
            ".git/",
            ".github/",
            "tests/",
            "Dockerfile*",
            "docker-compose*.yml",
            ".dockerignore",
        ]

        for pattern in docker_specific:
            with pytest_check.check:
                assert pattern in dockerignore_content, (
                    f".dockerignore should include Docker-specific pattern: {pattern}"
                )

        # Ensure .env.example is NOT ignored
        with pytest_check.check:
            assert "!.env.example" in dockerignore_content, (
                ".env.example should be explicitly included in Docker builds"
            )

    def test_env_example_has_all_database_variables(self, project_root: Path) -> None:
        """Test that .env.example documents all database configuration."""
        env_example_path = project_root / ".env.example"

        assert env_example_path.exists(), ".env.example should exist"
        assert env_example_path.is_file(), ".env.example should be a file"

        content = env_example_path.read_text()

        # Check for all required database variables based on DatabaseConfig
        required_vars = [
            "DATABASE_CONFIG__DATABASE_URL",
            "DATABASE_CONFIG__POOL_SIZE",
            "DATABASE_CONFIG__MAX_OVERFLOW",
            "DATABASE_CONFIG__POOL_TIMEOUT",
            "DATABASE_CONFIG__POOL_PRE_PING",
            "DATABASE_CONFIG__ECHO",
            "TEST_DATABASE_URL",  # For pytest
        ]

        for var in required_vars:
            with pytest_check.check:
                assert var in content, f".env.example should include {var}"

        # Check that database URL uses correct driver
        with pytest_check.check:
            assert "postgresql+asyncpg://" in content, (
                "Database URLs should use postgresql+asyncpg:// for async support"
            )

        # Check for reasonable default values
        with pytest_check.check:
            assert (
                "DATABASE_CONFIG__DATABASE_URL="
                "postgresql+asyncpg://tributum:tributum_pass@localhost:5432/tributum_db"
                in content
            ), "DATABASE_CONFIG__DATABASE_URL should have proper default"
        with pytest_check.check:
            assert (
                "TEST_DATABASE_URL="
                "postgresql+asyncpg://tributum:tributum_pass@localhost:5432/tributum_test"
                in content
            ), "TEST_DATABASE_URL should point to test database"

    def test_docker_structure_follows_best_practices(self, project_root: Path) -> None:
        """Test that Docker structure follows best practices."""
        docker_dir = project_root / "docker"

        # Check for clean separation of concerns
        subdirs = [d.name for d in docker_dir.iterdir() if d.is_dir()]

        with pytest_check.check:
            assert "postgres" in subdirs, (
                "postgres/ directory should exist for PostgreSQL-specific files"
            )
        with pytest_check.check:
            assert "scripts" in subdirs, (
                "scripts/ directory should exist for utility scripts"
            )

        # Ensure no unexpected files in docker root
        docker_root_files = [f.name for f in docker_dir.iterdir() if f.is_file()]
        with pytest_check.check:
            assert len(docker_root_files) == 0, (
                f"docker/ root should not contain files, found: {docker_root_files}"
            )
