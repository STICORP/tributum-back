"""Unit tests for DatabaseConfig class."""

import pytest
from pydantic import ValidationError

from src.core.config import DatabaseConfig


@pytest.mark.unit
class TestDatabaseConfig:
    """Test cases for DatabaseConfig class."""

    def test_default_values(self) -> None:
        """Test default values for DatabaseConfig."""
        config = DatabaseConfig()
        assert (
            config.database_url
            == "postgresql+asyncpg://tributum:tributum_pass@localhost:5432/tributum_db"
        )
        assert config.pool_size == 10
        assert config.max_overflow == 5
        assert config.pool_timeout == 30.0
        assert config.pool_pre_ping is True
        assert config.echo is False

    def test_custom_values(self) -> None:
        """Test custom values for DatabaseConfig."""
        config = DatabaseConfig(
            database_url="postgresql+asyncpg://user:pass@host:5433/mydb",
            pool_size=20,
            max_overflow=10,
            pool_timeout=60.0,
            pool_pre_ping=False,
            echo=True,
        )
        assert config.database_url == "postgresql+asyncpg://user:pass@host:5433/mydb"
        assert config.pool_size == 20
        assert config.max_overflow == 10
        assert config.pool_timeout == 60.0
        assert config.pool_pre_ping is False
        assert config.echo is True

    def test_pool_size_validation(self) -> None:
        """Test pool_size validation."""
        # Valid sizes
        DatabaseConfig(pool_size=1)
        DatabaseConfig(pool_size=50)
        DatabaseConfig(pool_size=100)

        # Invalid sizes
        with pytest.raises(ValidationError, match="greater than or equal to 1"):
            DatabaseConfig(pool_size=0)

        with pytest.raises(ValidationError, match="less than or equal to 100"):
            DatabaseConfig(pool_size=101)

    def test_max_overflow_validation(self) -> None:
        """Test max_overflow validation."""
        # Valid values
        DatabaseConfig(max_overflow=0)
        DatabaseConfig(max_overflow=25)
        DatabaseConfig(max_overflow=50)

        # Invalid values
        with pytest.raises(ValidationError, match="greater than or equal to 0"):
            DatabaseConfig(max_overflow=-1)

        with pytest.raises(ValidationError, match="less than or equal to 50"):
            DatabaseConfig(max_overflow=51)

    def test_pool_timeout_validation(self) -> None:
        """Test pool_timeout validation."""
        # Valid values
        DatabaseConfig(pool_timeout=0.1)
        DatabaseConfig(pool_timeout=150.0)
        DatabaseConfig(pool_timeout=300.0)

        # Invalid values
        with pytest.raises(ValidationError, match="greater than 0"):
            DatabaseConfig(pool_timeout=0.0)

        with pytest.raises(ValidationError, match="less than or equal to 300"):
            DatabaseConfig(pool_timeout=301.0)

    def test_database_url_validation(self) -> None:
        """Test database URL validation for async driver."""
        # Valid URL with correct driver
        config = DatabaseConfig(
            database_url="postgresql+asyncpg://user:pass@host:5432/mydb"
        )
        assert config.database_url == "postgresql+asyncpg://user:pass@host:5432/mydb"

        # Invalid URL with wrong driver
        expected_msg = (
            "Database URL must use postgresql\\+asyncpg:// driver for async support"
        )
        with pytest.raises(ValidationError, match=expected_msg):
            DatabaseConfig(database_url="postgresql://user:pass@host:5432/mydb")

        # Invalid URL with psycopg2 driver
        with pytest.raises(ValidationError, match=expected_msg):
            DatabaseConfig(
                database_url="postgresql+psycopg2://user:pass@host:5432/mydb"
            )

    def test_get_test_database_url(self) -> None:
        """Test get_test_database_url method."""
        # Default database
        config = DatabaseConfig()
        assert (
            config.get_test_database_url()
            == "postgresql+asyncpg://tributum:tributum_pass@localhost:5432/tributum_test"
        )

        # Custom database name
        config = DatabaseConfig(
            database_url="postgresql+asyncpg://user:pass@host:5432/myapp"
        )
        assert (
            config.get_test_database_url()
            == "postgresql+asyncpg://user:pass@host:5432/myapp_test"
        )

        # With query parameters
        config = DatabaseConfig(
            database_url="postgresql+asyncpg://user:pass@host:5432/myapp?sslmode=require"
        )
        assert (
            config.get_test_database_url()
            == "postgresql+asyncpg://user:pass@host:5432/myapp_test?sslmode=require"
        )

        # Already has _test suffix (edge case)
        config = DatabaseConfig(
            database_url="postgresql+asyncpg://user:pass@host:5432/tributum_test"
        )
        assert (
            config.get_test_database_url()
            == "postgresql+asyncpg://user:pass@host:5432/tributum_test_test"
        )

        # URL without database name
        config = DatabaseConfig(database_url="postgresql+asyncpg://localhost")
        assert config.get_test_database_url() == "postgresql+asyncpg://localhost_test"

        # URL with empty database name
        config = DatabaseConfig(database_url="postgresql+asyncpg://host:5432/")
        assert config.get_test_database_url() == "postgresql+asyncpg://host:5432/_test"

        # URL with multiple path parts
        config = DatabaseConfig(database_url="postgresql+asyncpg://host/path/to/db")
        assert (
            config.get_test_database_url()
            == "postgresql+asyncpg://host/path/to/db_test"
        )

        # Test edge case for line 119 by setting URL directly (bypassing validation)
        config = DatabaseConfig()
        config.database_url = "postgresql+asyncpg:no-slash"  # No "/" in URL
        assert config.get_test_database_url() == "postgresql+asyncpg:no-slash"
