"""Unit tests for configuration management."""

import pytest
import pytest_check
from pydantic import ValidationError

from src.core.config import (
    DatabaseConfig,
    LogConfig,
    ObservabilityConfig,
    Settings,
    get_settings,
)


@pytest.mark.unit
class TestLogConfig:
    """Test cases for LogConfig class."""

    def test_default_values(self) -> None:
        """Test default values for LogConfig."""
        config = LogConfig()
        assert config.log_level == "INFO"
        assert config.log_format == "console"
        assert config.render_json_logs is False
        assert config.add_timestamp is True
        assert config.timestamper_format == "iso"

    def test_custom_values(self) -> None:
        """Test custom values for LogConfig."""
        config = LogConfig(
            log_level="DEBUG",
            log_format="json",
            render_json_logs=True,
            add_timestamp=False,
            timestamper_format="unix",
        )
        assert config.log_level == "DEBUG"
        assert config.log_format == "json"
        assert config.render_json_logs is True
        assert config.add_timestamp is False
        assert config.timestamper_format == "unix"


@pytest.mark.unit
class TestObservabilityConfig:
    """Test cases for ObservabilityConfig class."""

    def test_default_values(self) -> None:
        """Test default values for ObservabilityConfig."""
        config = ObservabilityConfig()
        assert config.enable_tracing is False
        assert config.service_name == "tributum"
        assert config.gcp_project_id is None
        assert config.trace_sample_rate == 1.0

    def test_custom_values(self) -> None:
        """Test custom values for ObservabilityConfig."""
        config = ObservabilityConfig(
            enable_tracing=True,
            service_name="test-service",
            gcp_project_id="test-project-123",
            trace_sample_rate=0.5,
        )
        assert config.enable_tracing is True
        assert config.service_name == "test-service"
        assert config.gcp_project_id == "test-project-123"
        assert config.trace_sample_rate == 0.5

    def test_trace_sample_rate_validation(self) -> None:
        """Test trace_sample_rate validation."""
        # Valid rates
        ObservabilityConfig(trace_sample_rate=0.0)
        ObservabilityConfig(trace_sample_rate=0.5)
        ObservabilityConfig(trace_sample_rate=1.0)

        # Invalid rates
        with pytest.raises(ValidationError, match="greater than or equal to 0"):
            ObservabilityConfig(trace_sample_rate=-0.1)

        with pytest.raises(ValidationError, match="less than or equal to 1"):
            ObservabilityConfig(trace_sample_rate=1.1)


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


