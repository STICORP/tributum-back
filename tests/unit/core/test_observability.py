"""Tests for simplified observability implementation."""

from unittest.mock import Mock

import pytest
from fastapi import FastAPI
from opentelemetry.sdk.trace.export import SpanExportResult
from pytest_mock import MockerFixture

from src.core.config import ObservabilityConfig, Settings
from src.core.context import RequestContext
from src.core.observability import (
    LoguruSpanExporter,
    add_correlation_id_to_span,
    add_span_attributes,
    get_span_exporter,
    get_tracer,
    instrument_app,
    setup_tracing,
    trace_operation,
)


@pytest.mark.unit
class TestExporterSelection:
    """Test exporter selection logic."""

    def test_console_exporter(self) -> None:
        """Test console exporter for development."""
        settings = Settings(
            observability_config=ObservabilityConfig(
                enable_tracing=True,
                exporter_type="console",
            )
        )

        exporter = get_span_exporter(settings)
        assert exporter is not None
        assert exporter.__class__.__name__ == "LoguruSpanExporter"

    def test_none_exporter(self) -> None:
        """Test explicitly disabled tracing."""
        settings = Settings(
            observability_config=ObservabilityConfig(
                enable_tracing=True,
                exporter_type="none",
            )
        )

        exporter = get_span_exporter(settings)
        assert exporter is None

    def test_otlp_exporter(self, mocker: MockerFixture) -> None:
        """Test OTLP exporter configuration."""
        mock_otlp = mocker.patch("src.core.observability.OTLPSpanExporter")
        settings = Settings(
            observability_config=ObservabilityConfig(
                enable_tracing=True,
                exporter_type="otlp",
                exporter_endpoint="http://jaeger:4317",
            )
        )

        get_span_exporter(settings)

        mock_otlp.assert_called_once_with(
            endpoint="http://jaeger:4317",
            insecure=True,  # Development environment
        )

    def test_gcp_exporter_without_package(self, mocker: MockerFixture) -> None:
        """Test GCP exporter when package not installed."""
        settings = Settings(
            observability_config=ObservabilityConfig(
                enable_tracing=True,
                exporter_type="gcp",
                gcp_project_id="test-project",
            )
        )

        # Simulate import error
        mocker.patch("builtins.__import__", side_effect=ImportError)
        exporter = get_span_exporter(settings)
        assert exporter is None

    def test_gcp_exporter_with_package(self, mocker: MockerFixture) -> None:
        """Test GCP exporter with package installed."""
        settings = Settings(
            observability_config=ObservabilityConfig(
                enable_tracing=True,
                exporter_type="gcp",
                gcp_project_id="test-project",
            )
        )

        # Mock the module and CloudTraceSpanExporter
        mock_module = mocker.MagicMock()
        mock_exporter_cls = mocker.MagicMock()
        mock_module.CloudTraceSpanExporter = mock_exporter_cls

        mocker.patch("importlib.import_module", return_value=mock_module)

        exporter = get_span_exporter(settings)

        # Verify exporter was created with correct project ID
        mock_exporter_cls.assert_called_once_with(project_id="test-project")
        assert exporter is not None

    def test_gcp_exporter_with_env_project(
        self, mocker: MockerFixture, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test GCP exporter using environment variable for project ID."""
        monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "env-project")

        settings = Settings(
            observability_config=ObservabilityConfig(
                enable_tracing=True,
                exporter_type="gcp",
                gcp_project_id=None,  # Not set in config
            )
        )

        # Mock the module and CloudTraceSpanExporter
        mock_module = mocker.MagicMock()
        mock_exporter_cls = mocker.MagicMock()
        mock_module.CloudTraceSpanExporter = mock_exporter_cls

        mocker.patch("importlib.import_module", return_value=mock_module)

        exporter = get_span_exporter(settings)

        # Verify exporter was created with env project ID
        mock_exporter_cls.assert_called_once_with(project_id="env-project")
        assert exporter is not None

    def test_gcp_exporter_no_project_id(self, mocker: MockerFixture) -> None:
        """Test GCP exporter without project ID configured."""
        settings = Settings(
            observability_config=ObservabilityConfig(
                enable_tracing=True,
                exporter_type="gcp",
                gcp_project_id=None,
            )
        )

        # Mock the module
        mock_module = mocker.MagicMock()
        mocker.patch("importlib.import_module", return_value=mock_module)

        exporter = get_span_exporter(settings)
        assert exporter is None  # Should return None when no project ID

    def test_aws_exporter(self, mocker: MockerFixture) -> None:
        """Test AWS X-Ray exporter configuration."""
        mock_otlp = mocker.patch("src.core.observability.OTLPSpanExporter")
        settings = Settings(
            observability_config=ObservabilityConfig(
                enable_tracing=True,
                exporter_type="aws",
                exporter_endpoint="https://xray.us-east-1.amazonaws.com",
            )
        )

        get_span_exporter(settings)

        mock_otlp.assert_called_once_with(
            endpoint="https://xray.us-east-1.amazonaws.com",
            insecure=True,  # Development environment
        )

    def test_unknown_exporter_type(self, mocker: MockerFixture) -> None:
        """Test unknown exporter type."""
        # Create a settings object with a valid type
        settings = Settings(
            observability_config=ObservabilityConfig(
                enable_tracing=True,
                exporter_type="console",
            )
        )

        # Mock the exporter_type to return an unknown value
        mocker.patch.object(
            settings.observability_config,
            "exporter_type",
            new_callable=mocker.PropertyMock,
            return_value="unknown",
        )

        exporter = get_span_exporter(settings)
        assert exporter is None


@pytest.mark.unit
class TestTracingSetup:
    """Test tracing setup."""

    def test_tracing_disabled(self, mocker: MockerFixture) -> None:
        """Test tracing can be disabled."""
        settings = Settings(
            observability_config=ObservabilityConfig(
                enable_tracing=False,
            )
        )

        # Clear any existing provider
        mock_trace = mocker.patch("src.core.observability.trace")
        mock_trace.set_tracer_provider(None)

        setup_tracing(settings)

        # Should not set up a provider
        mock_trace.set_tracer_provider.assert_called_once_with(None)

    def test_tracing_with_console_exporter(self, mocker: MockerFixture) -> None:
        """Test tracing setup with console exporter."""
        settings = Settings(
            app_name="test-app",
            app_version="1.0.0",
            environment="development",
            observability_config=ObservabilityConfig(
                enable_tracing=True,
                exporter_type="console",
                trace_sample_rate=0.5,
            ),
        )

        mock_trace = mocker.patch("src.core.observability.trace")
        mocker.patch("src.core.observability.TracerProvider")
        mock_resource = mocker.patch("src.core.observability.Resource")

        setup_tracing(settings)

        # Verify resource was created with correct attributes
        mock_resource.create.assert_called_once_with(
            {
                "service.name": "test-app",
                "service.version": "1.0.0",
                "deployment.environment": "development",
            }
        )

        # Verify provider is set
        mock_trace.set_tracer_provider.assert_called_once()

    def test_get_tracer(self) -> None:
        """Test getting a tracer instance."""
        tracer = get_tracer("test.module")
        assert hasattr(tracer, "start_span")


@pytest.mark.unit
class TestSpanOperations:
    """Test span operations and utilities."""

    def test_add_correlation_id_to_span(self) -> None:
        """Test adding correlation ID to span."""
        # Create mock span
        mock_span = Mock()
        mock_scope = {
            "headers": [(b"x-request-id", b"req-123")],
        }

        # Set correlation ID in context
        RequestContext.set_correlation_id("corr-456")

        add_correlation_id_to_span(mock_span, mock_scope)

        # Verify attributes were set
        mock_span.set_attribute.assert_any_call("correlation_id", "corr-456")
        mock_span.set_attribute.assert_any_call("request_id", "req-123")

    def test_add_span_attributes(self, mocker: MockerFixture) -> None:
        """Test adding custom span attributes."""
        mock_span = Mock()
        mock_span.is_recording.return_value = True

        mocker.patch("opentelemetry.trace.get_current_span", return_value=mock_span)
        add_span_attributes(
            user_id=123,
            action="login",
            success=True,
        )

        # All values should be converted to strings
        mock_span.set_attribute.assert_any_call("user_id", "123")
        mock_span.set_attribute.assert_any_call("action", "login")
        mock_span.set_attribute.assert_any_call("success", "True")

    def test_trace_operation_context_manager(self, mocker: MockerFixture) -> None:
        """Test trace_operation context manager."""
        # Setup basic tracing
        settings = Settings(
            observability_config=ObservabilityConfig(
                enable_tracing=True,
                exporter_type="console",
            )
        )
        setup_tracing(settings)

        # Set correlation ID
        RequestContext.set_correlation_id("test-correlation")

        # Mock tracer and span
        mock_tracer = Mock()
        mock_span = Mock()
        mock_tracer.start_span.return_value = mock_span

        mocker.patch("src.core.observability.get_tracer", return_value=mock_tracer)
        mock_use_span = mocker.patch("src.core.observability.trace.use_span")

        # Use trace_operation
        with trace_operation("test_operation", operation_type="unit_test"):
            # Operation code would go here
            pass

        # Verify span was created with correct name
        mock_tracer.start_span.assert_called_once_with("test_operation")

        # Verify attributes were set
        mock_span.set_attribute.assert_any_call("operation_type", "unit_test")
        mock_span.set_attribute.assert_any_call("correlation_id", "test-correlation")

        # Verify use_span was called
        mock_use_span.assert_called_once_with(mock_span, end_on_exit=True)


@pytest.mark.unit
class TestInstrumentation:
    """Test application instrumentation."""

    def test_instrument_app(self, mocker: MockerFixture) -> None:
        """Test FastAPI and SQLAlchemy instrumentation."""
        mock_fastapi_instrumentor = mocker.patch(
            "src.core.observability.FastAPIInstrumentor"
        )
        mock_sqlalchemy_instrumentor = mocker.patch(
            "src.core.observability.SQLAlchemyInstrumentor"
        )

        app = FastAPI()
        settings = Settings(
            observability_config=ObservabilityConfig(
                enable_tracing=True,
            )
        )

        instrument_app(app, settings)

        # Verify instrumentors were called
        mock_fastapi_instrumentor.instrument_app.assert_called_once_with(
            app,
            excluded_urls="/health,/metrics,/docs,/redoc,/openapi.json",
            server_request_hook=add_correlation_id_to_span,
        )
        mock_sqlalchemy_instrumentor.return_value.instrument.assert_called_once_with(
            enable_commenter=True,
            commenter_options={
                "opentelemetry_values": True,
            },
        )

    def test_instrument_app_disabled(self) -> None:
        """Test instrumentation when tracing is disabled."""
        app = FastAPI()
        settings = Settings(
            observability_config=ObservabilityConfig(
                enable_tracing=False,
            )
        )

        # Should not crash when disabled
        instrument_app(app, settings)


@pytest.mark.unit
class TestLoguruSpanExporter:
    """Test LoguruSpanExporter functionality."""

    def test_export_spans(self, mocker: MockerFixture) -> None:
        """Test that LoguruSpanExporter exports spans through Loguru."""
        # Mock logger.bind
        mock_logger = mocker.MagicMock()
        mock_bind = mocker.patch(
            "src.core.observability.logger.bind", return_value=mock_logger
        )

        # Create a mock span
        mock_span = mocker.MagicMock()
        mock_span.name = "test_operation"
        mock_span.kind.name = "INTERNAL"
        mock_span.attributes = {"user_id": "123", "action": "test"}
        mock_span.start_time = 1000000000  # 1 second in nanoseconds
        mock_span.end_time = 2000000000  # 2 seconds in nanoseconds
        mock_span.status.status_code.name = "OK"

        # Mock span context
        mock_context = mocker.MagicMock()
        mock_context.trace_id = 0x12345678
        mock_context.span_id = 0xABCDEF
        mock_span.get_span_context.return_value = mock_context

        exporter = LoguruSpanExporter()
        result = exporter.export([mock_span])

        # Verify export succeeded
        assert result == SpanExportResult.SUCCESS

        # Verify logger.bind was called with correct parameters
        mock_bind.assert_called_once_with(
            trace_id="0x00000000000000000000000012345678",
            span_id="0x0000000000abcdef",
            correlation_id=None,
            span_name="test_operation",
            span_kind="INTERNAL",
            duration_ms=1000,  # (2s - 1s) / 1_000_000
            attributes={"user_id": "123", "action": "test"},
            status="OK",
        )

        # Verify debug was called
        mock_logger.debug.assert_called_once_with(
            "Trace span completed: {}", "test_operation"
        )

    def test_export_spans_without_span_context(self, mocker: MockerFixture) -> None:
        """Test that LoguruSpanExporter handles spans without context gracefully."""
        # Mock logger.bind
        mock_logger = mocker.MagicMock()
        mock_bind = mocker.patch(
            "src.core.observability.logger.bind", return_value=mock_logger
        )

        # Create a mock span that returns None for get_span_context
        mock_span = mocker.MagicMock()
        mock_span.get_span_context.return_value = None

        # Export the span
        exporter = LoguruSpanExporter()
        result = exporter.export([mock_span])

        # Verify result is success but logger was not called
        assert result == SpanExportResult.SUCCESS
        mock_bind.assert_not_called()
        mock_logger.debug.assert_not_called()

    def test_export_spans_with_correlation_id(self, mocker: MockerFixture) -> None:
        """Test that LoguruSpanExporter includes correlation ID from context."""
        # Set correlation ID in context
        RequestContext.set_correlation_id("test-correlation-123")

        # Mock logger.bind
        mock_logger = mocker.MagicMock()
        mock_bind = mocker.patch(
            "src.core.observability.logger.bind", return_value=mock_logger
        )

        # Create a mock span without correlation_id in attributes
        mock_span = mocker.MagicMock()
        mock_span.name = "test_operation"
        mock_span.kind.name = "INTERNAL"
        mock_span.attributes = {}
        mock_span.start_time = 1000000000
        mock_span.end_time = 2000000000
        mock_span.status.status_code.name = "OK"

        # Mock span context
        mock_context = mocker.MagicMock()
        mock_context.trace_id = 0x12345678
        mock_context.span_id = 0xABCDEF
        mock_span.get_span_context.return_value = mock_context

        exporter = LoguruSpanExporter()
        exporter.export([mock_span])

        # Verify correlation ID from context was used
        bind_call_kwargs = mock_bind.call_args[1]
        assert bind_call_kwargs["correlation_id"] == "test-correlation-123"


@pytest.mark.unit
class TestCloudAgnostic:
    """Test cloud-agnostic functionality."""

    def test_no_cloud_dependencies_for_console(self) -> None:
        """Test console exporter requires no cloud dependencies."""
        settings = Settings(
            observability_config=ObservabilityConfig(
                enable_tracing=True,
                exporter_type="console",
            )
        )

        # Should work without any cloud authentication
        setup_tracing(settings)

        # Verify we can create spans
        tracer = get_tracer("test")
        with tracer.start_as_current_span("test_span") as span:
            span.set_attribute("test", "value")

    def test_environment_based_configuration(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test configuration via environment variables."""
        monkeypatch.setenv("OBSERVABILITY_CONFIG__EXPORTER_TYPE", "otlp")
        monkeypatch.setenv(
            "OBSERVABILITY_CONFIG__EXPORTER_ENDPOINT", "http://tempo:4317"
        )
        monkeypatch.setenv("OBSERVABILITY_CONFIG__TRACE_SAMPLE_RATE", "0.1")

        settings = Settings()

        assert settings.observability_config.exporter_type == "otlp"
        assert settings.observability_config.exporter_endpoint == "http://tempo:4317"
        assert settings.observability_config.trace_sample_rate == 0.1
