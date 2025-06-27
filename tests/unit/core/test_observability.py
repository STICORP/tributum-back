"""Unit tests for observability and tracing module."""

import psutil
import pytest
import pytest_check
from opentelemetry.sdk.trace import Span
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import Status, StatusCode
from pytest_mock import MockerFixture

import src.core.observability
from src.core.config import Settings
from src.core.exceptions import ErrorCode, Severity, TributumError
from src.core.observability import (
    ErrorTrackingSpanProcessor,
    _get_active_tasks_count,
    _get_cpu_percentage,
    _get_gc_collections,
    _get_memory_usage,
    get_database_pool_metrics,
    get_meter,
    get_tracer,
    record_tributum_error_in_span,
    setup_observability,
    setup_tracing,
)


@pytest.mark.unit
class TestSetupObservability:
    """Test cases for setup_observability and setup_tracing functions."""

    def test_setup_observability_all_disabled(self, mocker: MockerFixture) -> None:
        """Test setup_observability when both tracing and metrics are disabled."""
        # Mock get_settings
        mock_settings = Settings()
        mock_settings.observability_config.enable_tracing = False
        mock_settings.observability_config.enable_metrics = False
        mocker.patch("src.core.observability.get_settings", return_value=mock_settings)

        # Mock logger
        mock_logger = mocker.patch("src.core.observability.logger")

        # Call setup_observability
        setup_observability()

        # Verify both disabled logs were called
        assert mock_logger.info.call_count == 2
        mock_logger.info.assert_any_call("Tracing is disabled")
        mock_logger.info.assert_any_call("Metrics are disabled")

    def test_setup_tracing_without_gcp(self, mocker: MockerFixture) -> None:
        """Test setup_tracing without GCP project ID."""
        # Configure settings with tracing enabled but no GCP project
        mock_settings = Settings()
        mock_settings.observability_config.enable_tracing = True
        mock_settings.observability_config.enable_metrics = (
            False  # Explicitly disable metrics
        )
        mock_settings.observability_config.gcp_project_id = None
        mock_settings.observability_config.service_name = "test-service"
        mock_settings.observability_config.trace_sample_rate = 0.5
        mock_settings.app_version = "1.0.0"
        mock_settings.environment = "development"
        mocker.patch("src.core.observability.get_settings", return_value=mock_settings)

        # Mock dependencies
        mock_logger = mocker.patch("src.core.observability.logger")
        mock_resource = mocker.patch("src.core.observability.Resource")
        mock_sampler = mocker.patch("src.core.observability.TraceIdRatioBased")
        mock_provider_class = mocker.patch("src.core.observability.TracerProvider")
        mock_trace = mocker.patch("src.core.observability.trace")

        # Create mock instances
        mock_resource_instance = mocker.Mock()
        mock_resource.create.return_value = mock_resource_instance
        mock_sampler_instance = mocker.Mock()
        mock_sampler.return_value = mock_sampler_instance
        mock_provider = mocker.Mock()
        mock_provider_class.return_value = mock_provider

        # Call setup_tracing
        setup_tracing()

        # Verify resource was created with correct attributes
        mock_resource.create.assert_called_once_with(
            {
                "service.name": "test-service",
                "service.version": "1.0.0",
                "deployment.environment": "development",
            }
        )

        # Verify sampler was created with correct rate
        mock_sampler.assert_called_once_with(0.5)

        # Verify provider was created
        mock_provider_class.assert_called_once_with(
            resource=mock_resource_instance, sampler=mock_sampler_instance
        )

        # Verify trace provider was set
        mock_trace.set_tracer_provider.assert_called_once_with(mock_provider)

        # Verify warning about missing GCP project
        mock_logger.warning.assert_called_once_with(
            "GCP project ID not configured, traces will not be exported"
        )

    def test_setup_tracing_with_gcp(self, mocker: MockerFixture) -> None:
        """Test setup_tracing with GCP project ID configured."""
        # Configure settings with tracing and GCP enabled
        mock_settings = Settings()
        mock_settings.observability_config.enable_tracing = True
        mock_settings.observability_config.enable_metrics = (
            False  # Explicitly disable metrics
        )
        mock_settings.observability_config.gcp_project_id = "test-project"
        mock_settings.observability_config.service_name = "test-service"
        mock_settings.observability_config.trace_sample_rate = 1.0
        mock_settings.app_version = "1.0.0"
        mock_settings.environment = "production"
        mocker.patch("src.core.observability.get_settings", return_value=mock_settings)

        # Mock dependencies
        mock_logger = mocker.patch("src.core.observability.logger")
        mock_resource = mocker.patch("src.core.observability.Resource")
        mock_sampler = mocker.patch("src.core.observability.TraceIdRatioBased")
        mock_provider_class = mocker.patch("src.core.observability.TracerProvider")
        mocker.patch("src.core.observability.trace")
        mock_exporter_class = mocker.patch(
            "src.core.observability.CloudTraceSpanExporter"
        )
        mock_processor_class = mocker.patch(
            "src.core.observability.ErrorTrackingSpanProcessor"
        )

        # Create mock instances
        mock_resource_instance = mocker.Mock()
        mock_resource.create.return_value = mock_resource_instance
        mock_sampler_instance = mocker.Mock()
        mock_sampler.return_value = mock_sampler_instance
        mock_provider = mocker.Mock()
        mock_provider_class.return_value = mock_provider
        mock_exporter = mocker.Mock()
        mock_exporter_class.return_value = mock_exporter
        mock_processor = mocker.Mock()
        mock_processor_class.return_value = mock_processor

        # Call setup_tracing
        setup_tracing()

        # Verify exporter was created with project ID
        mock_exporter_class.assert_called_once_with(project_id="test-project")

        # Verify custom processor was created with exporter
        mock_processor_class.assert_called_once_with(mock_exporter)

        # Verify processor was added to provider
        mock_provider.add_span_processor.assert_called_once_with(mock_processor)

        # Verify info log about GCP configuration
        assert any(
            call.args[0] == "GCP Cloud Trace exporter configured"
            for call in mock_logger.info.call_args_list
        )

    def test_setup_tracing_gcp_error(self, mocker: MockerFixture) -> None:
        """Test setup_tracing when GCP exporter fails."""
        # Configure settings with GCP enabled
        mock_settings = Settings()
        mock_settings.observability_config.enable_tracing = True
        mock_settings.observability_config.enable_metrics = (
            False  # Explicitly disable metrics
        )
        mock_settings.observability_config.gcp_project_id = "test-project"
        mock_settings.observability_config.service_name = "test-service"
        mock_settings.observability_config.trace_sample_rate = 1.0
        mocker.patch("src.core.observability.get_settings", return_value=mock_settings)

        # Mock dependencies
        mock_logger = mocker.patch("src.core.observability.logger")
        mocker.patch("src.core.observability.Resource")
        mocker.patch("src.core.observability.TraceIdRatioBased")
        mock_provider_class = mocker.patch("src.core.observability.TracerProvider")
        mock_trace = mocker.patch("src.core.observability.trace")

        # Make exporter creation fail
        mock_exporter_class = mocker.patch(
            "src.core.observability.CloudTraceSpanExporter"
        )
        mock_exporter_class.side_effect = RuntimeError("GCP connection failed")

        # Mock provider
        mock_provider = mocker.Mock()
        mock_provider_class.return_value = mock_provider

        # Call setup_tracing - should not raise
        setup_tracing()

        # Verify error was logged
        assert any(
            "Failed to configure GCP Cloud Trace exporter" in str(call.args[0])
            for call in mock_logger.exception.call_args_list
        )

        # Verify tracing was still set up (without GCP)
        mock_trace.set_tracer_provider.assert_called_once()

    def test_setup_metrics_without_gcp(self, mocker: MockerFixture) -> None:
        """Test setup_observability with metrics enabled but no GCP project."""
        # Configure settings with metrics enabled but no GCP project
        mock_settings = Settings()
        mock_settings.observability_config.enable_tracing = False
        mock_settings.observability_config.enable_metrics = True
        mock_settings.observability_config.gcp_project_id = None
        mock_settings.observability_config.service_name = "test-service"
        mock_settings.observability_config.metrics_export_interval_ms = 30000
        mock_settings.observability_config.enable_system_metrics = False
        mock_settings.app_version = "1.0.0"
        mocker.patch("src.core.observability.get_settings", return_value=mock_settings)

        # Mock dependencies
        mock_logger = mocker.patch("src.core.observability.logger")
        mock_resource = mocker.patch("src.core.observability.Resource")
        mock_metrics = mocker.patch("src.core.observability.metrics")
        mock_meter_provider_class = mocker.patch("src.core.observability.MeterProvider")

        # Create mock instances
        mock_resource_instance = mocker.Mock()
        mock_resource.create.return_value = mock_resource_instance
        mock_meter_provider = mocker.Mock()
        mock_meter_provider_class.return_value = mock_meter_provider
        mock_meter = mocker.Mock()
        mock_meter_provider.get_meter.return_value = mock_meter

        # Call setup_observability
        setup_observability()

        # Verify resource was created
        mock_resource.create.assert_called_once()

        # Verify meter provider was created without readers (no GCP)
        mock_meter_provider_class.assert_called_once_with(
            resource=mock_resource_instance,
            metric_readers=[],
        )

        # Verify meter provider was set
        mock_metrics.set_meter_provider.assert_called_once_with(mock_meter_provider)

        # Verify meter was obtained
        mock_meter_provider.get_meter.assert_called_once_with(
            name="tributum",
            version="1.0.0",
        )

        # Verify metric instruments were created
        assert mock_meter.create_counter.call_count == 3  # request, error, db_query
        # request_duration, db_query_duration
        assert mock_meter.create_histogram.call_count == 2

        # Verify warning about missing GCP project
        mock_logger.warning.assert_called_once_with(
            "GCP project ID not configured, metrics will not be exported"
        )

    def test_setup_metrics_with_gcp(self, mocker: MockerFixture) -> None:
        """Test setup_observability with metrics and GCP project configured."""
        # Configure settings
        mock_settings = Settings()
        mock_settings.observability_config.enable_tracing = False
        mock_settings.observability_config.enable_metrics = True
        mock_settings.observability_config.gcp_project_id = "test-project"
        mock_settings.observability_config.service_name = "test-service"
        mock_settings.observability_config.metrics_export_interval_ms = 60000
        mock_settings.observability_config.enable_system_metrics = True
        mock_settings.app_version = "2.0.0"
        mocker.patch("src.core.observability.get_settings", return_value=mock_settings)

        # Mock dependencies
        mock_logger = mocker.patch("src.core.observability.logger")
        mocker.patch("src.core.observability.Resource")
        mocker.patch("src.core.observability.metrics")
        mock_meter_provider_class = mocker.patch("src.core.observability.MeterProvider")
        mock_cloud_exporter_class = mocker.patch(
            "src.core.observability.CloudMonitoringMetricsExporter"
        )
        mock_reader_class = mocker.patch(
            "src.core.observability.PeriodicExportingMetricReader"
        )
        mock_register_system_metrics = mocker.patch(
            "src.core.observability._register_system_metrics"
        )

        # Create mock instances
        mock_cloud_exporter = mocker.Mock()
        mock_cloud_exporter_class.return_value = mock_cloud_exporter
        mock_reader = mocker.Mock()
        mock_reader_class.return_value = mock_reader
        mock_meter_provider = mocker.Mock()
        mock_meter_provider_class.return_value = mock_meter_provider
        mock_meter = mocker.Mock()
        mock_meter_provider.get_meter.return_value = mock_meter

        # Call setup_observability
        setup_observability()

        # Verify cloud exporter was created
        mock_cloud_exporter_class.assert_called_once_with(project_id="test-project")

        # Verify reader was created with correct interval
        mock_reader_class.assert_called_once_with(
            exporter=mock_cloud_exporter,
            export_interval_millis=60000,
        )

        # Verify meter provider was created with reader
        mock_meter_provider_class.assert_called_once()
        call_kwargs = mock_meter_provider_class.call_args[1]
        assert call_kwargs["metric_readers"] == [mock_reader]

        # Verify system metrics were registered
        mock_register_system_metrics.assert_called_once_with(mock_meter)

        # Verify info log about GCP configuration
        assert any(
            "GCP Cloud Monitoring exporter configured" in str(call)
            for call in mock_logger.info.call_args_list
        )

    def test_setup_metrics_gcp_error(self, mocker: MockerFixture) -> None:
        """Test setup_observability when GCP metrics exporter fails."""
        # Configure settings
        mock_settings = Settings()
        mock_settings.observability_config.enable_tracing = False
        mock_settings.observability_config.enable_metrics = True
        mock_settings.observability_config.gcp_project_id = "test-project"
        mocker.patch("src.core.observability.get_settings", return_value=mock_settings)

        # Mock dependencies
        mock_logger = mocker.patch("src.core.observability.logger")
        mocker.patch("src.core.observability.Resource")
        mocker.patch("src.core.observability.metrics")
        mocker.patch("src.core.observability.MeterProvider")

        # Make exporter creation fail
        mock_cloud_exporter_class = mocker.patch(
            "src.core.observability.CloudMonitoringMetricsExporter"
        )
        mock_cloud_exporter_class.side_effect = RuntimeError("GCP connection failed")

        # Call setup_observability - should not raise
        setup_observability()

        # Verify error was logged
        mock_logger.exception.assert_called_once()
        assert "Failed to configure GCP Cloud Monitoring exporter" in str(
            mock_logger.exception.call_args[0][0]
        )

    def test_setup_tracing_compatibility(self, mocker: MockerFixture) -> None:
        """Test that setup_tracing calls setup_observability."""
        mock_setup_observability = mocker.patch(
            "src.core.observability.setup_observability"
        )

        setup_tracing()

        mock_setup_observability.assert_called_once()


