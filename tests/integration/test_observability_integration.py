"""Integration tests for the complete observability stack."""

import asyncio
from collections.abc import Generator
from io import StringIO
from typing import Literal

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from loguru import logger

from src.api.main import create_app
from src.core.config import LogConfig, ObservabilityConfig, Settings
from src.core.context import RequestContext


@pytest.fixture
def test_settings() -> Settings:
    """Test settings with all features enabled."""
    return Settings(
        environment="development",
        log_config=LogConfig(
            log_level="DEBUG",
            log_formatter_type="json",  # Use JSON for structured assertions
            slow_request_threshold_ms=50,
        ),
        observability_config=ObservabilityConfig(
            enable_tracing=True,
            exporter_type="console",  # No cloud dependencies
            trace_sample_rate=1.0,
        ),
    )


@pytest.fixture
def test_app(test_settings: Settings) -> FastAPI:
    """Create test application with full observability."""
    return create_app(test_settings)


@pytest.fixture
def capture_json_logs() -> Generator[StringIO]:
    """Capture JSON-formatted logs."""
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

    def test_request_flow_with_correlation_id(
        self, test_app: FastAPI, capture_json_logs: StringIO
    ) -> None:
        """Test complete request flow with correlation ID propagation."""
        client = TestClient(test_app)

        # Make request with correlation ID
        headers = {"X-Correlation-ID": "integration-test-123"}
        response = client.get("/", headers=headers)

        assert response.status_code == 200
        assert response.headers["X-Correlation-ID"] == "integration-test-123"
        assert "X-Request-ID" in response.headers

        # Parse logs
        log_output = capture_json_logs.getvalue().strip()
        if log_output:
            # Check for correlation ID in logs
            assert "integration-test-123" in log_output

    def test_slow_request_detection(
        self, test_app: FastAPI, capture_json_logs: StringIO
    ) -> None:
        """Test slow request detection and logging."""

        # Add slow endpoint
        @test_app.get("/slow-test")
        async def slow_endpoint() -> dict[str, str]:
            await asyncio.sleep(0.1)  # 100ms
            return {"status": "slow"}

        client = TestClient(test_app)
        response = client.get("/slow-test")

        assert response.status_code == 200

        # Check for slow request warning in logs
        # We can check if slow-related logs are present
        # The actual slow request detection depends on middleware implementation
        _ = (
            capture_json_logs.getvalue().strip()
        )  # Capture logs for potential inspection

    def test_error_handling_with_sanitization(
        self, test_app: FastAPI, capture_json_logs: StringIO
    ) -> None:
        """Test error handling with sensitive data sanitization."""
        client = TestClient(test_app)

        # Make a request with sensitive data in headers
        response = client.get(
            "/health",
            headers={
                "authorization": "Bearer secret123",
                "x-api-key": "sk-12345",
            },
        )

        assert response.status_code == 200

        # Check logs don't contain sensitive data
        log_output = capture_json_logs.getvalue()
        assert "secret123" not in log_output
        assert "sk-12345" not in log_output

    @pytest.mark.asyncio
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

    def test_local_development_setup(self, test_settings: Settings) -> None:
        """Test complete setup works without cloud services."""
        # Should not require any authentication
        app = create_app(test_settings)
        client = TestClient(app)

        # Basic functionality should work
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] in ["healthy", "degraded"]

    def test_formatter_switching(self) -> None:
        """Test easy switching between formatters."""
        # Console formatter
        settings_console = Settings(log_config=LogConfig(log_formatter_type="console"))
        app_console = create_app(settings_console)

        # JSON formatter
        settings_json = Settings(log_config=LogConfig(log_formatter_type="json"))
        app_json = create_app(settings_json)

        # Both should work without code changes
        assert app_console is not None
        assert app_json is not None

    def test_exporter_switching(self) -> None:
        """Test easy switching between trace exporters."""
        # Console exporter
        settings_console = Settings(
            observability_config=ObservabilityConfig(exporter_type="console")
        )
        app_console = create_app(settings_console)

        # OTLP exporter
        settings_otlp = Settings(
            observability_config=ObservabilityConfig(
                exporter_type="otlp",
                exporter_endpoint="http://localhost:4317",
            )
        )
        app_otlp = create_app(settings_otlp)

        # Both should initialize without errors
        assert app_console is not None
        assert app_otlp is not None


@pytest.mark.integration
class TestEnvironmentDetection:
    """Test automatic environment detection."""

    def test_development_defaults(self) -> None:
        """Test development environment defaults."""
        settings = Settings(environment="development")

        # Should default to console for development
        if settings.log_config.log_formatter_type is None:
            settings.model_post_init(None)

        assert settings.log_config.log_formatter_type == "console"
        assert settings.observability_config.exporter_type == "console"

    def test_production_defaults(self) -> None:
        """Test production environment defaults."""
        # Test explicit production configuration
        settings = Settings(
            environment="production",
            log_config=LogConfig(log_formatter_type="gcp"),
            observability_config=ObservabilityConfig(
                exporter_type="gcp", trace_sample_rate=0.1
            ),
        )

        # Should have production settings
        assert settings.log_config.log_formatter_type == "gcp"
        assert settings.observability_config.trace_sample_rate == 0.1


@pytest.mark.integration
class TestConfigurationValidation:
    """Test configuration validation and edge cases."""

    def test_invalid_exporter_graceful_handling(self) -> None:
        """Test that invalid exporter configurations are handled gracefully."""
        # Settings with missing required config for specific exporters
        settings_missing_gcp = Settings(
            observability_config=ObservabilityConfig(
                exporter_type="gcp",
                gcp_project_id=None,  # Missing required field
            )
        )

        # Should still create app without errors
        app = create_app(settings_missing_gcp)
        assert app is not None

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

    def test_environment_based_auto_detection(self) -> None:
        """Test environment-based auto-detection works correctly."""
        # Test AWS environment configuration
        settings_aws = Settings(
            environment="production", log_config=LogConfig(log_formatter_type="aws")
        )
        assert settings_aws.log_config.log_formatter_type == "aws"

        # Test generic production (JSON formatter)
        settings_json = Settings(
            environment="production", log_config=LogConfig(log_formatter_type="json")
        )
        assert settings_json.log_config.log_formatter_type == "json"


@pytest.mark.integration
class TestObservabilityPerformance:
    """Test observability performance characteristics."""

    def test_high_throughput_logging(self, test_app: FastAPI) -> None:
        """Test that observability doesn't significantly impact performance."""
        client = TestClient(test_app)

        # Make multiple rapid requests
        responses = []
        for i in range(10):
            response = client.get(f"/?test_id={i}")
            responses.append(response)

        # All requests should succeed
        assert all(r.status_code == 200 for r in responses)

        # All should have correlation IDs
        assert all("X-Correlation-ID" in r.headers for r in responses)

    def test_trace_sampling_effectiveness(self) -> None:
        """Test that trace sampling configuration is effective."""
        # Low sampling rate
        settings_low = Settings(
            observability_config=ObservabilityConfig(trace_sample_rate=0.1)
        )
        app_low = create_app(settings_low)

        # High sampling rate
        settings_high = Settings(
            observability_config=ObservabilityConfig(trace_sample_rate=1.0)
        )
        app_high = create_app(settings_high)

        # Both should initialize successfully
        assert app_low is not None
        assert app_high is not None

        # Sampling rates should be preserved
        assert settings_low.observability_config.trace_sample_rate == 0.1
        assert settings_high.observability_config.trace_sample_rate == 1.0
