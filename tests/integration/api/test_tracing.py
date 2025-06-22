"""Integration tests for OpenTelemetry tracing with FastAPI."""

import asyncio
import importlib
from collections.abc import Sequence
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult
from pytest_mock import MockerFixture

import src.api.main
from src.api.main import _add_correlation_id_to_span, create_app, lifespan
from src.core.config import ObservabilityConfig, Settings
from src.core.context import CORRELATION_ID_HEADER, RequestContext


class InMemorySpanExporter(SpanExporter):
    """In-memory span exporter for testing."""

    def __init__(self) -> None:
        """Initialize the exporter with an empty spans list."""
        self.spans: list[Any] = []

    def export(self, spans: Sequence[Any]) -> SpanExportResult:
        """Export spans to memory.

        Args:
            spans: The spans to export

        Returns:
            SpanExportResult: The result of the export operation
        """
        self.spans.extend(spans)
        return SpanExportResult.SUCCESS

    def shutdown(self) -> None:
        """Shutdown the exporter."""

    def clear(self) -> None:
        """Clear all recorded spans."""
        self.spans.clear()


@pytest.mark.integration
class TestTracingConfiguration:
    """Test cases for tracing configuration."""

    async def test_tracing_disabled(self, mocker: MockerFixture) -> None:
        """Test that tracing can be disabled via configuration."""
        # Create app with tracing disabled
        obs_config = ObservabilityConfig(
            enable_tracing=False,
            service_name="test-service",
        )
        settings = Settings(observability_config=obs_config)

        # Mock to verify set_tracer_provider is not called
        mock_set_provider = mocker.patch("opentelemetry.trace.set_tracer_provider")

        app = create_app(settings)

        # Verify tracing setup was skipped
        mock_set_provider.assert_not_called()

        # Make a request to ensure app works without tracing
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/")
            assert response.status_code == 200


@pytest.mark.integration
class TestCorrelationIdToSpan:
    """Test cases for _add_correlation_id_to_span function."""

    def test_add_correlation_id_to_span_with_id(self, mocker: MockerFixture) -> None:
        """Test that correlation ID is added to span when available."""
        # Mock span
        mock_span = mocker.Mock()

        # Set a correlation ID in context
        test_correlation_id = "test-corr-123"
        RequestContext.set_correlation_id(test_correlation_id)

        # Call the function
        _add_correlation_id_to_span(mock_span, {})

        # Verify attributes were set
        mock_span.set_attribute.assert_any_call("correlation_id", test_correlation_id)
        mock_span.set_attribute.assert_any_call(
            "tributum.correlation_id", test_correlation_id
        )
        assert mock_span.set_attribute.call_count == 2

        # Clean up
        RequestContext.clear()

    def test_add_correlation_id_to_span_without_id(self, mocker: MockerFixture) -> None:
        """Test that function handles missing correlation ID gracefully."""
        # Ensure no correlation ID is set
        RequestContext.clear()

        # Mock span
        mock_span = mocker.Mock()

        # Call the function
        _add_correlation_id_to_span(mock_span, {})

        # Verify no attributes were set
        mock_span.set_attribute.assert_not_called()

    def test_add_correlation_id_to_span_with_path(self, mocker: MockerFixture) -> None:
        """Test that request path is added to span when available."""
        # Mock span
        mock_span = mocker.Mock()

        # Call the function with request scope containing path
        request_scope = {"path": "/api/v1/test"}
        _add_correlation_id_to_span(mock_span, request_scope)

        # Verify path attribute was set
        mock_span.set_attribute.assert_any_call("http.target", "/api/v1/test")