@pytest.mark.unit
class TestGetTracer:
    """Test cases for get_tracer function."""

    def test_get_tracer(self, mocker: MockerFixture) -> None:
        """Test get_tracer returns tracer from OpenTelemetry."""
        # Mock trace.get_tracer
        mock_trace = mocker.patch("src.core.observability.trace")
        mock_tracer = mocker.Mock()
        mock_trace.get_tracer.return_value = mock_tracer

        # Call get_tracer
        result = get_tracer("test-component")

        # Verify it called trace.get_tracer with the name
        mock_trace.get_tracer.assert_called_once_with("test-component")
        assert result == mock_tracer


@pytest.mark.unit
class TestRecordTributumErrorInSpan:
    """Test cases for record_tributum_error_in_span function."""

    def test_record_critical_error(self, mocker: MockerFixture) -> None:
        """Test recording a critical severity error in span."""
        # Create a mock span
        mock_span = mocker.Mock(spec=Span)

        # Create a critical error
        error = TributumError(
            error_code=ErrorCode.INTERNAL_ERROR,
            message="Critical failure",
            severity=Severity.CRITICAL,
            context={"user_id": 123, "operation": "payment"},
        )

        # Record the error
        record_tributum_error_in_span(mock_span, error)

        # Verify span status was set to ERROR
        mock_span.set_status.assert_called_once()
        status_call = mock_span.set_status.call_args[0][0]
        assert isinstance(status_call, Status)
        assert status_call.status_code == StatusCode.ERROR
        assert status_call.description == "Critical failure"

        # Verify attributes were set - using pytest_check for multiple assertions
        expected_attrs = [
            ("tributum.error_code", ErrorCode.INTERNAL_ERROR.value),
            ("tributum.severity", Severity.CRITICAL.value),
            ("tributum.fingerprint", error.fingerprint),
            ("tributum.context.user_id", 123),
            ("tributum.context.operation", "payment"),
        ]

        with pytest_check.check:
            assert mock_span.set_attribute.call_count == 5

        for attr_name, attr_value in expected_attrs:
            with pytest_check.check:
                mock_span.set_attribute.assert_any_call(attr_name, attr_value)

        # Verify exception was recorded
        with pytest_check.check:
            mock_span.record_exception.assert_called_once()
        with pytest_check.check:
            exc_call_args = mock_span.record_exception.call_args
            assert exc_call_args[0][0] == error
        with pytest_check.check:
            assert (
                exc_call_args[1]["attributes"]["tributum.error_code"]
                == ErrorCode.INTERNAL_ERROR.value
            )

    def test_record_low_severity_error(self, mocker: MockerFixture) -> None:
        """Test recording a low severity error in span."""
        # Create a mock span
        mock_span = mocker.Mock(spec=Span)

        # Create a low severity error
        error = TributumError(
            error_code=ErrorCode.VALIDATION_ERROR,
            message="Invalid input",
            severity=Severity.LOW,
        )

        # Record the error
        record_tributum_error_in_span(mock_span, error)

        # Verify span status was set to OK (not ERROR)
        mock_span.set_status.assert_called_once()
        status_call = mock_span.set_status.call_args[0][0]
        assert isinstance(status_call, Status)
        assert status_call.status_code == StatusCode.OK

    def test_record_error_with_complex_context(self, mocker: MockerFixture) -> None:
        """Test recording error with non-primitive context values."""
        # Create a mock span
        mock_span = mocker.Mock(spec=Span)

        # Create error with complex context
        error = TributumError(
            error_code=ErrorCode.NOT_FOUND,
            message="Resource not found",
            context={
                "string_val": "test",
                "int_val": 42,
                "float_val": 3.14,
                "bool_val": True,
                "list_val": [1, 2, 3],  # Should be converted to string
                "dict_val": {"nested": "value"},  # Should be converted to string
            },
        )

        # Record the error
        record_tributum_error_in_span(mock_span, error)

        # Verify primitive types are set directly
        # Extract all calls to set_attribute for verification
        set_attribute_calls = mock_span.set_attribute.call_args_list

        # Build a dict of actual calls for easier verification
        actual_attrs = {
            call[0][0]: call[0][1] for call in set_attribute_calls if len(call[0]) >= 2
        }

        with pytest_check.check:
            assert "tributum.context.string_val" in actual_attrs
            assert actual_attrs["tributum.context.string_val"] == "test"
        with pytest_check.check:
            assert "tributum.context.int_val" in actual_attrs
            assert actual_attrs["tributum.context.int_val"] == 42
        with pytest_check.check:
            assert "tributum.context.float_val" in actual_attrs
            assert actual_attrs["tributum.context.float_val"] == 3.14
        with pytest_check.check:
            assert "tributum.context.bool_val" in actual_attrs
            assert actual_attrs["tributum.context.bool_val"] is True

        # Verify complex types are converted to strings
        with pytest_check.check:
            assert "tributum.context.list_val" in actual_attrs
            assert actual_attrs["tributum.context.list_val"] == "[1, 2, 3]"
        with pytest_check.check:
            assert "tributum.context.dict_val" in actual_attrs
            assert actual_attrs["tributum.context.dict_val"] == "{'nested': 'value'}"


