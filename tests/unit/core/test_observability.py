"""Unit tests for observability and tracing module."""

from unittest.mock import Mock

import pytest
import pytest_check
from opentelemetry.sdk.trace import Span
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import Status, StatusCode
from pytest_mock import MockerFixture

from src.core.config import Settings
from src.core.exceptions import ErrorCode, Severity, TributumError
from src.core.observability import (
    ErrorTrackingSpanProcessor,
    get_tracer,
    record_tributum_error_in_span,
    setup_tracing,
)


@pytest.mark.unit
class TestSetupTracing:
    """Test cases for setup_tracing function."""

    def test_setup_tracing_disabled(self, mocker: MockerFixture) -> None:
        """Test setup_tracing when tracing is disabled."""
        # Mock get_settings
        mock_settings = Settings()
        mock_settings.observability_config.enable_tracing = False
        mocker.patch("src.core.observability.get_settings", return_value=mock_settings)

        # Mock logger
        mock_logger = mocker.patch("src.core.observability.logger")

        # Call setup_tracing
        setup_tracing()

        # Verify only the disabled log was called
        mock_logger.info.assert_called_once_with("Tracing is disabled")

    def test_setup_tracing_without_gcp(self, mocker: MockerFixture) -> None:
        """Test setup_tracing without GCP project ID."""
        # Configure settings with tracing enabled but no GCP project
        mock_settings = Settings()
        mock_settings.observability_config.enable_tracing = True
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
        mock_resource_instance = Mock()
        mock_resource.create.return_value = mock_resource_instance
        mock_sampler_instance = Mock()
        mock_sampler.return_value = mock_sampler_instance
        mock_provider = Mock()
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
        mock_resource_instance = Mock()
        mock_resource.create.return_value = mock_resource_instance
        mock_sampler_instance = Mock()
        mock_sampler.return_value = mock_sampler_instance
        mock_provider = Mock()
        mock_provider_class.return_value = mock_provider
        mock_exporter = Mock()
        mock_exporter_class.return_value = mock_exporter
        mock_processor = Mock()
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
        mock_provider = Mock()
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


@pytest.mark.unit
class TestGetTracer:
    """Test cases for get_tracer function."""

    def test_get_tracer(self, mocker: MockerFixture) -> None:
        """Test get_tracer returns tracer from OpenTelemetry."""
        # Mock trace.get_tracer
        mock_trace = mocker.patch("src.core.observability.trace")
        mock_tracer = Mock()
        mock_trace.get_tracer.return_value = mock_tracer

        # Call get_tracer
        result = get_tracer("test-component")

        # Verify it called trace.get_tracer with the name
        mock_trace.get_tracer.assert_called_once_with("test-component")
        assert result == mock_tracer


@pytest.mark.unit
class TestRecordTributumErrorInSpan:
    """Test cases for record_tributum_error_in_span function."""

    def test_record_critical_error(self) -> None:
        """Test recording a critical severity error in span."""
        # Create a mock span
        mock_span = Mock(spec=Span)

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

    def test_record_low_severity_error(self) -> None:
        """Test recording a low severity error in span."""
        # Create a mock span
        mock_span = Mock(spec=Span)

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

    def test_record_error_with_complex_context(self) -> None:
        """Test recording error with non-primitive context values."""
        # Create a mock span
        mock_span = Mock(spec=Span)

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

    def test_processor_initialization(self) -> None:
        """Test processor initializes with exporter."""
        mock_exporter = Mock()
        processor = ErrorTrackingSpanProcessor(mock_exporter)

        # Should inherit from BatchSpanProcessor
        assert isinstance(processor, BatchSpanProcessor)

    def test_on_end_without_error(self, mocker: MockerFixture) -> None:
        """Test on_end when span has no error."""
        # Create processor with mock exporter
        mock_exporter = Mock()
        processor = ErrorTrackingSpanProcessor(mock_exporter)

        # Create a mock span without error
        mock_span = Mock()
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
        mock_exporter = Mock()
        processor = ErrorTrackingSpanProcessor(mock_exporter)

        # Create mock event with TributumError attributes
        mock_event = Mock()
        mock_event.name = "exception"
        mock_event.attributes = {
            "exception.type": "TributumError",
            "tributum.error_code": "INTERNAL_ERROR",
            "tributum.severity": "HIGH",
            "other_attr": "value",
        }

        # Create a mock span with error
        mock_span = Mock()
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
        mock_exporter = Mock()
        processor = ErrorTrackingSpanProcessor(mock_exporter)

        # Create a mock span with error but no events attribute
        mock_span = Mock(spec=["status", "set_attribute"])
        mock_span.status.status_code = StatusCode.ERROR

        # Mock the parent on_end
        mock_parent_on_end = mocker.patch.object(BatchSpanProcessor, "on_end")

        # Should not raise AttributeError
        processor.on_end(mock_span)

        # Verify parent on_end was called
        mock_parent_on_end.assert_called_once_with(mock_span)
