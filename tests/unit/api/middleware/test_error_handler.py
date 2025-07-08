"""Unit tests for API middleware error handler.

This module tests all error handling functionality in the middleware error handler,
including exception type mapping, response formatting, logging, and OpenTelemetry.
"""

import asyncio
from typing import cast

import pytest
from fastapi import status
from fastapi.exceptions import RequestValidationError
from pytest_mock import MockType
from starlette.exceptions import HTTPException

from src.api.middleware.error_handler import (
    generic_exception_handler,
    get_service_info,
    http_exception_handler,
    register_exception_handlers,
    tributum_error_handler,
    validation_error_handler,
)
from src.api.schemas.errors import ServiceInfo
from src.core.config import Settings
from src.core.exceptions import (
    ErrorCode,
    TributumError,
)


@pytest.mark.unit
class TestErrorHandler:
    """Test suite for error handler middleware."""

    # Test get_service_info function

    def test_get_service_info_returns_correct_metadata(
        self,
        mock_settings: Settings,
    ) -> None:
        """Test get_service_info correctly extracts service metadata from settings."""
        # Execution
        result = get_service_info(mock_settings)

        # Assertions
        assert isinstance(result, ServiceInfo)
        assert result.name == mock_settings.app_name
        assert result.version == mock_settings.app_version
        assert result.environment == mock_settings.environment

    # Test tributum_error_handler

    @pytest.mark.timeout(5)
    async def test_tributum_error_handler_handles_tributum_errors(
        self,
        mock_request: MockType,
        mock_tributum_errors: dict[str, TributumError],
        mock_error_handler_dependencies: dict[str, MockType],
        mock_error_response: MockType,
        mock_orjson_response: MockType,
    ) -> None:
        """Test basic TributumError handling with proper response format."""
        # Setup
        error = mock_tributum_errors["basic"]
        deps = mock_error_handler_dependencies

        # Execution
        response = await tributum_error_handler(mock_request, error)

        # Assertions
        assert response == mock_orjson_response.instance
        assert (
            mock_orjson_response.instance.status_code
            == status.HTTP_500_INTERNAL_SERVER_ERROR
        )

        # Verify logger called with warning for expected error
        deps["logger"].warning.assert_called_once()
        log_call = deps["logger"].warning.call_args
        assert "Handling expected error" in log_call[0][0]
        assert log_call[1]["correlation_id"] == "test-correlation-123"
        assert log_call[1]["extra"]["alert"] is False

        # Verify span attributes set
        span = deps["span"]
        span.set_status.assert_called_once()
        span.set_attribute.assert_any_call("error.code", error.error_code)
        span.set_attribute.assert_any_call("error.severity", error.severity.value)
        span.set_attribute.assert_any_call("error.fingerprint", error.fingerprint)

        # Verify error response created with sanitized context
        mock_error_response.assert_called_once()
        call_args = mock_error_response.call_args[1]
        assert call_args["error_code"] == error.error_code
        assert call_args["message"] == error.message
        assert call_args["correlation_id"] == "test-correlation-123"
        assert call_args["request_id"] == "req-test-456"
        assert call_args["severity"] == error.severity.value

    @pytest.mark.timeout(5)
    @pytest.mark.parametrize(
        ("error_type", "expected_status"),
        [
            ("validation", status.HTTP_400_BAD_REQUEST),
            ("not_found", status.HTTP_404_NOT_FOUND),
            ("unauthorized", status.HTTP_401_UNAUTHORIZED),
            ("business_rule", status.HTTP_422_UNPROCESSABLE_ENTITY),
            ("basic", status.HTTP_500_INTERNAL_SERVER_ERROR),
        ],
    )
    @pytest.mark.usefixtures("mock_error_handler_dependencies")
    async def test_tributum_error_handler_maps_error_types_to_status_codes(
        self,
        error_type: str,
        expected_status: int,
        mock_request: MockType,
        mock_tributum_errors: dict[str, TributumError],
        mock_orjson_response: MockType,
    ) -> None:
        """Test correct HTTP status code mapping for TributumError subclasses."""
        # Setup
        error = mock_tributum_errors[error_type]

        # Execution
        response = await tributum_error_handler(mock_request, error)

        # Assertions
        assert response == mock_orjson_response.instance
        assert mock_orjson_response.instance.status_code == expected_status

    @pytest.mark.timeout(5)
    @pytest.mark.parametrize("environment", ["development", "production", "staging"])
    @pytest.mark.usefixtures("mock_error_handler_dependencies")
    async def test_tributum_error_handler_includes_debug_info_in_development(
        self,
        environment: str,
        mock_request: MockType,
        mock_tributum_errors: dict[str, TributumError],
        mock_error_response: MockType,
        mock_settings: Settings,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test debug information included only in development environment."""
        # Setup
        monkeypatch.setattr(mock_settings, "environment", environment)
        error = mock_tributum_errors["with_cause"]

        # Execution
        await tributum_error_handler(mock_request, error)

        # Assertions
        call_args = mock_error_response.call_args[1]
        if environment == "development":
            assert call_args["debug_info"] is not None
            debug_info = call_args["debug_info"]
            assert "stack_trace" in debug_info
            assert "error_context" in debug_info
            assert "exception_type" in debug_info
            assert "cause" in debug_info
            assert debug_info["cause"]["type"] == "ValueError"
            assert debug_info["cause"]["message"] == "Original database error"
        else:
            assert call_args["debug_info"] is None

    @pytest.mark.timeout(5)
    async def test_tributum_error_handler_raises_type_error_for_wrong_exception_type(
        self,
        mock_request: MockType,
        mock_error_handler_dependencies: dict[str, MockType],
    ) -> None:
        """Test handler raises TypeError if passed non-TributumError."""
        # Setup
        generic_error = Exception("Not a TributumError")

        # Execution & Assertions
        with pytest.raises(TypeError, match="Expected TributumError, got Exception"):
            await tributum_error_handler(mock_request, generic_error)

        # Verify no logging or response creation
        mock_error_handler_dependencies["logger"].warning.assert_not_called()
        mock_error_handler_dependencies["logger"].error.assert_not_called()

    @pytest.mark.timeout(5)
    @pytest.mark.usefixtures("mock_orjson_response")
    async def test_tributum_error_handler_logs_unexpected_errors_with_alert(
        self,
        mock_request: MockType,
        mock_tributum_errors: dict[str, TributumError],
        mock_error_handler_dependencies: dict[str, MockType],
    ) -> None:
        """Test unexpected TributumErrors trigger alerts and critical severity."""
        # Setup
        critical_error = mock_tributum_errors["critical"]
        deps = mock_error_handler_dependencies

        # Execution
        await tributum_error_handler(mock_request, critical_error)

        # Assertions - should use logger.error for critical errors
        deps["logger"].error.assert_called_once()
        log_call = deps["logger"].error.call_args
        assert "Handling unexpected error" in log_call[0][0]
        assert log_call[1]["extra"]["alert"] is True
        assert log_call[1]["extra"]["notify_oncall"] is True

    @pytest.mark.timeout(5)
    async def test_tributum_error_handler_sanitizes_sensitive_context(
        self,
        mock_request: MockType,
        mock_tributum_errors: dict[str, TributumError],
        mock_error_handler_dependencies: dict[str, MockType],
        mock_error_response: MockType,
    ) -> None:
        """Test that sensitive data is sanitized in error responses."""
        # Setup
        error = mock_tributum_errors["with_sensitive_data"]
        deps = mock_error_handler_dependencies

        # Execution
        await tributum_error_handler(mock_request, error)

        # Assertions
        # Verify sanitize_error_context was called
        deps["sanitize_error_context"].assert_called_once_with(
            error,
            {
                "request_method": mock_request.method,
                "request_path": str(mock_request.url.path),
                "error_code": error.error_code,
            },
        )

        # Verify sanitize_dict was called for details (and possibly debug_info)
        assert deps["sanitize_dict"].call_count >= 1

        # Verify sanitized data in response
        call_args = mock_error_response.call_args[1]
        details = call_args["details"]
        assert "password" not in details or details["password"] == "[REDACTED]"

    # Test validation_error_handler

    @pytest.mark.timeout(5)
    @pytest.mark.usefixtures("mock_error_handler_dependencies")
    async def test_validation_error_handler_extracts_field_errors(
        self,
        mock_request: MockType,
        mock_validation_errors: dict[str, RequestValidationError],
        mock_error_response: MockType,
        mock_orjson_response: MockType,
    ) -> None:
        """Test correct extraction and grouping of field-level validation errors."""
        # Setup
        error = mock_validation_errors["multiple"]

        # Execution
        response = await validation_error_handler(mock_request, error)

        # Assertions
        assert response == mock_orjson_response.instance
        assert (
            mock_orjson_response.instance.status_code
            == status.HTTP_422_UNPROCESSABLE_ENTITY
        )

        # Verify error response structure
        call_args = mock_error_response.call_args[1]
        assert call_args["error_code"] == ErrorCode.VALIDATION_ERROR.value
        assert call_args["message"] == "Request validation failed"
        assert call_args["severity"] == "LOW"

        # Check field errors
        validation_errors = call_args["details"]["validation_errors"]
        assert "email" in validation_errors
        assert "age" in validation_errors
        assert "name" in validation_errors
        assert validation_errors["email"] == ["value is not a valid email address"]
        assert validation_errors["age"] == ["ensure this value is greater than 0"]
        assert validation_errors["name"] == ["field required"]

    @pytest.mark.timeout(5)
    @pytest.mark.usefixtures("mock_error_handler_dependencies")
    async def test_validation_error_handler_handles_nested_fields(
        self,
        mock_request: MockType,
        mock_validation_errors: dict[str, RequestValidationError],
        mock_error_response: MockType,
    ) -> None:
        """Test nested field paths are correctly converted to dot notation."""
        # Setup
        error = mock_validation_errors["nested"]

        # Execution
        await validation_error_handler(mock_request, error)

        # Assertions
        call_args = mock_error_response.call_args[1]
        validation_errors = call_args["details"]["validation_errors"]
        assert "address.street" in validation_errors
        assert "address.city" in validation_errors
        assert "address.zip_code" in validation_errors

    @pytest.mark.timeout(5)
    @pytest.mark.usefixtures("mock_error_handler_dependencies")
    async def test_validation_error_handler_handles_root_errors(
        self,
        mock_request: MockType,
        mock_validation_errors: dict[str, RequestValidationError],
        mock_error_response: MockType,
    ) -> None:
        """Test root-level validation errors are labeled correctly."""
        # Setup
        error = mock_validation_errors["root"]

        # Execution
        await validation_error_handler(mock_request, error)

        # Assertions
        call_args = mock_error_response.call_args[1]
        validation_errors = call_args["details"]["validation_errors"]
        assert "root" in validation_errors
        assert validation_errors["root"] == ["passwords do not match"]

    @pytest.mark.timeout(5)
    @pytest.mark.usefixtures("mock_error_handler_dependencies")
    async def test_validation_error_handler_groups_multiple_errors_per_field(
        self,
        mock_request: MockType,
        mock_validation_errors: dict[str, RequestValidationError],
        mock_error_response: MockType,
    ) -> None:
        """Test multiple errors for the same field are grouped together."""
        # Setup
        error = mock_validation_errors["same_field"]

        # Execution
        await validation_error_handler(mock_request, error)

        # Assertions
        call_args = mock_error_response.call_args[1]
        validation_errors = call_args["details"]["validation_errors"]
        assert "password" in validation_errors
        assert len(validation_errors["password"]) == 3
        assert (
            "ensure this value has at least 8 characters"
            in validation_errors["password"]
        )
        assert (
            "password must contain at least one uppercase letter"
            in validation_errors["password"]
        )
        assert (
            "password must contain at least one number" in validation_errors["password"]
        )

    @pytest.mark.timeout(5)
    async def test_validation_error_handler_records_span_attributes(
        self,
        mock_request: MockType,
        mock_validation_errors: dict[str, RequestValidationError],
        mock_error_handler_dependencies: dict[str, MockType],
    ) -> None:
        """Test span attributes set correctly for validation errors."""
        # Setup
        error = mock_validation_errors["multiple"]
        span = mock_error_handler_dependencies["span"]

        # Execution
        await validation_error_handler(mock_request, error)

        # Assertions
        span.set_status.assert_called_once()
        # The Status object is created, check if it was called with correct params
        deps = mock_error_handler_dependencies
        deps["Status"].assert_called_once()
        status_args = deps["Status"].call_args
        assert status_args[1]["description"] == "Request validation failed"

        span.set_attribute.assert_any_call("error.type", "ValidationError")
        span.set_attribute.assert_any_call("error.validation_count", 3)

    @pytest.mark.timeout(5)
    @pytest.mark.usefixtures("mock_error_handler_dependencies")
    async def test_validation_error_handler_raises_type_error_for_wrong_type(
        self,
        mock_request: MockType,
    ) -> None:
        """Test handler raises TypeError if passed non-RequestValidationError."""
        # Setup
        generic_error = Exception("Not a validation error")

        # Execution & Assertions
        with pytest.raises(
            TypeError, match="Expected RequestValidationError, got Exception"
        ):
            await validation_error_handler(mock_request, generic_error)

    # Test http_exception_handler

    @pytest.mark.timeout(5)
    @pytest.mark.parametrize(
        ("status_code", "expected_error_code", "expected_severity"),
        [
            (400, ErrorCode.VALIDATION_ERROR.value, "LOW"),
            (401, ErrorCode.UNAUTHORIZED.value, "HIGH"),
            (404, ErrorCode.NOT_FOUND.value, "LOW"),
            (500, ErrorCode.INTERNAL_ERROR.value, "HIGH"),
            (503, ErrorCode.INTERNAL_ERROR.value, "HIGH"),
        ],
    )
    @pytest.mark.usefixtures("mock_error_handler_dependencies")
    async def test_http_exception_handler_maps_status_codes_correctly(
        self,
        status_code: int,
        expected_error_code: str,
        expected_severity: str,
        mock_request: MockType,
        mock_http_exceptions: dict[str, HTTPException],
        mock_error_response: MockType,
        mock_orjson_response: MockType,
    ) -> None:
        """Test HTTP status codes map to appropriate error codes and severities."""
        # Setup
        error = mock_http_exceptions[str(status_code)]

        # Execution
        response = await http_exception_handler(mock_request, error)

        # Assertions
        assert response == mock_orjson_response.instance
        assert mock_orjson_response.instance.status_code == status_code

        # Verify error response
        call_args = mock_error_response.call_args[1]
        assert call_args["error_code"] == expected_error_code
        assert call_args["severity"] == expected_severity
        assert call_args["message"] == str(error.detail)

    @pytest.mark.timeout(5)
    @pytest.mark.usefixtures("mock_error_handler_dependencies")
    async def test_http_exception_handler_raises_type_error_for_wrong_type(
        self,
        mock_request: MockType,
    ) -> None:
        """Test handler raises TypeError if passed non-HTTPException."""
        # Setup
        generic_error = Exception("Not an HTTP exception")

        # Execution & Assertions
        with pytest.raises(TypeError, match="Expected HTTPException, got Exception"):
            await http_exception_handler(mock_request, generic_error)

    @pytest.mark.timeout(5)
    async def test_http_exception_handler_records_span_attributes(
        self,
        mock_request: MockType,
        mock_http_exceptions: dict[str, HTTPException],
        mock_error_handler_dependencies: dict[str, MockType],
    ) -> None:
        """Test span attributes set correctly for HTTP exceptions."""
        # Setup
        error = mock_http_exceptions["404"]
        span = mock_error_handler_dependencies["span"]

        # Execution
        await http_exception_handler(mock_request, error)

        # Assertions
        span.set_status.assert_called_once()
        span.set_attribute.assert_any_call("http.status_code", 404)
        span.set_attribute.assert_any_call("error.type", "HTTPException")

    # Test generic_exception_handler

    @pytest.mark.timeout(5)
    @pytest.mark.parametrize("environment", ["development", "production"])
    @pytest.mark.usefixtures("mock_error_handler_dependencies")
    async def test_generic_exception_handler_hides_details_in_production(
        self,
        environment: str,
        mock_request: MockType,
        mock_generic_exceptions: dict[str, Exception],
        mock_error_response: MockType,
        mock_settings: Settings,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test generic exceptions hide details in production."""
        # Setup
        monkeypatch.setattr(mock_settings, "environment", environment)
        error = mock_generic_exceptions["value_error"]

        # Execution
        await generic_exception_handler(mock_request, error)

        # Assertions
        call_args = mock_error_response.call_args[1]

        if environment == "production":
            assert call_args["message"] == "An internal server error occurred"
            assert call_args["details"] is None
            assert call_args["debug_info"] is None
        else:
            assert call_args["message"] == "Internal server error: ValueError"
            assert call_args["details"] is not None
            assert call_args["details"]["error"] == "Invalid value provided"
            assert call_args["details"]["type"] == "ValueError"
            assert call_args["debug_info"] is not None
            assert "stack_trace" in call_args["debug_info"]
            assert "error_context" in call_args["debug_info"]
            assert "exception_type" in call_args["debug_info"]

    @pytest.mark.timeout(5)
    async def test_generic_exception_handler_logs_with_alert_flags(
        self,
        mock_request: MockType,
        mock_generic_exceptions: dict[str, Exception],
        mock_error_handler_dependencies: dict[str, MockType],
    ) -> None:
        """Test generic exceptions always trigger alerts and proper logging."""
        # Setup
        error = mock_generic_exceptions["runtime_error"]
        logger = mock_error_handler_dependencies["logger"]

        # Execution
        await generic_exception_handler(mock_request, error)

        # Assertions
        logger.exception.assert_called_once()
        log_call = logger.exception.call_args
        assert "Unhandled exception: {exception_type}" in log_call[0][0]
        assert log_call[1]["exception_type"] == "RuntimeError"
        assert log_call[1]["correlation_id"] == "test-correlation-123"
        assert log_call[1]["extra"]["alert"] is True
        assert log_call[1]["extra"]["is_expected"] is False
        assert log_call[1]["extra"]["error_category"] == "system_error"

    @pytest.mark.timeout(5)
    async def test_generic_exception_handler_records_span_attributes(
        self,
        mock_request: MockType,
        mock_generic_exceptions: dict[str, Exception],
        mock_error_handler_dependencies: dict[str, MockType],
    ) -> None:
        """Test span attributes set correctly for generic exceptions."""
        # Setup
        error = mock_generic_exceptions["type_error"]
        span = mock_error_handler_dependencies["span"]

        # Execution
        await generic_exception_handler(mock_request, error)

        # Assertions
        span.set_status.assert_called_once()
        span.set_attribute.assert_any_call("error.type", "TypeError")
        span.set_attribute.assert_any_call("error.unexpected", "true")

    @pytest.mark.timeout(5)
    @pytest.mark.usefixtures("mock_error_handler_dependencies")
    async def test_generic_exception_handler_handles_various_exception_types(
        self,
        mock_request: MockType,
        mock_generic_exceptions: dict[str, Exception],
        mock_error_response: MockType,
    ) -> None:
        """Test handler works with various exception types including edge cases."""
        # Test with exception that has args
        error = mock_generic_exceptions["with_args"]
        await generic_exception_handler(mock_request, error)

        # Should not crash and should create response
        mock_error_response.assert_called()
        call_args = mock_error_response.call_args[1]
        assert call_args["severity"] == "CRITICAL"

    # Test register_exception_handlers

    @pytest.mark.timeout(5)
    async def test_register_exception_handlers_registers_all_handlers(
        self,
        mock_fastapi_app: MockType,
        mock_error_handler_dependencies: dict[str, MockType],
    ) -> None:
        """Test all exception handlers registered with FastAPI app."""
        # Setup
        logger = mock_error_handler_dependencies["logger"]

        # Execution
        register_exception_handlers(mock_fastapi_app)

        # Assertions
        assert mock_fastapi_app.add_exception_handler.call_count == 4

        # Check each handler registration
        calls = mock_fastapi_app.add_exception_handler.call_args_list
        registered_handlers = {call[0][0]: call[0][1] for call in calls}

        assert TributumError in registered_handlers
        assert registered_handlers[TributumError] == tributum_error_handler

        assert RequestValidationError in registered_handlers
        assert registered_handlers[RequestValidationError] == validation_error_handler

        assert HTTPException in registered_handlers
        assert registered_handlers[HTTPException] == http_exception_handler

        assert Exception in registered_handlers
        assert registered_handlers[Exception] == generic_exception_handler

        # Verify logger called
        logger.info.assert_called_once_with("Exception handlers registered")

    # Test edge cases and integration scenarios

    @pytest.mark.timeout(5)
    @pytest.mark.usefixtures("mock_error_handler_dependencies")
    async def test_handlers_handle_empty_and_none_values(
        self,
        mock_request: MockType,
        mock_error_response: MockType,
    ) -> None:
        """Test handlers gracefully handle empty messages and None contexts."""
        # Test with empty message
        empty_error = TributumError(
            error_code=ErrorCode.INTERNAL_ERROR,
            message="",
            context=None,
        )
        await tributum_error_handler(mock_request, empty_error)

        # Should not crash
        mock_error_response.assert_called()
        call_args = mock_error_response.call_args[1]
        assert call_args["message"] == ""
        assert (
            call_args["details"] is None
        )  # None context should result in None details

        # Test with empty context
        mock_error_response.reset_mock()
        empty_context_error = TributumError(
            error_code=ErrorCode.INTERNAL_ERROR,
            message="Error with empty context",
            context={},
        )
        await tributum_error_handler(mock_request, empty_context_error)

        # Should handle empty dict
        mock_error_response.assert_called()

    @pytest.mark.timeout(5)
    @pytest.mark.usefixtures("mock_error_handler_dependencies")
    async def test_all_handlers_include_correlation_id(
        self,
        mock_request: MockType,
        mock_tributum_errors: dict[str, TributumError],
        mock_validation_errors: dict[str, RequestValidationError],
        mock_http_exceptions: dict[str, HTTPException],
        mock_generic_exceptions: dict[str, Exception],
        mock_error_response: MockType,
    ) -> None:
        """Test all handlers properly include correlation ID in responses and logs."""
        correlation_id = "test-correlation-123"

        # Test TributumError handler
        await tributum_error_handler(mock_request, mock_tributum_errors["basic"])
        assert mock_error_response.call_args[1]["correlation_id"] == correlation_id

        # Test validation error handler
        mock_error_response.reset_mock()
        await validation_error_handler(mock_request, mock_validation_errors["single"])
        assert mock_error_response.call_args[1]["correlation_id"] == correlation_id

        # Test HTTP exception handler
        mock_error_response.reset_mock()
        await http_exception_handler(mock_request, mock_http_exceptions["404"])
        assert mock_error_response.call_args[1]["correlation_id"] == correlation_id

        # Test generic exception handler
        mock_error_response.reset_mock()
        await generic_exception_handler(
            mock_request, mock_generic_exceptions["value_error"]
        )
        assert mock_error_response.call_args[1]["correlation_id"] == correlation_id

    @pytest.mark.timeout(5)
    @pytest.mark.parametrize("is_recording", [True, False])
    async def test_all_handlers_record_span_when_recording(
        self,
        is_recording: bool,
        mock_request: MockType,
        mock_tributum_errors: dict[str, TributumError],
        mock_error_handler_dependencies: dict[str, MockType],
    ) -> None:
        """Test handlers only record span attributes when span is recording."""
        # Setup
        span = mock_error_handler_dependencies["span"]
        span.is_recording.return_value = is_recording
        span.reset_mock()

        # Execution
        await tributum_error_handler(mock_request, mock_tributum_errors["basic"])

        # Assertions
        if is_recording:
            span.set_status.assert_called()
            span.set_attribute.assert_called()
        else:
            span.set_status.assert_not_called()
            span.set_attribute.assert_not_called()

    @pytest.mark.timeout(10)
    @pytest.mark.usefixtures("mock_tributum_errors")
    async def test_handlers_thread_safe_with_concurrent_requests(
        self,
        mock_request: MockType,
        mock_error_handler_dependencies: dict[str, MockType],
        mock_error_response: MockType,
    ) -> None:
        """Test handlers work correctly with concurrent requests."""
        # Setup
        results = []
        call_count = 0

        # Mock the error response to capture multiple calls
        def capture_response(
            *, correlation_id: str | None = None, **_kwargs: object
        ) -> MockType:
            nonlocal call_count
            call_count += 1
            results.append(
                {
                    "call_num": call_count,
                    "correlation_id": correlation_id,
                }
            )
            return cast("MockType", mock_error_response.return_value)

        mock_error_response.side_effect = capture_response

        async def handle_error(correlation_id: str) -> None:
            """Handle error with specific correlation ID."""
            # Mock different correlation ID for each task
            mock_error_handler_dependencies[
                "get_correlation_id"
            ].return_value = correlation_id

            # Handle error
            error = TributumError(
                error_code=ErrorCode.INTERNAL_ERROR,
                message=f"Error from {correlation_id}",
            )
            await tributum_error_handler(mock_request, error)

        # Create tasks for concurrent execution
        tasks = [handle_error(f"corr-{i}") for i in range(3)]

        # Wait for all tasks
        await asyncio.gather(*tasks)

        # Assertions
        assert len(results) == 3, f"Expected 3 results, got {len(results)}"

        # Check that each correlation ID was captured
        correlation_ids = {r["correlation_id"] for r in results}
        expected_ids = {f"corr-{i}" for i in range(3)}
        assert correlation_ids == expected_ids, (
            f"Expected {expected_ids}, got {correlation_ids}"
        )

    @pytest.mark.timeout(5)
    async def test_all_handlers_include_correct_logger_extra_fields(
        self,
        mock_request: MockType,
        mock_tributum_errors: dict[str, TributumError],
        mock_generic_exceptions: dict[str, Exception],
        mock_error_handler_dependencies: dict[str, MockType],
    ) -> None:
        """Test all handlers pass correct extra fields to logger."""
        logger = mock_error_handler_dependencies["logger"]

        # Test expected TributumError
        basic_error = mock_tributum_errors["basic"]
        await tributum_error_handler(mock_request, basic_error)

        log_call = logger.warning.call_args
        assert log_call[1]["extra"]["alert"] is False

        # Test critical TributumError
        logger.reset_mock()
        critical_error = mock_tributum_errors["critical"]
        await tributum_error_handler(mock_request, critical_error)

        log_call = logger.error.call_args
        assert log_call[1]["extra"]["alert"] is True
        assert log_call[1]["extra"]["notify_oncall"] is True

        # Test generic exception
        logger.reset_mock()
        generic_error = mock_generic_exceptions["runtime_error"]
        await generic_exception_handler(mock_request, generic_error)

        log_call = logger.exception.call_args
        assert log_call[1]["extra"]["alert"] is True
        assert log_call[1]["extra"]["is_expected"] is False
        assert log_call[1]["extra"]["error_category"] == "system_error"
