"""Unit tests for LogConfig class."""

import pytest
from pydantic import ValidationError

from src.core.config import LogConfig


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

    def test_new_default_values(self) -> None:
        """Test default values for new LogConfig fields."""
        config = LogConfig()

        # Sampling and async logging
        assert config.sampling_rate == 1.0
        assert config.enable_async_logging is False
        assert config.async_queue_size == 10000

        # Path exclusion and sensitive fields
        assert config.excluded_paths == ["/health", "/metrics"]
        assert config.sensitive_fields == [
            "password",
            "token",
            "secret",
            "api_key",
            "authorization",
        ]

        # SQL logging
        assert config.enable_sql_logging is False
        assert config.slow_query_threshold_ms == 100

        # Processor flags
        assert config.enable_performance_processor is False
        assert config.enable_environment_processor is True
        assert config.enable_error_context_processor is True

        # Request/Response body logging
        assert config.log_request_body is False
        assert config.log_response_body is False
        assert config.max_body_log_size == 10240

    def test_sampling_rate_validation(self) -> None:
        """Test sampling_rate field validation."""
        # Valid rates
        LogConfig(sampling_rate=0.0)
        LogConfig(sampling_rate=0.5)
        LogConfig(sampling_rate=1.0)

        # Invalid rates
        with pytest.raises(ValidationError, match="greater than or equal to 0"):
            LogConfig(sampling_rate=-0.1)

        with pytest.raises(ValidationError, match="less than or equal to 1"):
            LogConfig(sampling_rate=1.1)

    def test_async_queue_size_validation(self) -> None:
        """Test async_queue_size field validation."""
        # Valid sizes
        LogConfig(async_queue_size=1)
        LogConfig(async_queue_size=50000)

        # Invalid size
        with pytest.raises(ValidationError, match="greater than 0"):
            LogConfig(async_queue_size=0)

    def test_slow_query_threshold_validation(self) -> None:
        """Test slow_query_threshold_ms field validation."""
        # Valid thresholds
        LogConfig(slow_query_threshold_ms=1)
        LogConfig(slow_query_threshold_ms=5000)

        # Invalid threshold
        with pytest.raises(ValidationError, match="greater than 0"):
            LogConfig(slow_query_threshold_ms=0)

    def test_max_body_log_size_validation(self) -> None:
        """Test max_body_log_size field validation."""
        # Valid sizes
        LogConfig(max_body_log_size=1)
        LogConfig(max_body_log_size=1048576)  # 1MB

        # Invalid size
        with pytest.raises(ValidationError, match="greater than 0"):
            LogConfig(max_body_log_size=0)

    def test_custom_list_fields(self) -> None:
        """Test custom values for list fields."""
        config = LogConfig(
            excluded_paths=["/api/v1/health", "/api/v1/ready"],
            sensitive_fields=["password", "creditcard", "ssn"],
        )
        assert config.excluded_paths == ["/api/v1/health", "/api/v1/ready"]
        assert config.sensitive_fields == ["password", "creditcard", "ssn"]

    def test_all_new_fields_custom_values(self) -> None:
        """Test all new fields with custom values."""
        config = LogConfig(
            sampling_rate=0.75,
            enable_async_logging=True,
            async_queue_size=20000,
            excluded_paths=["/status"],
            sensitive_fields=["key", "credential"],
            enable_sql_logging=True,
            slow_query_threshold_ms=200,
            enable_performance_processor=True,
            enable_environment_processor=False,
            enable_error_context_processor=False,
            log_request_body=True,
            log_response_body=True,
            max_body_log_size=20480,
        )

        assert config.sampling_rate == 0.75
        assert config.enable_async_logging is True
        assert config.async_queue_size == 20000
        assert config.excluded_paths == ["/status"]
        assert config.sensitive_fields == ["key", "credential"]
        assert config.enable_sql_logging is True
        assert config.slow_query_threshold_ms == 200
        assert config.enable_performance_processor is True
        assert config.enable_environment_processor is False
        assert config.enable_error_context_processor is False
        assert config.log_request_body is True
        assert config.log_response_body is True
        assert config.max_body_log_size == 20480

    def test_enhanced_sanitization_defaults(self) -> None:
        """Test default values for enhanced sanitization fields."""
        config = LogConfig()

        # Enhanced pattern-based detection defaults
        assert config.additional_sensitive_patterns == []
        assert config.sensitive_value_detection is True
        assert config.excluded_fields_from_sanitization == []

    def test_enhanced_sanitization_custom_values(self) -> None:
        """Test custom values for enhanced sanitization fields."""
        config = LogConfig(
            additional_sensitive_patterns=[r"\b\d{3}-\d{2}-\d{4}\b", r"[A-Z]{2}\d{6}"],
            sensitive_value_detection=False,
            excluded_fields_from_sanitization=["debug_info", "raw_data"],
        )

        assert config.additional_sensitive_patterns == [
            r"\b\d{3}-\d{2}-\d{4}\b",
            r"[A-Z]{2}\d{6}",
        ]
        assert config.sensitive_value_detection is False
        assert config.excluded_fields_from_sanitization == ["debug_info", "raw_data"]

    def test_complete_config_with_enhanced_sanitization(self) -> None:
        """Test LogConfig with all fields including enhanced sanitization."""
        config = LogConfig(
            log_level="DEBUG",
            log_format="json",
            sampling_rate=0.5,
            enable_async_logging=True,
            excluded_paths=["/health"],
            sensitive_fields=["password", "token"],
            enable_sql_logging=True,
            slow_query_threshold_ms=150,
            enable_performance_processor=True,
            log_request_body=True,
            max_body_log_size=15360,
            # Enhanced sanitization fields
            additional_sensitive_patterns=[r"\bSSN:\s*\d{3}-\d{2}-\d{4}\b"],
            sensitive_value_detection=True,
            excluded_fields_from_sanitization=["debug_field"],
        )

        # Standard fields
        assert config.log_level == "DEBUG"
        assert config.log_format == "json"
        assert config.sampling_rate == 0.5
        assert config.enable_async_logging is True
        assert config.excluded_paths == ["/health"]
        assert config.sensitive_fields == ["password", "token"]
        assert config.enable_sql_logging is True
        assert config.slow_query_threshold_ms == 150
        assert config.enable_performance_processor is True
        assert config.log_request_body is True
        assert config.max_body_log_size == 15360

        # Enhanced sanitization fields
        assert config.additional_sensitive_patterns == [r"\bSSN:\s*\d{3}-\d{2}-\d{4}\b"]
        assert config.sensitive_value_detection is True
        assert config.excluded_fields_from_sanitization == ["debug_field"]