@pytest.mark.unit
class TestSettings:
    """Test cases for Settings class."""

    def test_default_application_settings(self) -> None:
        """Test default application settings."""
        settings = Settings()

        # Application settings
        with pytest_check.check:
            assert settings.app_name == "Tributum"
        with pytest_check.check:
            assert settings.app_version  # Just check it exists and is not empty
        with pytest_check.check:
            assert settings.environment == "development"  # pytest-env sets this
        with pytest_check.check:
            assert settings.debug is True

        # API settings
        with pytest_check.check:
            assert settings.api_host == "127.0.0.1"
        with pytest_check.check:
            assert settings.api_port == 8000
        with pytest_check.check:
            assert settings.docs_url == "/docs"
        with pytest_check.check:
            assert settings.redoc_url == "/redoc"
        with pytest_check.check:
            assert settings.openapi_url == "/openapi.json"

    def test_default_log_config(self) -> None:
        """Test default logging configuration."""
        settings = Settings()

        # Logging (with pytest-env overrides)
        with pytest_check.check:
            assert isinstance(settings.log_config, LogConfig)
        with pytest_check.check:
            assert settings.log_config.log_level == "WARNING"  # Set by pytest-env
        with pytest_check.check:
            assert settings.log_config.log_format == "console"
        with pytest_check.check:
            assert settings.log_config.render_json_logs is False
        with pytest_check.check:
            assert settings.log_config.add_timestamp is False  # Set by pytest-env
        with pytest_check.check:
            assert settings.log_config.timestamper_format == "iso"

    def test_default_observability_config(self) -> None:
        """Test default observability configuration."""
        settings = Settings()

        # Observability
        with pytest_check.check:
            assert isinstance(settings.observability_config, ObservabilityConfig)
        with pytest_check.check:
            assert settings.observability_config.enable_tracing is False
        with pytest_check.check:
            assert settings.observability_config.service_name == "tributum"
        with pytest_check.check:
            assert settings.observability_config.gcp_project_id is None
        with pytest_check.check:
            assert settings.observability_config.trace_sample_rate == 1.0

    def test_default_database_config(self) -> None:
        """Test default database configuration."""
        settings = Settings()

        # Database
        with pytest_check.check:
            assert isinstance(settings.database_config, DatabaseConfig)
        with pytest_check.check:
            assert (
                settings.database_config.database_url
                == "postgresql+asyncpg://tributum:tributum_pass@localhost:5432/tributum_db"
            )
        with pytest_check.check:
            assert settings.database_config.pool_size == 10
        with pytest_check.check:
            assert settings.database_config.max_overflow == 5
        with pytest_check.check:
            assert settings.database_config.pool_timeout == 30.0
        with pytest_check.check:
            assert settings.database_config.pool_pre_ping is True
        with pytest_check.check:
            assert settings.database_config.echo is False

    def test_application_env_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test application environment variable overrides."""
        monkeypatch.setenv("APP_NAME", "Test App")
        monkeypatch.setenv("APP_VERSION", "2.0.0")
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("DEBUG", "false")
        monkeypatch.setenv("API_PORT", "9000")

        settings = Settings()

        with pytest_check.check:
            assert settings.app_name == "Test App"
        with pytest_check.check:
            assert settings.app_version == "2.0.0"
        with pytest_check.check:
            assert settings.environment == "production"
        with pytest_check.check:
            assert settings.debug is False
        with pytest_check.check:
            assert settings.api_port == 9000

    def test_log_config_env_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test log configuration environment variable overrides."""
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("LOG_CONFIG__LOG_LEVEL", "DEBUG")
        monkeypatch.setenv("LOG_CONFIG__LOG_FORMAT", "json")

        settings = Settings()

        with pytest_check.check:
            assert settings.log_config.log_level == "DEBUG"
        # In production, console format should be overridden to json
        with pytest_check.check:
            assert settings.log_config.log_format == "json"
        with pytest_check.check:
            assert settings.log_config.render_json_logs is True

    def test_observability_env_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test observability configuration environment variable overrides."""
        monkeypatch.setenv("OBSERVABILITY_CONFIG__ENABLE_TRACING", "true")
        monkeypatch.setenv("OBSERVABILITY_CONFIG__SERVICE_NAME", "test-service")
        monkeypatch.setenv("OBSERVABILITY_CONFIG__GCP_PROJECT_ID", "my-project")
        monkeypatch.setenv("OBSERVABILITY_CONFIG__TRACE_SAMPLE_RATE", "0.75")

        settings = Settings()

        with pytest_check.check:
            assert settings.observability_config.enable_tracing is True
        with pytest_check.check:
            assert settings.observability_config.service_name == "test-service"
        with pytest_check.check:
            assert settings.observability_config.gcp_project_id == "my-project"
        with pytest_check.check:
            assert settings.observability_config.trace_sample_rate == 0.75

    def test_database_env_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test database configuration environment variable overrides."""
        monkeypatch.setenv(
            "DATABASE_CONFIG__DATABASE_URL",
            "postgresql+asyncpg://test:test@dbhost:5433/testdb",
        )
        monkeypatch.setenv("DATABASE_CONFIG__POOL_SIZE", "20")
        monkeypatch.setenv("DATABASE_CONFIG__MAX_OVERFLOW", "10")
        monkeypatch.setenv("DATABASE_CONFIG__POOL_TIMEOUT", "60.0")
        monkeypatch.setenv("DATABASE_CONFIG__POOL_PRE_PING", "false")
        monkeypatch.setenv("DATABASE_CONFIG__ECHO", "true")

        settings = Settings()

        with pytest_check.check:
            assert (
                settings.database_config.database_url
                == "postgresql+asyncpg://test:test@dbhost:5433/testdb"
            )
        with pytest_check.check:
            assert settings.database_config.pool_size == 20
        with pytest_check.check:
            assert settings.database_config.max_overflow == 10
        with pytest_check.check:
            assert settings.database_config.pool_timeout == 60.0
        with pytest_check.check:
            assert settings.database_config.pool_pre_ping is False
        with pytest_check.check:
            assert settings.database_config.echo is True

    def test_case_insensitive_env_vars(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that environment variables are case-insensitive."""
        monkeypatch.setenv("app_name", "Lower Case App")
        monkeypatch.setenv("API_HOST", "127.0.0.1")

        settings = Settings()

        assert settings.app_name == "Lower Case App"
        assert settings.api_host == "127.0.0.1"

    def test_invalid_environment_value(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that invalid environment values raise validation errors."""
        monkeypatch.setenv("ENVIRONMENT", "invalid_env")

        with pytest.raises(
            ValidationError,
            match="Input should be 'development', 'staging' or 'production'",
        ):
            Settings()

    def test_invalid_log_level(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that invalid log levels raise validation errors."""
        monkeypatch.setenv("LOG_CONFIG__LOG_LEVEL", "INVALID")

        with pytest.raises(
            ValidationError,
            match=("Input should be 'DEBUG', 'INFO', 'WARNING', 'ERROR' or 'CRITICAL'"),
        ):
            Settings()

    def test_nullable_doc_urls(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that documentation URLs can be set to None."""
        monkeypatch.setenv("DOCS_URL", "")
        monkeypatch.setenv("REDOC_URL", "")
        monkeypatch.setenv("OPENAPI_URL", "")

        settings = Settings()

        assert settings.docs_url is None
        assert settings.redoc_url is None
        assert settings.openapi_url is None

    def test_production_environment_json_logs(self, production_env: None) -> None:
        """Test that production environment automatically sets JSON logs.

        Uses the production_env fixture to set up production environment.
        """
        _ = production_env  # Fixture sets up environment
        settings = Settings()
        assert settings.environment == "production"
        assert settings.log_config.log_format == "json"
        assert settings.log_config.render_json_logs is True

    def test_development_environment_console_logs(self, development_env: None) -> None:
        """Test that development environment keeps console logs.

        Uses the development_env fixture to set up development environment.
        """
        _ = development_env  # Fixture sets up environment
        settings = Settings()
        assert settings.environment == "development"
        assert settings.log_config.log_format == "console"
        assert settings.log_config.render_json_logs is False

    def test_invalid_trace_sample_rate(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that invalid trace sample rate raises validation errors."""
        # Test rate too low
        monkeypatch.setenv("OBSERVABILITY_CONFIG__TRACE_SAMPLE_RATE", "-0.5")
        with pytest.raises(ValidationError, match="greater than or equal to 0"):
            Settings()

        # Clear and test rate too high
        monkeypatch.setenv("OBSERVABILITY_CONFIG__TRACE_SAMPLE_RATE", "1.5")
        with pytest.raises(ValidationError, match="less than or equal to 1"):
            Settings()

    def test_invalid_database_config(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that invalid database configuration values raise validation errors."""
        # Test invalid pool_size
        monkeypatch.setenv("DATABASE_CONFIG__POOL_SIZE", "0")
        with pytest.raises(ValidationError, match="greater than or equal to 1"):
            Settings()

        # Test invalid max_overflow
        monkeypatch.setenv("DATABASE_CONFIG__POOL_SIZE", "10")  # Reset to valid
        monkeypatch.setenv("DATABASE_CONFIG__MAX_OVERFLOW", "-1")
        with pytest.raises(ValidationError, match="greater than or equal to 0"):
            Settings()

        # Test invalid pool_timeout
        monkeypatch.setenv("DATABASE_CONFIG__MAX_OVERFLOW", "5")  # Reset to valid
        monkeypatch.setenv("DATABASE_CONFIG__POOL_TIMEOUT", "0")
        with pytest.raises(ValidationError, match="greater than 0"):
            Settings()


@pytest.mark.unit
class TestGetSettings:
    """Test cases for get_settings function."""

    def test_get_settings_caching(self) -> None:
        """Test that get_settings returns the same instance (cached).

        Note: The clear_settings_cache fixture automatically clears cache
        before and after each test, so we test caching within a single test.
        """
        settings1 = get_settings()
        settings2 = get_settings()

        assert settings1 is settings2

    def test_get_settings_cache_clear(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that cache can be cleared to get new settings.

        The clear_settings_cache fixture handles automatic clearing,
        but we test manual clearing within a test.
        """
        # Get initial settings
        settings1 = get_settings()
        initial_name = settings1.app_name

        # Clear the cache manually
        get_settings.cache_clear()

        # Modify environment and get new settings
        monkeypatch.setenv("APP_NAME", "Modified App")
        settings2 = get_settings()

        assert settings1 is not settings2
        assert settings2.app_name == "Modified App"
        assert initial_name == "Tributum"  # Verify initial was default
