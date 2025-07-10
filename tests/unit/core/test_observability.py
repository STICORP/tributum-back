"""Unit tests for the observability module.

This module tests the distributed tracing implementation using OpenTelemetry
with support for multiple backends (Console/Loguru, GCP, AWS, OTLP).
"""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING, Any, cast

import pytest
from opentelemetry.sdk.trace.export import SpanExportResult

from src.core.context import RequestContext
from src.core.observability import (
    LoguruSpanExporter,
    _get_gcp_exporter,
    _get_otlp_exporter,
    add_correlation_id_to_span,
    add_span_attributes,
    get_span_exporter,
    get_tracer,
    instrument_app,
    setup_tracing,
    trace_operation,
)

if TYPE_CHECKING:
    from pytest_mock import MockerFixture, MockType

    from src.core.config import Settings


@pytest.mark.unit
class TestObservability:
    """Test suite for observability module."""

    # LoguruSpanExporter Tests

    def test_loguru_exporter_export_spans_successfully(
        self,
        mocker: MockerFixture,
        mock_readable_spans: list[MockType],
    ) -> None:
        """Test that spans are correctly exported through Loguru."""
        # Mock logger
        mock_logger = mocker.patch("src.core.observability.logger")
        mock_bind = mocker.Mock(return_value=mock_logger)
        mock_logger.bind = mock_bind

        # Create exporter
        exporter = LoguruSpanExporter()

        # Export spans
        result = exporter.export(mock_readable_spans)

        # Verify success
        assert result == SpanExportResult.SUCCESS

        # Verify logger.bind called for non-filtered spans (3 out of 5)
        assert mock_bind.call_count == 3

        # Check bind parameters for first non-filtered span
        first_call = mock_bind.call_args_list[0]
        bind_kwargs = first_call[1]
        assert bind_kwargs["trace_id"] == "0x0123456789abcdef0123456789abcdef"
        assert bind_kwargs["span_id"] == "0x0123456789abcdef"
        assert bind_kwargs["span_name"] == "http_request"
        assert bind_kwargs["duration_ms"] == 50  # 50ms

    @pytest.mark.parametrize(
        "span_name",
        ["connect", "http send", "http receive", "cursor.execute"],
    )
    def test_loguru_exporter_filters_noisy_spans(
        self,
        mocker: MockerFixture,
        mock_span: MockType,
        span_name: str,
    ) -> None:
        """Test that certain span names are filtered out."""
        # Mock logger
        mock_logger = mocker.patch("src.core.observability.logger")

        # Modify span name
        mock_span.name = span_name

        # Create exporter and export
        exporter = LoguruSpanExporter()
        result = exporter.export([mock_span])

        # Verify success but no logging
        assert result == SpanExportResult.SUCCESS
        mock_logger.bind.assert_not_called()

    def test_loguru_exporter_handles_missing_span_context(
        self,
        mocker: MockerFixture,
        mock_span: MockType,
    ) -> None:
        """Test graceful handling when span has no context."""
        # Mock logger
        mock_logger = mocker.patch("src.core.observability.logger")

        # Remove span context
        mock_span.get_span_context.return_value = None

        # Create exporter and export
        exporter = LoguruSpanExporter()
        result = exporter.export([mock_span])

        # Verify success but no logging
        assert result == SpanExportResult.SUCCESS
        mock_logger.bind.assert_not_called()

    @pytest.mark.parametrize(
        ("start_time", "end_time", "expected_duration"),
        [
            (1000000000, 2000000000, 1000),  # 1 second = 1000ms
            (1000000000, 1050000000, 50),  # 50ms
            (1000000000, None, None),  # No end time
            (None, 2000000000, None),  # No start time
        ],
    )
    def test_loguru_exporter_calculates_duration_correctly(
        self,
        mocker: MockerFixture,
        mock_span: MockType,
        start_time: int | None,
        end_time: int | None,
        expected_duration: int | None,
    ) -> None:
        """Test duration calculation from start/end times."""
        # Mock logger
        mock_logger = mocker.patch("src.core.observability.logger")
        mock_bind = mocker.Mock(return_value=mock_logger)
        mock_logger.bind = mock_bind

        # Set times
        mock_span.start_time = start_time
        mock_span.end_time = end_time

        # Create exporter and export
        exporter = LoguruSpanExporter()
        result = exporter.export([mock_span])

        # Verify success
        assert result == SpanExportResult.SUCCESS

        # Check duration in bind call
        if mock_bind.called:
            bind_kwargs = mock_bind.call_args[1]
            assert bind_kwargs["duration_ms"] == expected_duration

    def test_loguru_exporter_gets_correlation_id_from_context(
        self,
        mocker: MockerFixture,
        mock_span: MockType,
    ) -> None:
        """Test correlation ID is retrieved from RequestContext."""
        # Mock logger
        mock_logger = mocker.patch("src.core.observability.logger")
        mock_bind = mocker.Mock(return_value=mock_logger)
        mock_logger.bind = mock_bind

        # Set correlation ID in context
        test_correlation_id = "test-correlation-id"
        RequestContext.set_correlation_id(test_correlation_id)

        # Remove correlation_id from span attributes
        mock_span.attributes = {}

        # Create exporter and export
        exporter = LoguruSpanExporter()
        result = exporter.export([mock_span])

        # Verify success
        assert result == SpanExportResult.SUCCESS

        # Check correlation ID in bind call
        bind_kwargs = mock_bind.call_args[1]
        assert bind_kwargs["correlation_id"] == test_correlation_id

    def test_loguru_exporter_handles_large_batch(
        self,
        mocker: MockerFixture,
        mock_span_context: MockType,
    ) -> None:
        """Test exporter handles large batches efficiently."""
        # Mock logger
        mock_logger = mocker.patch("src.core.observability.logger")
        mock_bind = mocker.Mock(return_value=mock_logger)
        mock_logger.bind = mock_bind

        # Create 1000 spans
        spans = []
        for i in range(1000):
            span = mocker.Mock()
            span.name = f"span_{i}"
            span.get_span_context.return_value = mock_span_context
            span.start_time = 1000000000
            span.end_time = 2000000000
            span.attributes = {"index": i}
            span.status = mocker.Mock()
            span.status.status_code = mocker.Mock()
            span.status.status_code.name = "OK"
            span.kind = mocker.Mock()
            span.kind.name = "INTERNAL"
            spans.append(span)

        # Create exporter and export
        exporter = LoguruSpanExporter()
        result = exporter.export(spans)

        # Verify all processed
        assert result == SpanExportResult.SUCCESS
        assert mock_bind.call_count == 1000

    # get_span_exporter Tests

    @pytest.mark.parametrize("exporter_type", ["console", "Console", "CONSOLE"])
    def test_get_span_exporter_console(
        self,
        mocker: MockerFixture,
        mock_observability_settings: Settings,
        exporter_type: str,
    ) -> None:
        """Test console exporter returns LoguruSpanExporter."""
        # Mock logger
        mock_logger = mocker.patch("src.core.observability.logger")

        # Set exporter type
        mock_observability_settings.observability_config.exporter_type = cast(
            "Any", exporter_type
        )

        # Get exporter
        exporter = get_span_exporter(mock_observability_settings)

        # Verify
        assert isinstance(exporter, LoguruSpanExporter)
        mock_logger.info.assert_called_with(
            "Using Loguru span exporter for development"
        )

    def test_get_span_exporter_gcp(
        self,
        mocker: MockerFixture,
        mock_observability_settings: Settings,
    ) -> None:
        """Test GCP exporter creation via dynamic import."""
        # Mock _get_gcp_exporter
        mock_gcp_exporter = mocker.Mock()
        mock_get_gcp = mocker.patch(
            "src.core.observability._get_gcp_exporter",
            return_value=mock_gcp_exporter,
        )

        # Set exporter type
        mock_observability_settings.observability_config.exporter_type = "gcp"

        # Get exporter
        exporter = get_span_exporter(mock_observability_settings)

        # Verify
        assert exporter == mock_gcp_exporter
        mock_get_gcp.assert_called_once_with(mock_observability_settings)

    @pytest.mark.parametrize("exporter_type", ["aws", "otlp"])
    def test_get_span_exporter_aws_otlp(
        self,
        mocker: MockerFixture,
        mock_observability_settings: Settings,
        exporter_type: str,
    ) -> None:
        """Test AWS and OTLP exporters use _get_otlp_exporter."""
        # Mock _get_otlp_exporter
        mock_otlp_exporter = mocker.Mock()
        mock_get_otlp = mocker.patch(
            "src.core.observability._get_otlp_exporter",
            return_value=mock_otlp_exporter,
        )

        # Set exporter type
        mock_observability_settings.observability_config.exporter_type = cast(
            "Any", exporter_type
        )

        # Get exporter
        exporter = get_span_exporter(mock_observability_settings)

        # Verify
        assert exporter == mock_otlp_exporter
        mock_get_otlp.assert_called_once_with(
            mock_observability_settings, exporter_type
        )

    def test_get_span_exporter_none(
        self,
        mocker: MockerFixture,
        mock_observability_settings: Settings,
    ) -> None:
        """Test tracing can be explicitly disabled."""
        # Mock logger
        mock_logger = mocker.patch("src.core.observability.logger")

        # Set exporter type
        mock_observability_settings.observability_config.exporter_type = "none"

        # Get exporter
        exporter = get_span_exporter(mock_observability_settings)

        # Verify
        assert exporter is None
        mock_logger.info.assert_called_with("Tracing explicitly disabled")

    def test_get_span_exporter_unknown(
        self,
        mocker: MockerFixture,
        mock_observability_settings: Settings,
    ) -> None:
        """Test graceful handling of unknown exporter types."""
        # Mock logger
        mock_logger = mocker.patch("src.core.observability.logger")

        # Set unknown exporter type
        mock_observability_settings.observability_config.exporter_type = cast(
            "Any", "invalid"
        )

        # Get exporter
        exporter = get_span_exporter(mock_observability_settings)

        # Verify
        assert exporter is None
        mock_logger.warning.assert_called_with(
            "Unknown exporter type: invalid, disabling tracing"
        )

    # _get_gcp_exporter Tests

    def test_get_gcp_exporter_success(
        self,
        mocker: MockerFixture,
        mock_observability_settings: Settings,
    ) -> None:
        """Test successful GCP exporter creation."""
        # Mock logger
        mock_logger = mocker.patch("src.core.observability.logger")

        # Mock importlib.import_module
        mock_module = mocker.Mock()
        mock_exporter_class = mocker.Mock()
        mock_exporter_instance = mocker.Mock()
        mock_exporter_class.return_value = mock_exporter_instance
        mock_module.CloudTraceSpanExporter = mock_exporter_class

        mock_import = mocker.patch("importlib.import_module", return_value=mock_module)

        # Set project ID
        project_id = "test-project-123"
        mock_observability_settings.observability_config.gcp_project_id = project_id

        # Get exporter
        exporter = _get_gcp_exporter(mock_observability_settings)

        # Verify
        assert exporter == mock_exporter_instance
        mock_import.assert_called_once_with("opentelemetry.exporter.cloud_trace")
        mock_exporter_class.assert_called_once_with(project_id=project_id)
        mock_logger.info.assert_called_with(
            f"Using GCP Cloud Trace exporter for project {project_id}"
        )

    def test_get_gcp_exporter_project_id_from_env(
        self,
        mocker: MockerFixture,
        mock_observability_settings: Settings,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test fallback to GOOGLE_CLOUD_PROJECT env var."""
        # Mock importlib.import_module
        mock_module = mocker.Mock()
        mock_exporter_class = mocker.Mock()
        mock_exporter_instance = mocker.Mock()
        mock_exporter_class.return_value = mock_exporter_instance
        mock_module.CloudTraceSpanExporter = mock_exporter_class

        mocker.patch("importlib.import_module", return_value=mock_module)

        # No project ID in settings
        mock_observability_settings.observability_config.gcp_project_id = None

        # Set env var
        env_project_id = "env-project-456"
        monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", env_project_id)

        # Get exporter
        exporter = _get_gcp_exporter(mock_observability_settings)

        # Verify
        assert exporter == mock_exporter_instance
        mock_exporter_class.assert_called_once_with(project_id=env_project_id)

    def test_get_gcp_exporter_missing_project_id(
        self,
        mocker: MockerFixture,
        mock_observability_settings: Settings,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test error handling when no project ID available."""
        # Mock logger
        mock_logger = mocker.patch("src.core.observability.logger")

        # Mock successful import but no project ID
        mock_module = mocker.Mock()
        mocker.patch("importlib.import_module", return_value=mock_module)

        # No project ID in settings or env
        mock_observability_settings.observability_config.gcp_project_id = None
        monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)

        # Get exporter
        exporter = _get_gcp_exporter(mock_observability_settings)

        # Verify
        assert exporter is None
        mock_logger.warning.assert_called_with(
            "GCP project ID not configured, disabling tracing"
        )

    def test_get_gcp_exporter_import_error(
        self,
        mocker: MockerFixture,
        mock_observability_settings: Settings,
    ) -> None:
        """Test graceful handling when GCP package not installed."""
        # Mock logger
        mock_logger = mocker.patch("src.core.observability.logger")

        # Mock importlib.import_module to raise ImportError
        mocker.patch("importlib.import_module", side_effect=ImportError("No module"))

        # Set project ID
        mock_observability_settings.observability_config.gcp_project_id = "test-project"

        # Get exporter
        exporter = _get_gcp_exporter(mock_observability_settings)

        # Verify
        assert exporter is None
        mock_logger.error.assert_called_with(
            "GCP exporter requested but opentelemetry-exporter-gcp-trace "
            "not installed. Install with: uv add opentelemetry-exporter-gcp-trace"
        )

    # _get_otlp_exporter Tests

    @pytest.mark.parametrize(
        ("environment", "expected_insecure"),
        [
            ("development", True),
            ("staging", False),
            ("production", False),
        ],
    )
    def test_get_otlp_exporter_with_custom_endpoint(
        self,
        mocker: MockerFixture,
        mock_observability_settings: Settings,
        environment: str,
        expected_insecure: bool,
    ) -> None:
        """Test OTLP exporter uses configured endpoint."""
        # Mock OTLPSpanExporter
        mock_exporter_class = mocker.patch("src.core.observability.OTLPSpanExporter")
        mock_exporter_instance = mocker.Mock()
        mock_exporter_class.return_value = mock_exporter_instance

        # Set environment and endpoint
        mock_observability_settings.environment = cast("Any", environment)
        custom_endpoint = "http://telemetry.example.com:4317"
        mock_observability_settings.observability_config.exporter_endpoint = (
            custom_endpoint
        )

        # Get exporter
        exporter = _get_otlp_exporter(mock_observability_settings, "otlp")

        # Verify
        assert exporter == mock_exporter_instance
        mock_exporter_class.assert_called_once_with(
            endpoint=custom_endpoint,
            insecure=expected_insecure,
        )

    def test_get_otlp_exporter_default_endpoint(
        self,
        mocker: MockerFixture,
        mock_observability_settings: Settings,
    ) -> None:
        """Test default endpoint when not configured."""
        # Mock OTLPSpanExporter
        mock_exporter_class = mocker.patch("src.core.observability.OTLPSpanExporter")

        # No endpoint configured
        mock_observability_settings.observability_config.exporter_endpoint = None

        # Get exporter
        _get_otlp_exporter(mock_observability_settings, "otlp")

        # Verify default endpoint
        mock_exporter_class.assert_called_once_with(
            endpoint="http://localhost:4317",
            insecure=True,  # development environment
        )

    @pytest.mark.parametrize("exporter_type", ["aws", "otlp"])
    def test_get_otlp_exporter_logging(
        self,
        mocker: MockerFixture,
        mock_observability_settings: Settings,
        exporter_type: str,
    ) -> None:
        """Test different log messages for AWS vs OTLP."""
        # Mock logger and exporter
        mock_logger = mocker.patch("src.core.observability.logger")
        mocker.patch("src.core.observability.OTLPSpanExporter")

        # Set endpoint
        endpoint = "http://example.com:4317"
        mock_observability_settings.observability_config.exporter_endpoint = endpoint

        # Get exporter
        _get_otlp_exporter(mock_observability_settings, exporter_type)

        # Verify appropriate log message
        if exporter_type == "aws":
            mock_logger.info.assert_called_with(
                f"Using AWS X-Ray exporter via OTLP at {endpoint}"
            )
        else:
            mock_logger.info.assert_called_with(f"Using OTLP exporter at {endpoint}")

    # get_tracer Tests

    def test_get_tracer_creation_and_caching(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Test tracer is created and cached."""
        # Mock trace.get_tracer
        mock_tracer = mocker.Mock()
        mock_get_tracer = mocker.patch(
            "src.core.observability.trace.get_tracer", return_value=mock_tracer
        )

        # Get tracer multiple times
        tracer1 = get_tracer("test_component")
        tracer2 = get_tracer("test_component")
        tracer3 = get_tracer("test_component")

        # Verify
        assert tracer1 == mock_tracer
        assert tracer2 == mock_tracer
        assert tracer3 == mock_tracer
        # Should only be called once due to caching
        mock_get_tracer.assert_called_once_with("test_component")

    @pytest.mark.parametrize(
        "component_names",
        [
            ["component1", "component2", "component3"],
            ["api", "database", "cache"],
        ],
    )
    def test_get_tracer_different_names(
        self,
        mocker: MockerFixture,
        component_names: list[str],
    ) -> None:
        """Test different tracers for different component names."""
        # Mock trace.get_tracer
        mock_get_tracer = mocker.patch("src.core.observability.trace.get_tracer")

        # Get tracers for different components
        for name in component_names:
            get_tracer(name)

        # Verify each called once
        assert mock_get_tracer.call_count == len(component_names)
        for name in component_names:
            mock_get_tracer.assert_any_call(name)

    def test_get_tracer_thread_safety(
        self,
        mocker: MockerFixture,
        thread_sync: dict[str, Any],
    ) -> None:
        """Test get_tracer is thread-safe with concurrent access."""
        # Mock trace.get_tracer
        mock_tracer = mocker.Mock()
        mock_get_tracer = mocker.patch(
            "src.core.observability.trace.get_tracer", return_value=mock_tracer
        )

        # Thread synchronization
        num_threads = 10
        barrier = thread_sync["barrier"](num_threads)
        results = thread_sync["create_results"]()

        def get_tracer_thread() -> None:
            """Get tracer in thread."""
            barrier.wait()  # Synchronize all threads
            tracer = get_tracer("concurrent_component")
            results.append(tracer)

        # Create and start threads
        threads = []
        for _ in range(num_threads):
            thread = threading.Thread(target=get_tracer_thread)
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join(timeout=5)

        # Verify
        assert len(results) == num_threads
        assert all(tracer == mock_tracer for tracer in results)
        # Should only be called once despite concurrent access
        mock_get_tracer.assert_called_once_with("concurrent_component")

    # setup_tracing Tests

    def test_setup_tracing_disabled(
        self,
        mocker: MockerFixture,
        mock_observability_settings: Settings,
    ) -> None:
        """Test setup exits early when tracing disabled."""
        # Mock logger and trace
        mock_logger = mocker.patch("src.core.observability.logger")
        mock_set_tracer_provider = mocker.patch(
            "src.core.observability.trace.set_tracer_provider"
        )

        # Disable tracing
        mock_observability_settings.observability_config.enable_tracing = False

        # Setup tracing
        setup_tracing(mock_observability_settings)

        # Verify
        mock_logger.info.assert_called_with("Tracing disabled by configuration")
        mock_set_tracer_provider.assert_not_called()

    def test_setup_tracing_resource_creation(
        self,
        mocker: MockerFixture,
        mock_observability_settings: Settings,
    ) -> None:
        """Test resource created with correct attributes."""
        # Mock dependencies
        mock_resource = mocker.Mock()
        mock_resource_create = mocker.patch(
            "src.core.observability.Resource.create", return_value=mock_resource
        )
        mock_provider = mocker.Mock()
        mocker.patch(
            "src.core.observability.TracerProvider", return_value=mock_provider
        )
        mocker.patch("src.core.observability.get_span_exporter", return_value=None)
        mocker.patch("src.core.observability.trace.set_tracer_provider")

        # Set app info
        mock_observability_settings.app_name = "TestApp"
        mock_observability_settings.app_version = "1.2.3"
        mock_observability_settings.environment = "production"

        # Setup tracing
        setup_tracing(mock_observability_settings)

        # Verify resource creation
        mock_resource_create.assert_called_once_with(
            {
                "service.name": "TestApp",
                "service.version": "1.2.3",
                "deployment.environment": "production",
            }
        )

    @pytest.mark.parametrize("sample_rate", [0.0, 0.5, 1.0])
    def test_setup_tracing_provider_configuration(
        self,
        mocker: MockerFixture,
        mock_observability_settings: Settings,
        sample_rate: float,
    ) -> None:
        """Test tracer provider setup with sampling."""
        # Mock dependencies
        mock_resource = mocker.Mock()
        mocker.patch(
            "src.core.observability.Resource.create", return_value=mock_resource
        )
        mock_sampler = mocker.Mock()
        mock_sampler_class = mocker.patch(
            "src.core.observability.TraceIdRatioBased", return_value=mock_sampler
        )
        mock_provider = mocker.Mock()
        mocker.patch(
            "src.core.observability.TracerProvider", return_value=mock_provider
        )
        mocker.patch("src.core.observability.get_span_exporter", return_value=None)
        mocker.patch("src.core.observability.trace.set_tracer_provider")

        # Set sample rate
        mock_observability_settings.observability_config.trace_sample_rate = sample_rate

        # Setup tracing
        setup_tracing(mock_observability_settings)

        # Verify sampler and provider
        mock_sampler_class.assert_called_once_with(sample_rate)

    def test_setup_tracing_span_processor_addition(
        self,
        mocker: MockerFixture,
        mock_observability_settings: Settings,
    ) -> None:
        """Test span processor added when exporter available."""
        # Mock dependencies
        mock_exporter = mocker.Mock()
        mocker.patch(
            "src.core.observability.get_span_exporter", return_value=mock_exporter
        )
        mock_processor = mocker.Mock()
        mock_processor_class = mocker.patch(
            "src.core.observability.BatchSpanProcessor", return_value=mock_processor
        )
        mock_provider = mocker.Mock()
        mocker.patch(
            "src.core.observability.TracerProvider", return_value=mock_provider
        )
        mocker.patch("src.core.observability.Resource.create")
        mocker.patch("src.core.observability.trace.set_tracer_provider")

        # Setup tracing
        setup_tracing(mock_observability_settings)

        # Verify processor added
        mock_processor_class.assert_called_once_with(mock_exporter)
        mock_provider.add_span_processor.assert_called_once_with(mock_processor)

    def test_setup_tracing_no_processor_when_no_exporter(
        self,
        mocker: MockerFixture,
        mock_observability_settings: Settings,
    ) -> None:
        """Test no processor added when exporter is None."""
        # Mock dependencies
        mocker.patch("src.core.observability.get_span_exporter", return_value=None)
        mock_provider = mocker.Mock()
        mocker.patch(
            "src.core.observability.TracerProvider", return_value=mock_provider
        )
        mocker.patch("src.core.observability.Resource.create")
        mocker.patch("src.core.observability.trace.set_tracer_provider")

        # Setup tracing
        setup_tracing(mock_observability_settings)

        # Verify no processor added
        mock_provider.add_span_processor.assert_not_called()

    def test_setup_tracing_resource_creation_failure(
        self,
        mocker: MockerFixture,
        mock_observability_settings: Settings,
    ) -> None:
        """Test handling when Resource.create fails."""
        # Mock logger
        mocker.patch("src.core.observability.logger")

        # Mock Resource.create to raise exception
        mocker.patch(
            "src.core.observability.Resource.create",
            side_effect=Exception("Resource creation failed"),
        )

        # Setup tracing doesn't handle Resource.create failures, so it will raise
        with pytest.raises(Exception, match="Resource creation failed"):
            setup_tracing(mock_observability_settings)

    def test_setup_tracing_concurrent_calls(
        self,
        mocker: MockerFixture,
        mock_observability_settings: Settings,
        thread_sync: dict[str, Any],
    ) -> None:
        """Test setup_tracing handles concurrent initialization."""
        # Mock dependencies
        mock_set_tracer_provider = mocker.patch(
            "src.core.observability.trace.set_tracer_provider"
        )
        mocker.patch("src.core.observability.Resource.create")
        mocker.patch("src.core.observability.TracerProvider")
        mocker.patch("src.core.observability.get_span_exporter", return_value=None)

        # Thread synchronization
        num_threads = 5
        barrier = thread_sync["barrier"](num_threads)
        errors = thread_sync["create_results"]()

        def setup_thread() -> None:
            """Setup tracing in thread."""
            try:
                barrier.wait()
                setup_tracing(mock_observability_settings)
            except Exception as e:
                errors.append(e)

        # Create and start threads
        threads = []
        for _ in range(num_threads):
            thread = threading.Thread(target=setup_thread)
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join(timeout=5)

        # Verify no errors and provider set multiple times is OK
        assert len(errors) == 0
        assert mock_set_tracer_provider.call_count == num_threads

    # instrument_app Tests

    def test_instrument_app_disabled(
        self,
        mocker: MockerFixture,
        mock_observability_settings: Settings,
        mock_fastapi_app: MockType,
    ) -> None:
        """Test no instrumentation when tracing disabled."""
        # Mock instrumentors
        mock_fastapi_instrumentor = mocker.patch(
            "src.core.observability.FastAPIInstrumentor"
        )

        # Disable tracing
        mock_observability_settings.observability_config.enable_tracing = False

        # Instrument app
        instrument_app(mock_fastapi_app, mock_observability_settings)

        # Verify no instrumentation
        mock_fastapi_instrumentor.instrument_app.assert_not_called()

    def test_instrument_app_fastapi(
        self,
        mocker: MockerFixture,
        mock_observability_settings: Settings,
        mock_fastapi_app: MockType,
    ) -> None:
        """Test FastAPI app is instrumented correctly."""
        # Mock logger and instrumentor
        mock_logger = mocker.patch("src.core.observability.logger")
        mock_fastapi_instrumentor = mocker.patch(
            "src.core.observability.FastAPIInstrumentor"
        )

        # Instrument app
        instrument_app(mock_fastapi_app, mock_observability_settings)

        # Verify instrumentation
        mock_fastapi_instrumentor.instrument_app.assert_called_once_with(
            mock_fastapi_app,
            excluded_urls="/health,/metrics,/docs,/redoc,/openapi.json",
            server_request_hook=add_correlation_id_to_span,
        )
        mock_logger.info.assert_called_with("Application instrumented for tracing")

    def test_instrument_app_sqlalchemy(
        self,
        mocker: MockerFixture,
        mock_observability_settings: Settings,
        mock_fastapi_app: MockType,
    ) -> None:
        """Test SQLAlchemy instrumented when database configured."""
        # Mock instrumentors
        mocker.patch("src.core.observability.FastAPIInstrumentor")
        mock_sqlalchemy_instrumentor = mocker.patch(
            "src.core.observability.SQLAlchemyInstrumentor"
        )
        mock_instance = mocker.Mock()
        mock_sqlalchemy_instrumentor.return_value = mock_instance

        # Ensure database_config exists
        mock_observability_settings.database_config = mocker.Mock()

        # Instrument app
        instrument_app(mock_fastapi_app, mock_observability_settings)

        # Verify SQLAlchemy instrumentation
        mock_instance.instrument.assert_called_once_with(
            enable_commenter=True,
            commenter_options={
                "opentelemetry_values": True,
            },
        )

    def test_instrument_app_no_sqlalchemy_without_database(
        self,
        mocker: MockerFixture,
        mock_observability_settings: Settings,
        mock_fastapi_app: MockType,
    ) -> None:
        """Test SQLAlchemy not instrumented without database."""
        # Mock instrumentors
        mocker.patch("src.core.observability.FastAPIInstrumentor")
        mock_sqlalchemy_instrumentor = mocker.patch(
            "src.core.observability.SQLAlchemyInstrumentor"
        )

        # No database config
        mock_observability_settings.database_config = cast("Any", None)

        # Instrument app
        instrument_app(mock_fastapi_app, mock_observability_settings)

        # Verify no SQLAlchemy instrumentation
        mock_sqlalchemy_instrumentor.assert_not_called()

    def test_instrument_app_httpx_available(
        self,
        mocker: MockerFixture,
        mock_observability_settings: Settings,
        mock_fastapi_app: MockType,
    ) -> None:
        """Test HTTPX instrumentation when library is available."""
        # Mock logger and instrumentors
        mock_logger = mocker.patch("src.core.observability.logger")
        mocker.patch("src.core.observability.FastAPIInstrumentor")

        # Mock importlib to simulate HTTPX availability
        mock_find_spec = mocker.patch("src.core.observability.importlib.util.find_spec")

        def httpx_spec_side_effect(name: str | None) -> bool:
            return name in ["httpx", "opentelemetry.instrumentation.httpx"]

        mock_find_spec.side_effect = httpx_spec_side_effect

        # Mock importlib.import_module for HTTPX
        mock_httpx_module = mocker.Mock()
        mock_httpx_instrumentor = mocker.Mock()
        mock_httpx_module.HTTPXClientInstrumentor.return_value = mock_httpx_instrumentor

        mock_import_module = mocker.patch(
            "src.core.observability.importlib.import_module"
        )
        mock_import_module.return_value = mock_httpx_module

        # Instrument app
        instrument_app(mock_fastapi_app, mock_observability_settings)

        # Verify HTTPX instrumentation
        mock_import_module.assert_any_call("opentelemetry.instrumentation.httpx")
        mock_httpx_module.HTTPXClientInstrumentor.assert_called_once()
        mock_httpx_instrumentor.instrument.assert_called_once()
        mock_logger.info.assert_any_call("HTTPX client instrumented for tracing")

    def test_instrument_app_requests_available(
        self,
        mocker: MockerFixture,
        mock_observability_settings: Settings,
        mock_fastapi_app: MockType,
    ) -> None:
        """Test Requests instrumentation when library is available."""
        # Mock logger and instrumentors
        mock_logger = mocker.patch("src.core.observability.logger")
        mocker.patch("src.core.observability.FastAPIInstrumentor")

        # Mock importlib to simulate Requests availability
        mock_find_spec = mocker.patch("src.core.observability.importlib.util.find_spec")

        def requests_spec_side_effect(name: str | None) -> bool:
            return name in ["requests", "opentelemetry.instrumentation.requests"]

        mock_find_spec.side_effect = requests_spec_side_effect

        # Mock importlib.import_module for Requests
        mock_requests_module = mocker.Mock()
        mock_requests_instrumentor = mocker.Mock()
        mock_requests_module.RequestsInstrumentor.return_value = (
            mock_requests_instrumentor
        )

        mock_import_module = mocker.patch(
            "src.core.observability.importlib.import_module"
        )
        mock_import_module.return_value = mock_requests_module

        # Instrument app
        instrument_app(mock_fastapi_app, mock_observability_settings)

        # Verify Requests instrumentation
        mock_import_module.assert_any_call("opentelemetry.instrumentation.requests")
        mock_requests_module.RequestsInstrumentor.assert_called_once()
        mock_requests_instrumentor.instrument.assert_called_once()
        mock_logger.info.assert_any_call("Requests client instrumented for tracing")

    def test_instrument_app_http_clients_not_available(
        self,
        mocker: MockerFixture,
        mock_observability_settings: Settings,
        mock_fastapi_app: MockType,
    ) -> None:
        """Test graceful handling when HTTP client libraries are not available."""
        # Mock logger and instrumentors
        mock_logger = mocker.patch("src.core.observability.logger")
        mocker.patch("src.core.observability.FastAPIInstrumentor")

        # Mock importlib to simulate libraries not available
        mock_find_spec = mocker.patch("src.core.observability.importlib.util.find_spec")
        mock_find_spec.return_value = None  # Libraries not found

        mock_import_module = mocker.patch(
            "src.core.observability.importlib.import_module"
        )

        # Instrument app
        instrument_app(mock_fastapi_app, mock_observability_settings)

        # Verify no HTTP client instrumentation attempted
        mock_import_module.assert_not_called()
        # Should only log the final "Application instrumented" message
        mock_logger.info.assert_called_with("Application instrumented for tracing")

    def test_instrument_app_http_import_error(
        self,
        mocker: MockerFixture,
        mock_observability_settings: Settings,
        mock_fastapi_app: MockType,
    ) -> None:
        """Test graceful handling when import fails after spec check passes."""
        # Mock logger and instrumentors
        mock_logger = mocker.patch("src.core.observability.logger")
        mocker.patch("src.core.observability.FastAPIInstrumentor")

        # Mock importlib to simulate library available but import fails
        mock_find_spec = mocker.patch("src.core.observability.importlib.util.find_spec")

        def httpx_import_error_spec_side_effect(name: str | None) -> bool:
            return name in ["httpx", "opentelemetry.instrumentation.httpx"]

        mock_find_spec.side_effect = httpx_import_error_spec_side_effect

        # Mock import_module to raise ImportError
        mock_import_module = mocker.patch(
            "src.core.observability.importlib.import_module"
        )
        mock_import_module.side_effect = ImportError("Module not found")

        # Instrument app - should not raise exception
        instrument_app(mock_fastapi_app, mock_observability_settings)

        # Verify import was attempted but failed gracefully
        mock_import_module.assert_called_once_with(
            "opentelemetry.instrumentation.httpx"
        )
        # Should still log the final message
        mock_logger.info.assert_called_with("Application instrumented for tracing")

    def test_instrument_app_requests_import_error(
        self,
        mocker: MockerFixture,
        mock_observability_settings: Settings,
        mock_fastapi_app: MockType,
    ) -> None:
        """Test graceful handling when Requests import fails after spec check passes."""
        # Mock logger and instrumentors
        mock_logger = mocker.patch("src.core.observability.logger")
        mocker.patch("src.core.observability.FastAPIInstrumentor")
        # Mock importlib to simulate Requests library available but import fails
        mock_find_spec = mocker.patch("src.core.observability.importlib.util.find_spec")

        def requests_import_error_spec_side_effect(name: str | None) -> bool:
            return name in ["requests", "opentelemetry.instrumentation.requests"]

        mock_find_spec.side_effect = requests_import_error_spec_side_effect
        # Mock import_module to raise ImportError only for Requests
        mock_import_module = mocker.patch(
            "src.core.observability.importlib.import_module"
        )
        mock_import_module.side_effect = ImportError("Requests module not found")
        # Instrument app - should not raise exception
        instrument_app(mock_fastapi_app, mock_observability_settings)
        # Verify import was attempted but failed gracefully
        mock_import_module.assert_called_once_with(
            "opentelemetry.instrumentation.requests"
        )
        # Should still log the final message
        mock_logger.info.assert_called_with("Application instrumented for tracing")

    # add_correlation_id_to_span Tests

    def test_add_correlation_id_from_context(
        self,
        mock_span: MockType,
        mock_asgi_scope: dict[str, Any],
    ) -> None:
        """Test correlation ID added to span from RequestContext."""
        # Set correlation ID in context
        test_correlation_id = "ctx-correlation-123"
        RequestContext.set_correlation_id(test_correlation_id)

        # Add correlation ID to span
        add_correlation_id_to_span(mock_span, mock_asgi_scope)

        # Verify
        mock_span.set_attribute.assert_any_call("correlation_id", test_correlation_id)

    def test_add_request_id_from_headers(
        self,
        mock_span: MockType,
        mock_asgi_scope: dict[str, Any],
    ) -> None:
        """Test request ID extracted from headers."""
        # Add correlation ID to span
        add_correlation_id_to_span(mock_span, mock_asgi_scope)

        # Verify request ID from headers
        mock_span.set_attribute.assert_any_call("request_id", "req_12345")

    def test_add_correlation_id_handles_missing_values(
        self,
        mock_span: MockType,
    ) -> None:
        """Test no errors when values missing."""
        # Empty scope with no headers
        empty_scope: dict[str, Any] = {"headers": []}

        # Should not raise any errors
        add_correlation_id_to_span(mock_span, empty_scope)

        # Verify no correlation_id call (since context is empty)
        correlation_calls = [
            call
            for call in mock_span.set_attribute.call_args_list
            if call[0][0] == "correlation_id"
        ]
        assert len(correlation_calls) == 0

    # add_span_attributes Tests

    @pytest.mark.parametrize(
        "attributes",
        [
            {"key": "value"},
            {"user_id": 123, "action": "create"},
            {"rate": 0.95, "enabled": True},
        ],
    )
    def test_add_span_attributes_recording_span(
        self,
        mocker: MockerFixture,
        mock_span: MockType,
        attributes: dict[str, Any],
    ) -> None:
        """Test attributes added to current span."""
        # Mock get_current_span
        mocker.patch(
            "src.core.observability.trace.get_current_span", return_value=mock_span
        )

        # Add attributes
        add_span_attributes(**attributes)

        # Verify all attributes added as strings
        for key, value in attributes.items():
            mock_span.set_attribute.assert_any_call(key, str(value))

    def test_add_span_attributes_non_recording_span(
        self,
        mocker: MockerFixture,
        mock_span: MockType,
    ) -> None:
        """Test no attributes added to non-recording span."""
        # Make span non-recording
        mock_span.is_recording.return_value = False

        # Mock get_current_span
        mocker.patch(
            "src.core.observability.trace.get_current_span", return_value=mock_span
        )

        # Add attributes
        add_span_attributes(test="value")

        # Verify no attributes added
        mock_span.set_attribute.assert_not_called()

    def test_add_span_attributes_no_current_span(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Test graceful handling when no span active."""
        # Mock get_current_span to return None
        mocker.patch("src.core.observability.trace.get_current_span", return_value=None)

        # Should not raise any errors
        add_span_attributes(test="value")

    # trace_operation Context Manager Tests

    def test_trace_operation_basic_span_creation(
        self,
        mocker: MockerFixture,
        mock_tracer: MockType,
        mock_span: MockType,
    ) -> None:
        """Test context manager creates and ends span."""
        # Mock get_tracer and use_span
        mocker.patch("src.core.observability.get_tracer", return_value=mock_tracer)
        mock_use_span = mocker.patch("src.core.observability.trace.use_span")

        # Use trace_operation
        with trace_operation("test_operation") as span:
            assert span == mock_span

        # Verify
        mock_tracer.start_span.assert_called_once_with("test_operation")
        mock_use_span.assert_called_once_with(mock_span, end_on_exit=True)

    @pytest.mark.parametrize(
        "attributes",
        [
            {"user_id": "123"},
            {"http_method": "POST", "path": "/api/test"},
            {"count": 42, "success": True},
        ],
    )
    def test_trace_operation_initial_attributes(
        self,
        mocker: MockerFixture,
        mock_tracer: MockType,
        mock_span: MockType,
        attributes: dict[str, Any],
    ) -> None:
        """Test attributes passed to trace_operation are set."""
        # Mock get_tracer
        mocker.patch("src.core.observability.get_tracer", return_value=mock_tracer)
        mocker.patch("src.core.observability.trace.use_span")

        # Use trace_operation with attributes
        with trace_operation("test_op", **attributes):
            pass

        # Verify attributes set as strings
        for key, value in attributes.items():
            mock_span.set_attribute.assert_any_call(key, str(value))

    def test_trace_operation_correlation_id_addition(
        self,
        mocker: MockerFixture,
        mock_tracer: MockType,
        mock_span: MockType,
    ) -> None:
        """Test correlation ID automatically added."""
        # Mock get_tracer
        mocker.patch("src.core.observability.get_tracer", return_value=mock_tracer)
        mocker.patch("src.core.observability.trace.use_span")

        # Set correlation ID
        test_correlation_id = "trace-corr-456"
        RequestContext.set_correlation_id(test_correlation_id)

        # Use trace_operation
        with trace_operation("test_op"):
            pass

        # Verify correlation ID added
        mock_span.set_attribute.assert_any_call("correlation_id", test_correlation_id)

    def test_trace_operation_exception_propagation(
        self,
        mocker: MockerFixture,
        mock_tracer: MockType,
        mock_span: MockType,
    ) -> None:
        """Test exceptions propagate correctly."""
        # Mock get_tracer and use_span
        mocker.patch("src.core.observability.get_tracer", return_value=mock_tracer)
        mock_use_span = mocker.patch("src.core.observability.trace.use_span")

        # Use trace_operation with exception
        with (
            pytest.raises(ValueError, match="Test error"),
            trace_operation("failing_op"),
        ):
            raise ValueError("Test error")

        # Verify span still managed properly
        mock_use_span.assert_called_once_with(mock_span, end_on_exit=True)

    # Edge Case Tests

    def test_span_attribute_type_handling(
        self,
        mocker: MockerFixture,
        mock_span_context: MockType,
    ) -> None:
        """Test span attributes handle all OpenTelemetry attribute types."""
        # Mock logger
        mock_logger = mocker.patch("src.core.observability.logger")
        mock_bind = mocker.Mock(return_value=mock_logger)
        mock_logger.bind = mock_bind

        # Create span with various attribute types
        span = mocker.Mock()
        span.name = "test_span"
        span.get_span_context.return_value = mock_span_context
        span.start_time = 1000000000
        span.end_time = 2000000000
        span.attributes = {
            "str_attr": "value",
            "int_attr": 42,
            "float_attr": 3.14,
            "bool_attr": True,
            "none_attr": None,
            "list_attr": [1, 2, 3],
            "dict_attr": {"nested": "value"},
        }
        span.status = mocker.Mock()
        span.status.status_code = mocker.Mock()
        span.status.status_code.name = "OK"
        span.kind = mocker.Mock()
        span.kind.name = "INTERNAL"

        # Export span
        exporter = LoguruSpanExporter()
        result = exporter.export([span])

        # Verify success and attributes passed through
        assert result == SpanExportResult.SUCCESS
        bind_kwargs = mock_bind.call_args[1]
        assert bind_kwargs["attributes"] == span.attributes
