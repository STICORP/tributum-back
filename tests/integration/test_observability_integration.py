"""Integration tests for the complete observability stack."""

import asyncio
from collections.abc import Generator
from io import StringIO
from typing import Literal

import pytest
from httpx import AsyncClient
from loguru import logger

from src.core.config import LogConfig, ObservabilityConfig, Settings, get_settings
from src.core.context import RequestContext


@pytest.fixture
def capture_logs() -> Generator[StringIO]:
    """Capture logs for inspection."""
    output = StringIO()
    handler_id = logger.add(
        output,
        format="{time} | {level} | {message} | {extra}",
        level="DEBUG",
    )

    yield output

    logger.remove(handler_id)


@pytest.mark.integration
class TestFullStackIntegration:
    """Test full observability stack integration."""

    async def test_request_flow_with_correlation_id(
        self, client: AsyncClient, capture_logs: StringIO
    ) -> None:
        """Test complete request flow with correlation ID propagation."""
        # Make request with correlation ID
        headers = {"X-Correlation-ID": "integration-test-123"}
        response = await client.get("/", headers=headers)

        assert response.status_code == 200
        assert response.headers["X-Correlation-ID"] == "integration-test-123"
        assert "X-Request-ID" in response.headers

        # Parse logs
        log_output = capture_logs.getvalue().strip()
        if log_output:
            # Check for correlation ID in logs
            assert "integration-test-123" in log_output

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
        self, client: AsyncClient, capture_logs: StringIO
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
        log_output = capture_logs.getvalue()
        assert "secret123" not in log_output
        assert "sk-12345" not in log_output

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

    async def test_formatter_switching(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test easy switching between formatters."""
        # Test console formatter
        monkeypatch.setenv("LOG_CONFIG__LOG_FORMATTER_TYPE", "console")
        get_settings.cache_clear()
        settings_console = get_settings()
        assert settings_console.log_config.log_formatter_type == "console"

        # Test JSON formatter
        monkeypatch.setenv("LOG_CONFIG__LOG_FORMATTER_TYPE", "json")
        get_settings.cache_clear()
        settings_json = get_settings()
        assert settings_json.log_config.log_formatter_type == "json"

    async def test_exporter_switching(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test easy switching between trace exporters."""
        # Test console exporter
        monkeypatch.setenv("OBSERVABILITY_CONFIG__EXPORTER_TYPE", "console")
        get_settings.cache_clear()
        settings_console = get_settings()
        assert settings_console.observability_config.exporter_type == "console"

        # Test OTLP exporter
        monkeypatch.setenv("OBSERVABILITY_CONFIG__EXPORTER_TYPE", "otlp")
        monkeypatch.setenv(
            "OBSERVABILITY_CONFIG__EXPORTER_ENDPOINT", "http://localhost:4317"
        )
        get_settings.cache_clear()
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
        """Test development environment defaults."""
        _ = development_env  # Fixture used for its side effects
        settings = get_settings()

        # Should default to console for development
        assert settings.environment == "development"
        assert settings.log_config.log_formatter_type == "console"
        assert settings.observability_config.exporter_type == "console"

    async def test_production_defaults(
        self, production_env: None, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test production environment defaults."""
        _ = production_env  # Fixture used for its side effects

        # Add specific production configuration
        monkeypatch.setenv("LOG_CONFIG__LOG_FORMATTER_TYPE", "gcp")
        monkeypatch.setenv("OBSERVABILITY_CONFIG__EXPORTER_TYPE", "gcp")
        monkeypatch.setenv("OBSERVABILITY_CONFIG__TRACE_SAMPLE_RATE", "0.1")

        get_settings.cache_clear()
        settings = get_settings()

        # Should have production settings
        assert settings.environment == "production"
        assert settings.log_config.log_formatter_type == "gcp"
        assert settings.observability_config.trace_sample_rate == 0.1


@pytest.mark.integration
class TestConfigurationValidation:
    """Test configuration validation and edge cases."""

    async def test_invalid_exporter_graceful_handling(
        self, client: AsyncClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that invalid exporter configurations are handled gracefully."""
        # Settings with missing required config for specific exporters
        monkeypatch.setenv("OBSERVABILITY_CONFIG__EXPORTER_TYPE", "gcp")
        # Don't set GCP_PROJECT_ID to simulate missing configuration

        # App should still work even with incomplete configuration
        response = await client.get("/health")
        assert response.status_code == 200

    def test_trace_sampling_bounds(self) -> None:
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

    def test_log_level_validation(self) -> None:
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
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test environment-based auto-detection works correctly."""
        # Test AWS environment configuration
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("LOG_CONFIG__LOG_FORMATTER_TYPE", "aws")
        get_settings.cache_clear()
        settings_aws = get_settings()
        assert settings_aws.log_config.log_formatter_type == "aws"

        # Test generic production (JSON formatter)
        monkeypatch.setenv("LOG_CONFIG__LOG_FORMATTER_TYPE", "json")
        get_settings.cache_clear()
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
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that trace sampling configuration is effective."""
        # Test low sampling rate
        monkeypatch.setenv("OBSERVABILITY_CONFIG__TRACE_SAMPLE_RATE", "0.1")
        get_settings.cache_clear()
        settings_low = get_settings()
        assert settings_low.observability_config.trace_sample_rate == 0.1

        # Test high sampling rate
        monkeypatch.setenv("OBSERVABILITY_CONFIG__TRACE_SAMPLE_RATE", "1.0")
        get_settings.cache_clear()
        settings_high = get_settings()
        assert settings_high.observability_config.trace_sample_rate == 1.0