@pytest.mark.unit
class TestErrorTrackingSpanProcessor:
    """Test cases for ErrorTrackingSpanProcessor class."""

    def test_processor_initialization(self, mocker: MockerFixture) -> None:
        """Test processor initializes with exporter."""
        mock_exporter = mocker.Mock()
        processor = ErrorTrackingSpanProcessor(mock_exporter)

        # Should inherit from BatchSpanProcessor
        assert isinstance(processor, BatchSpanProcessor)

    def test_on_end_without_error(self, mocker: MockerFixture) -> None:
        """Test on_end when span has no error."""
        # Create processor with mock exporter
        mock_exporter = mocker.Mock()
        processor = ErrorTrackingSpanProcessor(mock_exporter)

        # Create a mock span without error
        mock_span = mocker.Mock()
        mock_span.status.status_code = StatusCode.OK

        # Mock the parent on_end
        mock_parent_on_end = mocker.patch.object(BatchSpanProcessor, "on_end")

        processor.on_end(mock_span)

        # Verify parent on_end was called
        mock_parent_on_end.assert_called_once_with(mock_span)

        # Verify no attributes were set (span was OK)
        mock_span.set_attribute.assert_not_called()

    def test_on_end_with_tributum_error(self, mocker: MockerFixture) -> None:
        """Test on_end when span has TributumError."""
        # Create processor with mock exporter
        mock_exporter = mocker.Mock()
        processor = ErrorTrackingSpanProcessor(mock_exporter)

        # Create mock event with TributumError attributes
        mock_event = mocker.Mock()
        mock_event.name = "exception"
        mock_event.attributes = {
            "exception.type": "TributumError",
            "tributum.error_code": "INTERNAL_ERROR",
            "tributum.severity": "HIGH",
            "other_attr": "value",
        }

        # Create a mock span with error
        mock_span = mocker.Mock()
        mock_span.status.status_code = StatusCode.ERROR
        mock_span.events = [mock_event]

        # Mock the parent on_end
        mock_parent_on_end = mocker.patch.object(BatchSpanProcessor, "on_end")

        processor.on_end(mock_span)

        # Verify parent on_end was called
        mock_parent_on_end.assert_called_once_with(mock_span)

        # Since spans are read-only in on_end, no attributes should be set
        mock_span.set_attribute.assert_not_called()

    def test_on_end_without_events_attribute(self, mocker: MockerFixture) -> None:
        """Test on_end when span doesn't have events attribute."""
        # Create processor with mock exporter
        mock_exporter = mocker.Mock()
        processor = ErrorTrackingSpanProcessor(mock_exporter)

        # Create a mock span with error but no events attribute
        mock_span = mocker.Mock(spec=["status", "set_attribute"])
        mock_span.status.status_code = StatusCode.ERROR

        # Mock the parent on_end
        mock_parent_on_end = mocker.patch.object(BatchSpanProcessor, "on_end")

        # Should not raise AttributeError
        processor.on_end(mock_span)

        # Verify parent on_end was called
        mock_parent_on_end.assert_called_once_with(mock_span)


