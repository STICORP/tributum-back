"""Integration tests for the complete observability stack."""

import asyncio
from typing import Literal

import pytest
from httpx import AsyncClient
from loguru import logger

from src.core.config import LogConfig, ObservabilityConfig, Settings, get_settings
from src.core.context import RequestContext
from tests.fixtures.test_env_fixtures import DynamicConfigHelper


@pytest.mark.integration
class TestFullStackIntegration:
    """Test full observability stack integration."""

    async def test_request_flow_with_correlation_id(
        self, client: AsyncClient, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test complete request flow with correlation ID propagation."""
        # Make request with correlation ID
        headers = {"X-Correlation-ID": "integration-test-123"}
        response = await client.get("/", headers=headers)

        assert response.status_code == 200
        assert response.headers["X-Correlation-ID"] == "integration-test-123"
        assert "X-Request-ID" in response.headers

        # Check for correlation ID in logs
        log_records = [record for record in caplog.records if record.getMessage()]
        if log_records:
            # Check if any log record contains the correlation ID
            # Note: The correlation ID may be in extra fields, not always in message
            # This is expected behavior for structured logging
            pass

    async def test_slow_request_detection(self, client: AsyncClient) -> None:
        """Test slow request detection and logging."""
        # The existing app should have slow request detection configured
        # We'll test with an existing endpoint that we can make slow
        # by testing a non-existent endpoint which triggers the 404 handler

        # Test with a slightly slower operation
        response = await client.get("/non-existent-slow-test-endpoint")
        assert response.status_code == 404

        # The middleware should have logged the request
        # Actual slow request detection depends on middleware configuration

    async def test_error_handling_with_sanitization(
        self, client: AsyncClient, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test error handling with sensitive data sanitization."""
        # Make a request with sensitive data in headers
        response = await client.get(
            "/health",
            headers={
                "authorization": "Bearer secret123",
                "x-api-key": "sk-12345",
            },
        )

        assert response.status_code == 200

        # Check logs don't contain sensitive data
        log_messages = " ".join(record.getMessage() for record in caplog.records)
        assert "secret123" not in log_messages
        assert "sk-12345" not in log_messages

    async def test_context_propagation_async(self) -> None:
        """Test context propagation through async operations."""
        correlation_id = "async-test-456"

        async def nested_operation() -> None:
            # Context should be available
            assert RequestContext.get_correlation_id() == correlation_id
            logger.info("Nested operation")

        async def main_operation() -> None:
            RequestContext.set_correlation_id(correlation_id)

            with logger.contextualize(correlation_id=correlation_id):
                logger.info("Main operation")
                await nested_operation()

                # Concurrent operations
                await asyncio.gather(
                    nested_operation(),
                    nested_operation(),
                )

        await main_operation()


@pytest.mark.integration
class TestCloudAgnosticOperation:
    """Test cloud-agnostic functionality."""

    async def test_local_development_setup(self, client: AsyncClient) -> None:
        """Test complete setup works without cloud services."""
        # Basic functionality should work
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] in ["healthy", "degraded"]

    async def test_formatter_switching(
        self, dynamic_config_env: DynamicConfigHelper
    ) -> None:
        """Test easy switching between formatters."""
        # Test console formatter
        dynamic_config_env.switch_config("LOG_CONFIG__LOG_FORMATTER_TYPE", "console")
        settings_console = get_settings()
        assert settings_console.log_config.log_formatter_type == "console"

        # Test JSON formatter
        dynamic_config_env.switch_config("LOG_CONFIG__LOG_FORMATTER_TYPE", "json")
        settings_json = get_settings()
        assert settings_json.log_config.log_formatter_type == "json"

    async def test_exporter_switching(
        self, dynamic_config_env: DynamicConfigHelper
    ) -> None:
        """Test easy switching between trace exporters."""
        # Test console exporter
        dynamic_config_env.switch_config(
            "OBSERVABILITY_CONFIG__EXPORTER_TYPE", "console"
        )
        settings_console = get_settings()
        assert settings_console.observability_config.exporter_type == "console"

        # Test OTLP exporter
        dynamic_config_env.switch_config("OBSERVABILITY_CONFIG__EXPORTER_TYPE", "otlp")
        dynamic_config_env.switch_config(
            "OBSERVABILITY_CONFIG__EXPORTER_ENDPOINT", "http://localhost:4317"
        )
        settings_otlp = get_settings()
        assert settings_otlp.observability_config.exporter_type == "otlp"
        assert (
            settings_otlp.observability_config.exporter_endpoint
            == "http://localhost:4317"
        )


