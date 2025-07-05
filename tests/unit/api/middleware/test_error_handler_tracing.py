"""Tests for OpenTelemetry tracing integration in error handlers."""

import pytest
from fastapi import HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from opentelemetry.trace import Status, StatusCode
from pytest_mock import MockerFixture

from src.api.middleware.error_handler import (
    generic_exception_handler,
    http_exception_handler,
    tributum_error_handler,
    validation_error_handler,
)
from src.core.exceptions import (
    BusinessRuleError,
    NotFoundError,
    UnauthorizedError,
    ValidationError,
)


@pytest.mark.unit
class TestTributumErrorTracing:
    """Test OpenTelemetry tracing for TributumError exceptions."""

    async def test_tributum_error_records_exception(
        self, mocker: MockerFixture
    ) -> None:
        """TributumError should record exception in span."""
        # Create mocks
        mock_request = mocker.Mock(spec=Request)
        mock_request.method = "GET"
        mock_request.url.path = "/test/endpoint"

        mock_span = mocker.Mock()
        mock_span.is_recording.return_value = True

        mocker.patch(
            "src.api.middleware.error_handler.trace.get_current_span",
            return_value=mock_span,
        )

        error = ValidationError(
            "Invalid email format",
            context={"field": "email", "value": "not-an-email"},
        )

        await tributum_error_handler(mock_request, error)

        # Verify span methods were called
        # Note: We need to check the call with a Status object
        status_call = mock_span.set_status.call_args[0][0]
        assert isinstance(status_call, Status)
        assert status_call.status_code == StatusCode.ERROR
        assert status_call.description == str(error)
        mock_span.set_attribute.assert_any_call("error.code", "VALIDATION_ERROR")
        mock_span.set_attribute.assert_any_call("error.severity", "LOW")
        assert mock_span.set_attribute.call_count >= 3  # code, severity, fingerprint

    async def test_high_severity_error_attributes(self, mocker: MockerFixture) -> None:
        """High severity errors should have proper attributes."""
        # Create mocks
        mock_request = mocker.Mock(spec=Request)
        mock_request.method = "GET"
        mock_request.url.path = "/test/endpoint"

        mock_span = mocker.Mock()
        mock_span.is_recording.return_value = True

        mocker.patch(
            "src.api.middleware.error_handler.trace.get_current_span",
            return_value=mock_span,
        )

        error = UnauthorizedError("Invalid API key")

        await tributum_error_handler(mock_request, error)

        mock_span.set_attribute.assert_any_call("error.severity", "HIGH")

    async def test_no_span_recording_no_error(self, mocker: MockerFixture) -> None:
        """Should handle gracefully when span is not recording."""
        # Create mocks
        mock_request = mocker.Mock(spec=Request)
        mock_request.method = "GET"
        mock_request.url.path = "/test/endpoint"

        mock_span = mocker.Mock()
        mock_span.is_recording.return_value = False

        mocker.patch(
            "src.api.middleware.error_handler.trace.get_current_span",
            return_value=mock_span,
        )

        error = NotFoundError("Resource not found")

        # Should not raise any errors
        await tributum_error_handler(mock_request, error)

        # Span methods should not be called
        mock_span.set_status.assert_not_called()
        mock_span.record_exception.assert_not_called()


@pytest.mark.unit
class TestGenericExceptionTracing:
    """Test OpenTelemetry tracing for generic exceptions."""

    async def test_generic_exception_records_in_span(
        self, mocker: MockerFixture
    ) -> None:
        """Generic exceptions should be recorded in span."""
        # Create mocks
        mock_request = mocker.Mock(spec=Request)
        mock_request.method = "GET"
        mock_request.url.path = "/test/endpoint"

        mock_span = mocker.Mock()
        mock_span.is_recording.return_value = True

        mocker.patch(
            "src.api.middleware.error_handler.trace.get_current_span",
            return_value=mock_span,
        )

        error = RuntimeError("Something went wrong")

        await generic_exception_handler(mock_request, error)

        # Verify Status object was created correctly
        status_call = mock_span.set_status.call_args[0][0]
        assert isinstance(status_call, Status)
        assert status_call.status_code == StatusCode.ERROR
        assert status_call.description == f"Unhandled exception: {type(error).__name__}"
        mock_span.set_attribute.assert_any_call("error.type", "RuntimeError")
        # Check that error.unexpected was set to "true"
        calls = [call[0] for call in mock_span.set_attribute.call_args_list]
        assert ("error.unexpected", "true") in calls