@pytest.mark.unit
class TestMetricsHelpers:
    """Test cases for metrics helper functions."""

    def test_get_meter_when_enabled(self, mocker: MockerFixture) -> None:
        """Test get_meter returns meter when metrics are enabled."""
        # Mock the module-level _meter variable
        mock_meter = mocker.Mock()
        mocker.patch.object(src.core.observability, "_meter", mock_meter, create=True)

        result = get_meter()
        assert result == mock_meter

    def test_get_meter_when_disabled(self, mocker: MockerFixture) -> None:
        """Test get_meter returns None when metrics are disabled."""
        # Mock the module-level _meter variable as None
        mocker.patch.object(src.core.observability, "_meter", None, create=True)

        result = get_meter()
        assert result is None

    def test_get_database_pool_metrics_with_pool(self, mocker: MockerFixture) -> None:
        """Test get_database_pool_metrics with a valid pool."""
        # Create a mock pool
        mock_pool = mocker.Mock()
        mock_pool.size.return_value = 10
        mock_pool.checked_in_connections = 7
        mock_pool.checked_out_connections = 3
        mock_pool.overflow = 0
        mock_pool.total = 10

        result = get_database_pool_metrics(mock_pool)

        assert result == {
            "size": 10,
            "checked_in": 7,
            "checked_out": 3,
            "overflow": 0,
            "total": 10,
        }

    def test_get_database_pool_metrics_with_none(self) -> None:
        """Test get_database_pool_metrics with None pool."""
        result = get_database_pool_metrics(None)

        assert result == {
            "size": 0,
            "checked_in": 0,
            "checked_out": 0,
            "overflow": 0,
            "total": 0,
        }

    def test_get_database_pool_metrics_with_attribute_error(
        self, mocker: MockerFixture
    ) -> None:
        """Test get_database_pool_metrics when pool attributes are missing."""
        # Create a mock pool that raises AttributeError
        mock_pool = mocker.Mock()
        mock_pool.size.side_effect = AttributeError("No such attribute")

        # Mock logger to verify debug message
        mock_logger = mocker.patch("src.core.observability.logger")

        result = get_database_pool_metrics(mock_pool)

        assert result == {
            "size": 0,
            "checked_in": 0,
            "checked_out": 0,
            "overflow": 0,
            "total": 0,
        }
        mock_logger.debug.assert_called_once_with("Failed to get pool metrics")


