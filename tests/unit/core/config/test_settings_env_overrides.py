"""Unit tests for Settings environment variable overrides."""

import pytest
import pytest_check
from pydantic import ValidationError

from src.core.config import Settings


@pytest.mark.unit
class TestSettingsEnvOverrides:
    """Test cases for Settings environment variable overrides."""

    def test_new_log_config_env_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test new log configuration environment variable overrides."""
        monkeypatch.setenv("LOG_CONFIG__SAMPLING_RATE", "0.8")
        monkeypatch.setenv("LOG_CONFIG__ENABLE_ASYNC_LOGGING", "true")
        monkeypatch.setenv("LOG_CONFIG__ASYNC_QUEUE_SIZE", "5000")
        monkeypatch.setenv(
            "LOG_CONFIG__EXCLUDED_PATHS", '["/api/health", "/api/metrics"]'
        )
        monkeypatch.setenv("LOG_CONFIG__SENSITIVE_FIELDS", '["api_key", "token"]')
        monkeypatch.setenv("LOG_CONFIG__ENABLE_SQL_LOGGING", "true")
        monkeypatch.setenv("LOG_CONFIG__SLOW_QUERY_THRESHOLD_MS", "250")
        monkeypatch.setenv("LOG_CONFIG__ENABLE_PERFORMANCE_PROCESSOR", "true")
        monkeypatch.setenv("LOG_CONFIG__ENABLE_ENVIRONMENT_PROCESSOR", "false")
        monkeypatch.setenv("LOG_CONFIG__ENABLE_ERROR_CONTEXT_PROCESSOR", "false")
        monkeypatch.setenv("LOG_CONFIG__LOG_REQUEST_BODY", "true")
        monkeypatch.setenv("LOG_CONFIG__LOG_RESPONSE_BODY", "true")
        monkeypatch.setenv("LOG_CONFIG__MAX_BODY_LOG_SIZE", "20480")

        settings = Settings()

        with pytest_check.check:
            assert settings.log_config.sampling_rate == 0.8
        with pytest_check.check:
            assert settings.log_config.enable_async_logging is True
        with pytest_check.check:
            assert settings.log_config.async_queue_size == 5000
        with pytest_check.check:
            assert settings.log_config.excluded_paths == ["/api/health", "/api/metrics"]
        with pytest_check.check:
            assert settings.log_config.sensitive_fields == ["api_key", "token"]
        with pytest_check.check:
            assert settings.log_config.enable_sql_logging is True
        with pytest_check.check:
            assert settings.log_config.slow_query_threshold_ms == 250
        with pytest_check.check:
            assert settings.log_config.enable_performance_processor is True
        with pytest_check.check:
            assert settings.log_config.enable_environment_processor is False
        with pytest_check.check:
            assert settings.log_config.enable_error_context_processor is False
        with pytest_check.check:
            assert settings.log_config.log_request_body is True
        with pytest_check.check:
            assert settings.log_config.log_response_body is True
        with pytest_check.check:
            assert settings.log_config.max_body_log_size == 20480

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