@pytest.mark.unit
class TestValidationErrorTracing:
    """Test OpenTelemetry tracing for validation errors."""

    async def test_validation_error_no_exception_recording(
        self, mocker: MockerFixture
    ) -> None:
        """Validation errors should not use record_exception."""
        # Create mocks
        mock_request = mocker.Mock(spec=Request)
        mock_request.method = "GET"
        mock_request.url.path = "/test/endpoint"

        mock_span = mocker.Mock()
        mock_span.is_recording.return_value = True

        mocker.patch(
            "src.api.middleware.error_handler.trace.get_current_span",
            return_value=mock_span,
        )

        # Create validation error with multiple fields
        validation_error = RequestValidationError(
            [
                {
                    "loc": ("body", "email"),
                    "msg": "invalid email format",
                    "type": "value_error.email",
                },
                {
                    "loc": ("body", "age"),
                    "msg": "ensure this value is greater than 0",
                    "type": "value_error.number.not_gt",
                },
            ]
        )

        await validation_error_handler(mock_request, validation_error)

        # Verify Status object was created correctly
        status_call = mock_span.set_status.call_args[0][0]
        assert isinstance(status_call, Status)
        assert status_call.status_code == StatusCode.ERROR
        # Should NOT call record_exception for validation errors
        mock_span.record_exception.assert_not_called()
        mock_span.set_attribute.assert_any_call("error.type", "ValidationError")
        mock_span.set_attribute.assert_any_call("error.validation_count", 2)


@pytest.mark.unit
class TestHTTPExceptionTracing:
    """Test OpenTelemetry tracing for HTTP exceptions."""

    async def test_http_exception_records_status_code(
        self, mocker: MockerFixture
    ) -> None:
        """HTTP exceptions should record status code in span."""
        # Create mocks
        mock_request = mocker.Mock(spec=Request)
        mock_request.method = "GET"
        mock_request.url.path = "/test/endpoint"

        mock_span = mocker.Mock()
        mock_span.is_recording.return_value = True

        mocker.patch(
            "src.api.middleware.error_handler.trace.get_current_span",
            return_value=mock_span,
        )

        error = HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resource not found",
        )

        await http_exception_handler(mock_request, error)

        # Verify Status object was created correctly
        status_call = mock_span.set_status.call_args[0][0]
        assert isinstance(status_call, Status)
        assert status_call.status_code == StatusCode.ERROR
        mock_span.set_attribute.assert_any_call("http.status_code", 404)
        mock_span.set_attribute.assert_any_call("error.type", "HTTPException")

    async def test_http_500_error_attributes(self, mocker: MockerFixture) -> None:
        """HTTP 500 errors should have proper attributes."""
        # Create mocks
        mock_request = mocker.Mock(spec=Request)
        mock_request.method = "GET"
        mock_request.url.path = "/test/endpoint"

        mock_span = mocker.Mock()
        mock_span.is_recording.return_value = True

        mocker.patch(
            "src.api.middleware.error_handler.trace.get_current_span",
            return_value=mock_span,
        )

        error = HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )

        await http_exception_handler(mock_request, error)

        mock_span.set_attribute.assert_any_call("http.status_code", 500)


@pytest.mark.unit
class TestSpanNotRecording:
    """Test behavior when span is not recording."""

    async def test_all_handlers_safe_when_no_span(self, mocker: MockerFixture) -> None:
        """All handlers should work safely when no span is recording."""
        # Create mocks
        mock_request = mocker.Mock(spec=Request)
        mock_request.method = "GET"
        mock_request.url.path = "/test/endpoint"

        # Create a span that's not recording
        mock_span = mocker.Mock()
        mock_span.is_recording.return_value = False

        mocker.patch(
            "src.api.middleware.error_handler.trace.get_current_span",
            return_value=mock_span,
        )

        # Test all handlers
        handlers_and_errors = [
            (tributum_error_handler, BusinessRuleError("Business rule violated")),
            (generic_exception_handler, ValueError("Invalid value")),
            (
                validation_error_handler,
                RequestValidationError(
                    [{"loc": ("body", "field"), "msg": "required", "type": "missing"}]
                ),
            ),
            (
                http_exception_handler,
                HTTPException(status_code=400, detail="Bad request"),
            ),
        ]

        for handler, error in handlers_and_errors:
            # Should not raise any errors
            await handler(mock_request, error)

        # Verify no span methods were called
        mock_span.set_status.assert_not_called()
        mock_span.record_exception.assert_not_called()
        mock_span.set_attribute.assert_not_called()