@pytest.mark.unit
class TestSystemMetrics:
    """Test cases for system metrics collectors."""

    def test_get_cpu_percentage(self, mocker: MockerFixture) -> None:
        """Test _get_cpu_percentage collector."""
        # Mock psutil
        mock_process_class = mocker.patch("src.core.observability.psutil.Process")
        mock_process = mocker.Mock()
        mock_process_class.return_value = mock_process
        mock_process.cpu_percent.return_value = 25.5

        # Mock os.getpid
        mocker.patch("src.core.observability.os.getpid", return_value=12345)

        # Create mock callback options
        mock_options = mocker.Mock()

        result = _get_cpu_percentage(mock_options)

        assert len(result) == 1
        assert result[0].value == 25.5
        assert result[0].attributes == {}
        mock_process.cpu_percent.assert_called_once_with(interval=None)

    def test_get_cpu_percentage_error(self, mocker: MockerFixture) -> None:
        """Test _get_cpu_percentage when psutil fails."""
        # Make psutil raise an error
        mocker.patch(
            "src.core.observability.psutil.Process",
            side_effect=psutil.NoSuchProcess(12345, "Process not found"),
        )

        # Mock logger
        mock_logger = mocker.patch("src.core.observability.logger")

        # Create mock callback options
        mock_options = mocker.Mock()

        result = _get_cpu_percentage(mock_options)

        assert len(result) == 1
        assert result[0].value == 0.0
        assert result[0].attributes == {}
        mock_logger.debug.assert_called_once_with("Failed to get CPU percentage")

    def test_get_memory_usage(self, mocker: MockerFixture) -> None:
        """Test _get_memory_usage collector."""
        # Mock psutil
        mock_process_class = mocker.patch("src.core.observability.psutil.Process")
        mock_process = mocker.Mock()
        mock_process_class.return_value = mock_process
        mock_memory_info = mocker.Mock()
        mock_memory_info.rss = 104857600  # 100 MB
        mock_process.memory_info.return_value = mock_memory_info

        # Mock os.getpid
        mocker.patch("src.core.observability.os.getpid", return_value=12345)

        # Create mock callback options
        mock_options = mocker.Mock()

        result = _get_memory_usage(mock_options)

        assert len(result) == 1
        assert result[0].value == 104857600
        assert result[0].attributes == {}

    def test_get_memory_usage_fallback(self, mocker: MockerFixture) -> None:
        """Test _get_memory_usage fallback to resource module."""
        # Make psutil fail
        mocker.patch(
            "src.core.observability.psutil.Process",
            side_effect=psutil.AccessDenied("Access denied"),
        )

        # Mock resource module
        mock_resource = mocker.patch("src.core.observability.resource")
        mock_usage = mocker.Mock()
        mock_usage.ru_maxrss = 102400  # 100 MB in KB
        mock_resource.getrusage.return_value = mock_usage
        mock_resource.RUSAGE_SELF = 0

        # Create mock callback options
        mock_options = mocker.Mock()

        result = _get_memory_usage(mock_options)

        assert len(result) == 1
        assert result[0].value == 102400 * 1024  # Converted to bytes
        assert result[0].attributes == {}

    def test_get_active_tasks_count(self, mocker: MockerFixture) -> None:
        """Test _get_active_tasks_count collector."""
        # Mock asyncio.all_tasks
        mock_tasks = [mocker.Mock(), mocker.Mock(), mocker.Mock()]
        mocker.patch(
            "src.core.observability.asyncio.all_tasks", return_value=mock_tasks
        )

        # Create mock callback options
        mock_options = mocker.Mock()

        result = _get_active_tasks_count(mock_options)

        assert len(result) == 1
        assert result[0].value == 3
        assert result[0].attributes == {}

    def test_get_active_tasks_count_error(self, mocker: MockerFixture) -> None:
        """Test _get_active_tasks_count when not in asyncio context."""
        # Make asyncio.all_tasks raise RuntimeError
        mocker.patch(
            "src.core.observability.asyncio.all_tasks",
            side_effect=RuntimeError("No event loop"),
        )

        # Create mock callback options
        mock_options = mocker.Mock()

        result = _get_active_tasks_count(mock_options)

        assert len(result) == 1
        assert result[0].value == 0
        assert result[0].attributes == {}

    def test_get_gc_collections(self, mocker: MockerFixture) -> None:
        """Test _get_gc_collections collector."""
        # Mock gc module
        mock_gc = mocker.patch("src.core.observability.gc")
        mock_gc.get_count.return_value = (10, 20, 30)  # Mock 3 generations
        mock_gc.get_stats.return_value = [
            {"collections": 100},
            {"collections": 50},
            {"collections": 10},
        ]

        # Create mock callback options
        mock_options = mocker.Mock()

        result = _get_gc_collections(mock_options)

        assert len(result) == 3
        assert result[0].value == 100
        assert result[0].attributes == {"generation": "0"}
        assert result[1].value == 50
        assert result[1].attributes == {"generation": "1"}
        assert result[2].value == 10
        assert result[2].attributes == {"generation": "2"}
