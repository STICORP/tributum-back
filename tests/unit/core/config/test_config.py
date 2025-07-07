"""Unit tests for src/core/config.py module.

This module contains comprehensive unit tests for the configuration management
system, including type-safe configuration with validation, environment variable
support, and cloud provider auto-detection.
"""

import os
import threading
from pathlib import Path
from typing import Any, Literal, cast

import pytest
from pydantic import ValidationError
from pytest_mock import MockerFixture

from src.core.config import (
    DatabaseConfig,
    LogConfig,
    ObservabilityConfig,
    Settings,
    get_config_defaults,
    get_settings,
)


@pytest.mark.unit
class TestLogConfig:
    """Tests for the LogConfig model."""

    def test_default_values(self) -> None:
        """Verify LogConfig initializes with correct default values."""
        config = LogConfig()

        assert config.log_level == "INFO"
        assert config.log_formatter_type is None
        assert config.excluded_paths == ["/health", "/metrics"]
        assert config.slow_request_threshold_ms == 1000
        assert config.enable_sql_logging is False
        assert config.slow_query_threshold_ms == 100
        assert config.sensitive_fields == [
            "password",
            "token",
            "secret",
            "api_key",
            "authorization",
        ]

    @pytest.mark.parametrize(
        ("field", "value", "expected_error"),
        [
            ("slow_request_threshold_ms", 0, "greater than 0"),
            ("slow_request_threshold_ms", -1, "greater than 0"),
            ("slow_query_threshold_ms", 0, "greater than 0"),
            ("slow_query_threshold_ms", -100, "greater than 0"),
        ],
    )
    def test_field_validation(
        self, field: str, value: int, expected_error: str
    ) -> None:
        """Verify field constraints are enforced."""
        with pytest.raises(ValidationError) as exc_info:
            LogConfig.model_validate({field: value})

        error_dict = exc_info.value.errors()[0]
        assert error_dict["loc"] == (field,)
        assert expected_error in str(error_dict["msg"])

    @pytest.mark.parametrize(
        "log_level",
        ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
    )
    def test_log_level_enum_validation_valid(self, log_level: str) -> None:
        """Verify valid log levels are accepted."""
        log_level_typed = cast(
            "Literal['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']", log_level
        )
        config = LogConfig(log_level=log_level_typed)
        assert config.log_level == log_level

    def test_log_level_enum_validation_invalid_trace(self) -> None:
        """Verify TRACE log level is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            LogConfig.model_validate({"log_level": "TRACE"})
        error = exc_info.value.errors()[0]
        assert error["loc"] == ("log_level",)

    def test_log_level_enum_validation_invalid_case_sensitive(self) -> None:
        """Verify log levels are case sensitive."""
        with pytest.raises(ValidationError) as exc_info:
            LogConfig.model_validate({"log_level": "info"})
        error = exc_info.value.errors()[0]
        assert error["loc"] == ("log_level",)

    def test_log_level_enum_validation_invalid_unknown(self) -> None:
        """Verify unknown log levels are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            LogConfig.model_validate({"log_level": "INVALID"})
        error = exc_info.value.errors()[0]
        assert error["loc"] == ("log_level",)

    def test_log_level_enum_validation_invalid_empty(self) -> None:
        """Verify empty log level is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            LogConfig.model_validate({"log_level": ""})
        error = exc_info.value.errors()[0]
        assert error["loc"] == ("log_level",)

    @pytest.mark.parametrize(
        "formatter_type",
        ["console", "json", "gcp", "aws"],
    )
    def test_formatter_type_enum_validation_valid(self, formatter_type: str) -> None:
        """Verify valid formatter types are accepted."""
        formatter_typed = cast(
            "Literal['console', 'json', 'gcp', 'aws']", formatter_type
        )
        config = LogConfig(log_formatter_type=formatter_typed)
        assert config.log_formatter_type == formatter_type

    def test_formatter_type_enum_validation_valid_none(self) -> None:
        """Verify None formatter type is accepted."""
        config = LogConfig(log_formatter_type=None)
        assert config.log_formatter_type is None

    def test_formatter_type_enum_validation_invalid_xml(self) -> None:
        """Verify xml formatter type is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            LogConfig.model_validate({"log_formatter_type": "xml"})
        error = exc_info.value.errors()[0]
        assert error["loc"] == ("log_formatter_type",)

    def test_formatter_type_enum_validation_invalid_yaml(self) -> None:
        """Verify yaml formatter type is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            LogConfig.model_validate({"log_formatter_type": "yaml"})
        error = exc_info.value.errors()[0]
        assert error["loc"] == ("log_formatter_type",)

    def test_formatter_type_enum_validation_invalid_case_sensitive(self) -> None:
        """Verify formatter types are case sensitive."""
        with pytest.raises(ValidationError) as exc_info:
            LogConfig.model_validate({"log_formatter_type": "CONSOLE"})
        error = exc_info.value.errors()[0]
        assert error["loc"] == ("log_formatter_type",)

    def test_formatter_type_enum_validation_invalid_empty(self) -> None:
        """Verify empty formatter type is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            LogConfig.model_validate({"log_formatter_type": ""})
        error = exc_info.value.errors()[0]
        assert error["loc"] == ("log_formatter_type",)