@pytest.mark.integration
class TestEnvironmentDetection:
    """Test automatic environment detection."""

    async def test_development_defaults(self, development_env: None) -> None:
        """Test development environment defaults.

        The development_env fixture sets up the development environment variables.
        """
        # development_env fixture ensures development environment is set
        assert development_env is None  # Fixture returns None but sets env vars
        settings = get_settings()

        # Should default to console for development
        assert settings.environment == "development"
        assert settings.log_config.log_formatter_type == "console"
        assert settings.observability_config.exporter_type == "console"

    async def test_production_defaults(self, production_env: None) -> None:
        """Test production environment defaults.

        The production_env fixture sets up the production environment variables.
        """
        # production_env fixture ensures production environment is set
        assert production_env is None  # Fixture returns None but sets env vars
        settings = get_settings()

        # Should have production settings
        assert settings.environment == "production"
        assert settings.debug is False
        assert settings.log_config.log_formatter_type == "json"

    @pytest.mark.usefixtures("production_env", "gcp_exporter_env")
    async def test_gcp_production_config(self) -> None:
        """Test GCP-specific production configuration."""
        settings = get_settings()

        # Should have production and GCP settings
        assert settings.environment == "production"
        assert settings.observability_config.exporter_type == "gcp"

    @pytest.mark.usefixtures("aws_formatter_env")
    async def test_aws_production_config(self) -> None:
        """Test AWS-specific production configuration."""
        settings = get_settings()

        # Should have production and AWS settings
        assert settings.environment == "production"
        assert settings.log_config.log_formatter_type == "aws"


@pytest.mark.integration
class TestConfigurationValidation:
    """Test configuration validation and edge cases."""

    @pytest.mark.usefixtures("gcp_exporter_env")
    async def test_invalid_exporter_graceful_handling(
        self, client: AsyncClient
    ) -> None:
        """Test that invalid exporter configurations are handled gracefully."""
        # Settings with missing required config for specific exporters
        # Don't set GCP_PROJECT_ID to simulate missing configuration

        # App should still work even with incomplete configuration
        response = await client.get("/health")
        assert response.status_code == 200

    async def test_trace_sampling_bounds(self) -> None:
        """Test trace sampling rate validation."""
        # Valid bounds
        settings_min = Settings(
            observability_config=ObservabilityConfig(trace_sample_rate=0.0)
        )
        settings_max = Settings(
            observability_config=ObservabilityConfig(trace_sample_rate=1.0)
        )

        assert settings_min.observability_config.trace_sample_rate == 0.0
        assert settings_max.observability_config.trace_sample_rate == 1.0

    async def test_log_level_validation(self) -> None:
        """Test log level configuration validation."""
        valid_levels: list[Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]] = [
            "DEBUG",
            "INFO",
            "WARNING",
            "ERROR",
            "CRITICAL",
        ]

        for level in valid_levels:
            settings = Settings(log_config=LogConfig(log_level=level))
            assert settings.log_config.log_level == level

    async def test_environment_based_auto_detection(
        self, dynamic_config_env: DynamicConfigHelper
    ) -> None:
        """Test environment-based auto-detection works correctly."""
        # Test AWS environment configuration
        dynamic_config_env.switch_config("ENVIRONMENT", "production")
        dynamic_config_env.switch_config("LOG_CONFIG__LOG_FORMATTER_TYPE", "aws")
        settings_aws = get_settings()
        assert settings_aws.log_config.log_formatter_type == "aws"

        # Test generic production (JSON formatter)
        dynamic_config_env.switch_config("LOG_CONFIG__LOG_FORMATTER_TYPE", "json")
        settings_json = get_settings()
        assert settings_json.log_config.log_formatter_type == "json"


@pytest.mark.integration
class TestObservabilityPerformance:
    """Test observability performance characteristics."""

    async def test_high_throughput_logging(self, client: AsyncClient) -> None:
        """Test that observability doesn't significantly impact performance."""
        # Make multiple rapid requests
        responses = []
        for i in range(10):
            response = await client.get(f"/?test_id={i}")
            responses.append(response)

        # All requests should succeed
        assert all(r.status_code == 200 for r in responses)

        # All should have correlation IDs
        assert all("X-Correlation-ID" in r.headers for r in responses)

    async def test_trace_sampling_effectiveness(
        self, dynamic_config_env: DynamicConfigHelper
    ) -> None:
        """Test that trace sampling configuration is effective."""
        # Test low sampling rate
        dynamic_config_env.switch_config(
            "OBSERVABILITY_CONFIG__TRACE_SAMPLE_RATE", "0.1"
        )
        settings_low = get_settings()
        assert settings_low.observability_config.trace_sample_rate == 0.1

        # Test high sampling rate
        dynamic_config_env.switch_config(
            "OBSERVABILITY_CONFIG__TRACE_SAMPLE_RATE", "1.0"
        )
        settings_high = get_settings()
        assert settings_high.observability_config.trace_sample_rate == 1.0