@pytest.mark.integration
class TestTracingIntegration:
    """Test cases for tracing integration with FastAPI.

    Note: These tests verify that the tracing setup works correctly,
    but actual span capture testing requires a full OpenTelemetry setup
    which is complex to mock properly. In a real environment, spans would
    be exported to GCP Cloud Trace.
    """

    async def test_tracing_setup_called_on_startup(self, mocker: MockerFixture) -> None:
        """Test that setup_tracing is called on application startup."""
        # Mock setup_tracing
        mock_setup_tracing = mocker.patch("src.api.main.setup_tracing")

        # Create app with tracing enabled
        obs_config = ObservabilityConfig(
            enable_tracing=True,
            service_name="test-service",
            trace_sample_rate=1.0,
        )
        settings = Settings(observability_config=obs_config)

        # Create app which triggers lifespan
        app = create_app(settings)

        # Simulate startup by using the lifespan context manager directly
        async with lifespan(app):
            # Verify setup_tracing was called during startup
            mock_setup_tracing.assert_called_once()

    async def test_correlation_id_propagation(self) -> None:
        """Test that correlation ID is properly propagated in responses."""
        # Create app
        app = create_app()

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Test with provided correlation ID
            correlation_id = "test-correlation-123"
            response = await client.get(
                "/", headers={CORRELATION_ID_HEADER: correlation_id}
            )
            assert response.status_code == 200
            assert response.headers[CORRELATION_ID_HEADER] == correlation_id

            # Test without correlation ID - should generate one
            response = await client.get("/")
            assert response.status_code == 200
            assert CORRELATION_ID_HEADER in response.headers
            # Should be a valid UUID
            generated_id = response.headers[CORRELATION_ID_HEADER]
            assert len(generated_id) == 36
            assert generated_id.count("-") == 4

    async def test_multiple_concurrent_requests_correlation_ids(self) -> None:
        """Test that concurrent requests maintain separate correlation IDs."""
        app = create_app()

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Make multiple concurrent requests with different correlation IDs
            correlation_ids = ["corr-1", "corr-2", "corr-3"]

            async def make_request(correlation_id: str) -> str:
                """Make a request and return the response correlation ID."""
                response = await client.get(
                    "/", headers={CORRELATION_ID_HEADER: correlation_id}
                )
                return response.headers[CORRELATION_ID_HEADER]

            # Execute requests concurrently
            results = await asyncio.gather(
                *[make_request(cid) for cid in correlation_ids]
            )

            # Verify each request maintained its correlation ID
            assert results == correlation_ids

    async def test_excluded_urls_configuration(self) -> None:
        """Test that docs endpoints are accessible (excluded from tracing)."""
        app = create_app()

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Test excluded URLs still work
            excluded_urls = ["/docs", "/redoc", "/openapi.json"]
            for url in excluded_urls:
                response = await client.get(url)
                assert response.status_code == 200

    async def test_instrumentor_setup(self, mocker: MockerFixture) -> None:
        """Test that FastAPIInstrumentor is properly configured."""
        # Mock the instrumentor
        mock_instrument = mocker.patch.object(FastAPIInstrumentor, "instrument_app")

        # Import and execute the module-level instrumentation
        # This simulates what happens when the module is imported
        importlib.reload(src.api.main)

        # Verify instrument_app was called
        assert mock_instrument.called
        call_kwargs = mock_instrument.call_args.kwargs

        # Verify excluded URLs configuration
        assert "excluded_urls" in call_kwargs
        assert "/docs" in call_kwargs["excluded_urls"]
        assert "/redoc" in call_kwargs["excluded_urls"]
        assert "/openapi.json" in call_kwargs["excluded_urls"]

        # Verify server_request_hook is set
        assert "server_request_hook" in call_kwargs
        assert (
            call_kwargs["server_request_hook"].__name__ == "_add_correlation_id_to_span"
        )

    async def test_observability_configuration(self, mocker: MockerFixture) -> None:
        """Test that observability configuration is properly passed to setup."""
        # Create app with specific observability config
        obs_config = ObservabilityConfig(
            enable_tracing=True,
            service_name="test-service",
            trace_sample_rate=0.5,
            gcp_project_id=None,
        )
        settings = Settings(observability_config=obs_config)

        # Mock get_settings to return our custom settings
        mocker.patch("src.core.observability.get_settings", return_value=settings)

        # Mock the observability setup components
        mock_resource_instance = mocker.Mock()
        mock_resource = mocker.patch("src.core.observability.Resource")
        mock_resource.create.return_value = mock_resource_instance

        mock_provider_class = mocker.patch("src.core.observability.TracerProvider")
        mock_trace = mocker.patch("src.core.observability.trace")
        mock_sampler = mocker.patch("src.core.observability.TraceIdRatioBased")

        # Create mock instances
        mock_provider = mocker.Mock()
        mock_provider_class.return_value = mock_provider
        mock_sampler_instance = mocker.Mock()
        mock_sampler.return_value = mock_sampler_instance

        app = create_app(settings)

        # Trigger startup using lifespan
        async with lifespan(app):
            # Verify resource creation with service info
            mock_resource.create.assert_called_once()
            resource_attrs = mock_resource.create.call_args[0][0]
            assert resource_attrs["service.name"] == "test-service"
            assert resource_attrs["service.version"] == settings.app_version
            assert resource_attrs["deployment.environment"] == settings.environment

            # Verify sampler configuration
            mock_sampler.assert_called_once_with(0.5)

            # Verify tracer provider was created with correct arguments
            mock_provider_class.assert_called_once_with(
                resource=mock_resource_instance, sampler=mock_sampler_instance
            )

            # Verify tracer provider was set
            mock_trace.set_tracer_provider.assert_called_once_with(mock_provider)