@pytest.mark.unit
class TestObservabilityConfig:
    """Tests for the ObservabilityConfig model."""

    def test_default_values(self) -> None:
        """Verify ObservabilityConfig defaults are correct."""
        config = ObservabilityConfig()

        assert config.enable_tracing is True
        assert config.exporter_type == "console"
        assert config.exporter_endpoint is None
        assert config.gcp_project_id is None
        assert config.trace_sample_rate == 1.0

    @pytest.mark.parametrize(
        ("field", "input_value", "expected_value"),
        [
            ("exporter_endpoint", "", None),
            ("exporter_endpoint", None, None),
            ("exporter_endpoint", "http://localhost:4317", "http://localhost:4317"),
            ("gcp_project_id", "", None),
            ("gcp_project_id", None, None),
            ("gcp_project_id", "my-project-123", "my-project-123"),
        ],
    )
    def test_empty_str_to_none_validator(
        self, field: str, input_value: str | None, expected_value: str | None
    ) -> None:
        """Verify empty strings are converted to None for nullable fields."""
        config = ObservabilityConfig.model_validate({field: input_value})
        assert getattr(config, field) == expected_value

    @pytest.mark.parametrize(
        ("rate", "is_valid"),
        [
            (0.0, True),
            (0.5, True),
            (1.0, True),
            (-0.1, False),
            (1.1, False),
            (2.0, False),
            (-1.0, False),
        ],
    )
    def test_trace_sample_rate_validation(self, rate: float, is_valid: bool) -> None:
        """Verify trace_sample_rate constraints (0.0-1.0)."""
        if is_valid:
            config = ObservabilityConfig(trace_sample_rate=rate)
            assert config.trace_sample_rate == rate
        else:
            with pytest.raises(ValidationError) as exc_info:
                ObservabilityConfig(trace_sample_rate=rate)
            error = exc_info.value.errors()[0]
            assert error["loc"] == ("trace_sample_rate",)

    @pytest.mark.parametrize(
        "exporter_type",
        ["console", "gcp", "aws", "otlp", "none"],
    )
    def test_exporter_type_enum_validation_valid(self, exporter_type: str) -> None:
        """Verify valid exporter types are accepted."""
        exporter_typed = cast(
            "Literal['console', 'gcp', 'aws', 'otlp', 'none']", exporter_type
        )
        config = ObservabilityConfig(exporter_type=exporter_typed)
        assert config.exporter_type == exporter_type

    def test_exporter_type_enum_validation_invalid_jaeger(self) -> None:
        """Verify jaeger exporter type is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ObservabilityConfig.model_validate({"exporter_type": "jaeger"})
        error = exc_info.value.errors()[0]
        assert error["loc"] == ("exporter_type",)

    def test_exporter_type_enum_validation_invalid_zipkin(self) -> None:
        """Verify zipkin exporter type is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ObservabilityConfig.model_validate({"exporter_type": "zipkin"})
        error = exc_info.value.errors()[0]
        assert error["loc"] == ("exporter_type",)

    def test_exporter_type_enum_validation_invalid_case_sensitive(self) -> None:
        """Verify exporter types are case sensitive."""
        with pytest.raises(ValidationError) as exc_info:
            ObservabilityConfig.model_validate({"exporter_type": "CONSOLE"})
        error = exc_info.value.errors()[0]
        assert error["loc"] == ("exporter_type",)

    def test_exporter_type_enum_validation_invalid_empty(self) -> None:
        """Verify empty exporter type is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ObservabilityConfig.model_validate({"exporter_type": ""})
        error = exc_info.value.errors()[0]
        assert error["loc"] == ("exporter_type",)


@pytest.mark.unit
class TestDatabaseConfig:
    """Tests for the DatabaseConfig model."""

    def test_default_values(self) -> None:
        """Verify DatabaseConfig defaults are correct."""
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

    @pytest.mark.parametrize(
        ("url", "is_valid"),
        [
            ("postgresql+asyncpg://user:pass@localhost/db", True),
            ("postgresql+asyncpg://user:pass@localhost:5432/db", True),
            ("postgresql+asyncpg://user:pass@host/db?sslmode=require", True),
            ("postgresql://user:pass@localhost/db", False),
            ("mysql://user:pass@localhost/db", False),
            ("sqlite:///path/to/db", False),
            ("postgresql+psycopg2://user:pass@localhost/db", False),
        ],
    )
    def test_database_url_validation(self, url: str, is_valid: bool) -> None:
        """Verify only postgresql+asyncpg URLs are accepted."""
        if is_valid:
            config = DatabaseConfig(database_url=url)
            assert config.database_url == url
        else:
            with pytest.raises(ValidationError) as exc_info:
                DatabaseConfig(database_url=url)
            error_msg = str(exc_info.value)
            assert "Database URL must use postgresql+asyncpg:// driver" in error_msg

    @pytest.mark.parametrize(
        ("field", "value", "is_valid"),
        [
            # pool_size tests (1-100)
            ("pool_size", 1, True),
            ("pool_size", 50, True),
            ("pool_size", 100, True),
            ("pool_size", 0, False),
            ("pool_size", 101, False),
            ("pool_size", -1, False),
            # max_overflow tests (0-50)
            ("max_overflow", 0, True),
            ("max_overflow", 25, True),
            ("max_overflow", 50, True),
            ("max_overflow", -1, False),
            ("max_overflow", 51, False),
            # pool_timeout tests (>0, <=300)
            ("pool_timeout", 0.1, True),
            ("pool_timeout", 150.0, True),
            ("pool_timeout", 300.0, True),
            ("pool_timeout", 0.0, False),
            ("pool_timeout", -1.0, False),
            ("pool_timeout", 301.0, False),
        ],
    )
    def test_pool_configuration_validation(
        self, field: str, value: int | float, is_valid: bool
    ) -> None:
        """Verify pool configuration constraints."""
        if is_valid:
            config = DatabaseConfig.model_validate({field: value})
            assert getattr(config, field) == value
        else:
            with pytest.raises(ValidationError) as exc_info:
                DatabaseConfig.model_validate({field: value})
            error = exc_info.value.errors()[0]
            assert error["loc"] == (field,)

    @pytest.mark.parametrize(
        ("original_url", "expected_test_url"),
        [
            # Standard patterns
            (
                "postgresql+asyncpg://user:pass@localhost/tributum_db",
                "postgresql+asyncpg://user:pass@localhost/tributum_test",
            ),
            (
                "postgresql+asyncpg://user:pass@localhost/tributum",
                "postgresql+asyncpg://user:pass@localhost/tributum_test",
            ),
            # With query parameters
            (
                "postgresql+asyncpg://user:pass@localhost/tributum_db?sslmode=require",
                "postgresql+asyncpg://user:pass@localhost/tributum_test?sslmode=require",
            ),
            # Custom database names
            (
                "postgresql+asyncpg://user:pass@localhost/myapp",
                "postgresql+asyncpg://user:pass@localhost/myapp_test",
            ),
            # Edge case: no database name - appends _test to last part
            (
                "postgresql+asyncpg://user:pass@localhost",
                "postgresql+asyncpg://user:pass@localhost_test",
            ),
        ],
    )
    def test_get_test_database_url(
        self, original_url: str, expected_test_url: str
    ) -> None:
        """Verify test database URL generation."""
        config = DatabaseConfig(database_url=original_url)
        assert config.get_test_database_url() == expected_test_url


@pytest.mark.unit
class TestSettings:
    """Tests for the main Settings class."""

    def test_default_initialization(self) -> None:
        """Verify Settings initializes with all defaults."""
        settings = Settings()

        # Application settings
        assert settings.app_name == "Tributum"
        assert settings.app_version == "0.3.0"
        assert settings.environment == "development"
        assert settings.debug is True

        # API settings
        assert settings.api_host == "127.0.0.1"
        assert settings.api_port == 8000
        assert settings.docs_url == "/docs"
        assert settings.redoc_url == "/redoc"
        assert settings.openapi_url == "/openapi.json"

        # Nested configs should have their defaults
        assert isinstance(settings.log_config, LogConfig)
        assert isinstance(settings.observability_config, ObservabilityConfig)
        assert isinstance(settings.database_config, DatabaseConfig)

    def test_env_file_loading(
        self,
        temp_env_file: Path,
    ) -> None:
        """Verify .env file is loaded correctly."""
        # Create a temporary .env file
        temp_env_file.write_text(
            "APP_NAME=TestApp\nAPP_VERSION=2.0.0\nENVIRONMENT=production\nDEBUG=false\n"
        )

        # Mock the file path to use our temp file
        old_cwd = Path.cwd()
        os.chdir(temp_env_file.parent)

        # Create .env file in the directory
        (temp_env_file.parent / ".env").write_text(temp_env_file.read_text())

        try:
            settings = Settings()
        finally:
            os.chdir(old_cwd)

        assert settings.app_name == "TestApp"
        assert settings.app_version == "2.0.0"
        assert settings.environment == "production"
        assert settings.debug is False

    @pytest.mark.parametrize(
        ("env_vars", "expected"),
        [
            # Basic overrides
            (
                {"APP_NAME": "EnvApp", "DEBUG": "false"},
                {"app_name": "EnvApp", "debug": False},
            ),
            # Nested configuration
            (
                {
                    "LOG_CONFIG__LOG_LEVEL": "ERROR",
                    "LOG_CONFIG__ENABLE_SQL_LOGGING": "true",
                },
                {
                    "log_config.log_level": "ERROR",
                    "log_config.enable_sql_logging": True,
                },
            ),
            # Multiple levels of override
            (
                {
                    "ENVIRONMENT": "production",
                    "API_PORT": "9000",
                    "DATABASE_CONFIG__POOL_SIZE": "20",
                },
                {
                    "environment": "production",
                    "api_port": 9000,
                    "database_config.pool_size": 20,
                },
            ),
        ],
    )
    def test_environment_variable_override(
        self,
        monkeypatch: pytest.MonkeyPatch,
        env_vars: dict[str, str],
        expected: dict[str, Any],
    ) -> None:
        """Verify env vars override defaults and .env file."""
        for key, value in env_vars.items():
            monkeypatch.setenv(key, value)

        settings = Settings()

        for path, expected_value in expected.items():
            if "." in path:
                # Handle nested attributes
                obj = settings
                for attr in path.split(".")[:-1]:
                    obj = getattr(obj, attr)
                actual_value = getattr(obj, path.split(".")[-1])
            else:
                actual_value = getattr(settings, path)
            assert actual_value == expected_value

    def test_nested_delimiter_support(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Verify __ delimiter works for nested configs."""
        monkeypatch.setenv("LOG_CONFIG__LOG_LEVEL", "DEBUG")
        monkeypatch.setenv("LOG_CONFIG__LOG_FORMATTER_TYPE", "json")
        monkeypatch.setenv("OBSERVABILITY_CONFIG__TRACE_SAMPLE_RATE", "0.5")
        monkeypatch.setenv("DATABASE_CONFIG__ECHO", "true")

        settings = Settings()

        assert settings.log_config.log_level == "DEBUG"
        assert settings.log_config.log_formatter_type == "json"
        assert settings.observability_config.trace_sample_rate == 0.5
        assert settings.database_config.echo is True

    @pytest.mark.parametrize(
        ("field", "value"),
        [
            ("docs_url", ""),
            ("redoc_url", ""),
            ("openapi_url", ""),
        ],
    )
    def test_empty_str_to_none_validator(
        self,
        monkeypatch: pytest.MonkeyPatch,
        field: str,
        value: str,
    ) -> None:
        """Verify empty strings become None for URL fields."""
        env_key = field.upper()
        monkeypatch.setenv(env_key, value)

        settings = Settings()
        assert getattr(settings, field) is None

    def test_model_post_init_development(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Verify post-init logic for development environment."""
        monkeypatch.setenv("ENVIRONMENT", "development")
        settings = Settings()

        # In test environment, formatter is always "console" due to test config
        # But we can verify the detection logic works
        assert settings._detect_formatter() == "console"
        # Exporter should remain console
        assert settings.observability_config.exporter_type == "console"
        # Sample rate should remain 1.0
        assert settings.observability_config.trace_sample_rate == 1.0

    def test_model_post_init_production(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Verify post-init logic for production environment."""
        monkeypatch.setenv("ENVIRONMENT", "production")
        settings = Settings()

        # In production, trace sample rate should be adjusted
        assert settings.observability_config.trace_sample_rate == 0.1

        # Test detection methods work correctly
        assert settings._detect_formatter() == "json"  # No cloud env
        assert settings._detect_exporter() == "otlp"  # No cloud env

        # Test cloud detection
        monkeypatch.setenv("K_SERVICE", "test-service")
        settings = Settings()
        assert settings._detect_formatter() == "gcp"
        assert settings._detect_exporter() == "gcp"

    def test_detect_formatter_logic(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Verify formatter auto-detection method works correctly."""
        # Test the _detect_formatter method directly since the actual Settings
        # initialization in test environment doesn't trigger auto-detection

        # Test GCP detection
        monkeypatch.setenv("K_SERVICE", "test-service")
        monkeypatch.setenv("ENVIRONMENT", "development")
        settings = Settings()
        assert settings._detect_formatter() == "gcp"

        # Test AWS detection
        monkeypatch.delenv("K_SERVICE", raising=False)
        monkeypatch.setenv("AWS_EXECUTION_ENV", "AWS_Lambda_python3.13")
        settings = Settings()
        assert settings._detect_formatter() == "aws"

        # Test development default
        monkeypatch.delenv("AWS_EXECUTION_ENV", raising=False)
        monkeypatch.setenv("ENVIRONMENT", "development")
        settings = Settings()
        assert settings._detect_formatter() == "console"

        # Test production default
        monkeypatch.setenv("ENVIRONMENT", "production")
        settings = Settings()
        assert settings._detect_formatter() == "json"

    def test_detect_exporter_logic(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Verify exporter auto-detection method works correctly."""
        # Test the _detect_exporter method directly

        # Test GCP detection
        monkeypatch.setenv("K_SERVICE", "test-service")
        monkeypatch.setenv("ENVIRONMENT", "production")
        settings = Settings()
        assert settings._detect_exporter() == "gcp"

        # Test AWS detection
        monkeypatch.delenv("K_SERVICE", raising=False)
        monkeypatch.setenv("AWS_EXECUTION_ENV", "AWS_Lambda")
        settings = Settings()
        assert settings._detect_exporter() == "aws"

        # Test production default (no cloud)
        monkeypatch.delenv("AWS_EXECUTION_ENV", raising=False)
        monkeypatch.setenv("ENVIRONMENT", "production")
        settings = Settings()
        assert settings._detect_exporter() == "otlp"

        # Test development default
        monkeypatch.setenv("ENVIRONMENT", "development")
        settings = Settings()
        assert settings._detect_exporter() == "console"

    def test_model_config_attributes(self) -> None:
        """Verify Settings model_config is properly configured."""
        config = Settings.model_config

        assert config.get("env_file") == ".env"
        assert config.get("env_file_encoding") == "utf-8"
        assert config.get("case_sensitive") is False
        assert config.get("validate_default") is True
        assert config.get("env_nested_delimiter") == "__"

    def test_cloud_env_conflict(
        self,
        mock_cloud_env: dict[str, Any],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Verify behavior when both GCP and AWS env vars are set."""
        mock_cloud_env["set_both"]()
        monkeypatch.setenv("ENVIRONMENT", "production")

        settings = Settings()

        # GCP should take precedence (first check in code)
        assert settings._detect_formatter() == "gcp"
        assert settings._detect_exporter() == "gcp"

    def test_malformed_env_file(
        self,
        temp_env_file: Path,
    ) -> None:
        """Verify graceful handling of malformed .env files."""
        # Create a malformed .env file with some valid app variables
        temp_env_file.write_text(
            "APP_NAME=TestApp\n"
            "INVALID LINE WITHOUT EQUALS\n"
            "ENVIRONMENT=development\n"
            "=INVALID_NO_KEY\n"
        )

        # The settings should still load with valid values from properly formatted lines
        old_cwd = Path.cwd()
        os.chdir(temp_env_file.parent)

        # Create .env file in the directory
        (temp_env_file.parent / ".env").write_text(temp_env_file.read_text())

        try:
            # Should not raise an exception - invalid lines are ignored by python-dotenv
            settings = Settings()
            assert isinstance(settings, Settings)
            assert settings.app_name == "TestApp"
            assert settings.environment == "development"
        finally:
            os.chdir(old_cwd)

    @pytest.mark.parametrize(
        ("env_key", "expected_value"),
        [
            ("APP_NAME", "TestApp"),
            ("app_name", "TestApp"),
            ("App_Name", "TestApp"),
            ("APP_name", "TestApp"),
        ],
    )
    def test_case_sensitivity(
        self,
        monkeypatch: pytest.MonkeyPatch,
        env_key: str,
        expected_value: str,
    ) -> None:
        """Verify environment variables are case-insensitive."""
        monkeypatch.setenv(env_key, expected_value)

        settings = Settings()
        assert settings.app_name == expected_value


@pytest.mark.unit
class TestGetSettings:
    """Tests for the get_settings function and caching."""

    def test_returns_settings_instance(self) -> None:
        """Verify get_settings returns Settings instance."""
        settings = get_settings()
        assert isinstance(settings, Settings)

    def test_caching_behavior(self, mocker: MockerFixture) -> None:
        """Verify settings instance is cached."""
        # Mock the Settings class to track instantiation
        settings_spy = mocker.spy(Settings, "__new__")

        # First call should create new instance
        settings1 = get_settings()
        assert settings_spy.call_count == 1

        # Second call should return cached instance
        settings2 = get_settings()
        assert settings_spy.call_count == 1

        # Should be the same instance
        assert settings1 is settings2

    def test_cache_clearing(self) -> None:
        """Verify cache can be cleared."""
        # Get initial instance
        settings1 = get_settings()

        # Clear cache
        get_settings.cache_clear()

        # Get new instance
        settings2 = get_settings()

        # Should be different instances
        assert settings1 is not settings2

    def test_thread_safety(self, thread_sync: dict[str, Any]) -> None:
        """Verify get_settings is thread-safe."""
        # Pre-populate the cache to ensure a baseline instance exists
        baseline_settings = get_settings()

        num_threads = 5  # Reduce thread count for more reliable testing
        barrier = thread_sync["barrier"](num_threads)
        results = thread_sync["create_results"]()

        def get_settings_in_thread() -> None:
            """Get settings instance in a thread."""
            try:
                # Wait for all threads to be ready
                barrier.wait()
                # Get settings
                settings = get_settings()
                # Store result
                results.append(settings)
            except Exception as e:
                results.append(f"ERROR: {e}")

        # Create and start threads
        threads = []
        for _ in range(num_threads):
            thread = threading.Thread(target=get_settings_in_thread)
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete with timeout
        for thread in threads:
            thread.join(timeout=5.0)
            assert not thread.is_alive(), "Thread did not complete in time"

        # All threads should get the same instance
        assert len(results) == num_threads

        # Check for errors
        errors = [r for r in results if isinstance(r, str) and r.startswith("ERROR")]
        assert not errors, f"Thread errors: {errors}"

        # All results should be the same Settings instance
        for instance in results:
            assert instance is baseline_settings, (
                "Expected same instance, got different instances"
            )


@pytest.mark.unit
class TestGetConfigDefaults:
    """Tests for the get_config_defaults helper."""

    def test_production_defaults(self) -> None:
        """Verify correct defaults for production."""
        defaults = get_config_defaults("production")

        assert defaults == {
            "log_config": {
                "log_formatter_type": "gcp",
            },
            "observability_config": {
                "exporter_type": "gcp",
            },
        }

    def test_development_defaults(self) -> None:
        """Verify correct defaults for development."""
        defaults = get_config_defaults("development")

        assert defaults == {
            "log_config": {
                "log_formatter_type": "console",
            },
            "observability_config": {
                "exporter_type": "console",
            },
        }

    @pytest.mark.parametrize(
        "environment",
        ["staging", "test", "custom", "unknown", ""],
    )
    def test_unknown_environment(self, environment: str) -> None:
        """Verify behavior with unknown environment."""
        defaults = get_config_defaults(environment)

        # Should return development defaults
        assert defaults == {
            "log_config": {
                "log_formatter_type": "console",
            },
            "observability_config": {
                "exporter_type": "console",
            },
        }
