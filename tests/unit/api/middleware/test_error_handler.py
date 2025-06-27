"""Unit tests for error handler middleware, focusing on metrics recording."""

from typing import cast

import pytest
from fastapi import HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError as PydanticValidationError
from pytest_mock import MockerFixture, MockType
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.api.middleware.error_handler import (
    generic_exception_handler,
    http_exception_handler,
    tributum_error_handler,
    validation_error_handler,
)
from src.core.exceptions import (
    BusinessRuleError,
    ErrorCode,
    NotFoundError,
    ValidationError,
)


@pytest.mark.unit
class TestErrorMetrics:
    """Test cases for error metrics recording in error handlers."""

    @pytest.fixture
    def mock_request(self, mocker: MockerFixture) -> MockType:
        """Create a mock request object."""
        request = mocker.Mock(spec=Request)
        request.method = "GET"
        request.url.path = "/test/endpoint"
        request.state.correlation_id = "test-correlation-id"
        request.query_params = {}
        return cast("MockType", request)

    @pytest.fixture
    def mock_error_counter(self, mocker: MockerFixture) -> MockType:
        """Mock the error counter metric instrument."""
        # Mock the error_counter at module level
        mock_counter = mocker.Mock()
        mocker.patch("src.api.middleware.error_handler.error_counter", mock_counter)
        return cast("MockType", mock_counter)

    async def test_tributum_error_handler_records_metrics(
        self,
        mock_request: MockType,
        mock_error_counter: MockType,
        mocker: MockerFixture,
    ) -> None:
        """Test that tributum_error_handler records error metrics."""
        # Mock logger and settings
        mocker.patch("src.api.middleware.error_handler.logger")
        mock_settings = mocker.Mock()
        mock_settings.app_name = "TestApp"
        mock_settings.app_version = "1.0.0"
        mock_settings.environment = "test"
        mocker.patch(
            "src.api.middleware.error_handler.get_settings", return_value=mock_settings
        )

        # Create a test error
        error = NotFoundError(
            message="Resource not found",
            context={"resource_id": "123"},
        )

        # Call the handler
        response = await tributum_error_handler(mock_request, error)

        # Verify response
        assert isinstance(response, Response)
        assert response.status_code == 404

        # Verify error metric was recorded
        mock_error_counter.add.assert_called_once_with(
            1,
            {
                "http.method": "GET",
                "http.route": "/test/endpoint",
                "http.status_code": "404",
                "error.type": "NotFoundError",
                "error.code": ErrorCode.NOT_FOUND.value,
            },
        )

    async def test_tributum_error_handler_business_rule_error_metrics(
        self,
        mock_request: MockType,
        mock_error_counter: MockType,
        mocker: MockerFixture,
    ) -> None:
        """Test metrics recording for BusinessRuleError (422 status)."""
        # Mock logger and settings
        mocker.patch("src.api.middleware.error_handler.logger")
        mock_settings = mocker.Mock()
        mock_settings.app_name = "TestApp"
        mock_settings.app_version = "1.0.0"
        mock_settings.environment = "test"
        mocker.patch(
            "src.api.middleware.error_handler.get_settings", return_value=mock_settings
        )

        # Create a business rule error
        error = BusinessRuleError(
            message="Business rule violated",
            context={"rule": "minimum_amount"},
        )

        # Call the handler
        response = await tributum_error_handler(mock_request, error)

        # Verify response
        assert response.status_code == 422

        # Verify error metric was recorded
        mock_error_counter.add.assert_called_once_with(
            1,
            {
                "http.method": "GET",
                "http.route": "/test/endpoint",
                "http.status_code": "422",
                "error.type": "BusinessRuleError",
                "error.code": ErrorCode.INTERNAL_ERROR.value,
            },
        )

    async def test_tributum_error_handler_validation_error_metrics(
        self,
        mock_request: MockType,
        mock_error_counter: MockType,
        mocker: MockerFixture,
    ) -> None:
        """Test metrics recording for custom ValidationError (400 status)."""
        # Mock logger and settings
        mocker.patch("src.api.middleware.error_handler.logger")
        mock_settings = mocker.Mock()
        mock_settings.app_name = "TestApp"
        mock_settings.app_version = "1.0.0"
        mock_settings.environment = "test"
        mocker.patch(
            "src.api.middleware.error_handler.get_settings", return_value=mock_settings
        )

        # Create our custom validation error
        error = ValidationError(
            message="Invalid input",
            context={"field": "email", "reason": "invalid format"},
        )

        # Call the handler
        response = await tributum_error_handler(mock_request, error)

        # Verify response
        assert response.status_code == 400

        # Verify error metric was recorded
        mock_error_counter.add.assert_called_once_with(
            1,
            {
                "http.method": "GET",
                "http.route": "/test/endpoint",
                "http.status_code": "400",
                "error.type": "ValidationError",
                "error.code": ErrorCode.VALIDATION_ERROR.value,
            },
        )

    async def test_tributum_error_handler_no_counter(
        self,
        mock_request: MockType,
        mocker: MockerFixture,
    ) -> None:
        """Test that handler works when error_counter is None."""
        # Mock logger and settings
        mocker.patch("src.api.middleware.error_handler.logger")
        mock_settings = mocker.Mock()
        mock_settings.app_name = "TestApp"
        mock_settings.app_version = "1.0.0"
        mock_settings.environment = "test"
        mocker.patch(
            "src.api.middleware.error_handler.get_settings", return_value=mock_settings
        )

        # Set error_counter to None
        mocker.patch("src.api.middleware.error_handler.error_counter", None)

        # Create a test error
        error = NotFoundError(message="Resource not found")

        # Call the handler - should not raise
        response = await tributum_error_handler(mock_request, error)

        # Verify response
        assert isinstance(response, Response)
        assert response.status_code == 404

    async def test_validation_error_handler_records_metrics(
        self,
        mock_request: MockType,
        mock_error_counter: MockType,
        mocker: MockerFixture,
    ) -> None:
        """Test that validation_error_handler records error metrics."""
        # Mock logger and settings
        mocker.patch("src.api.middleware.error_handler.logger")
        mock_settings = mocker.Mock()
        mock_settings.app_name = "TestApp"
        mock_settings.app_version = "1.0.0"
        mock_settings.environment = "test"
        mocker.patch(
            "src.api.middleware.error_handler.get_settings", return_value=mock_settings
        )

        # Create a RequestValidationError with mock errors
        pydantic_errors = [
            {
                "loc": ("body", "email"),
                "msg": "invalid email format",
                "type": "value_error.email",
            }
        ]
        # Create a mock Pydantic ValidationError
        mock_pydantic_error = mocker.Mock(spec=PydanticValidationError)
        mock_pydantic_error.errors.return_value = pydantic_errors

        # Create a RequestValidationError
        error = RequestValidationError(pydantic_errors, body={"email": "invalid"})

        # Call the handler
        response = await validation_error_handler(mock_request, error)

        # Verify response
        assert response.status_code == 422

        # Verify error metric was recorded
        mock_error_counter.add.assert_called_once_with(
            1,
            {
                "http.method": "GET",
                "http.route": "/test/endpoint",
                "http.status_code": "422",
                "error.type": "ValidationError",
                "error.code": ErrorCode.VALIDATION_ERROR.value,
            },
        )

    async def test_http_exception_handler_records_metrics(
        self,
        mock_request: MockType,
        mock_error_counter: MockType,
        mocker: MockerFixture,
    ) -> None:
        """Test that http_exception_handler records error metrics."""
        # Mock logger and settings
        mocker.patch("src.api.middleware.error_handler.logger")
        mock_settings = mocker.Mock()
        mock_settings.app_name = "TestApp"
        mock_settings.app_version = "1.0.0"
        mock_settings.environment = "test"
        mocker.patch(
            "src.api.middleware.error_handler.get_settings", return_value=mock_settings
        )

        # Create an HTTP exception
        error = HTTPException(status_code=403, detail="Forbidden")

        # Call the handler
        response = await http_exception_handler(mock_request, error)

        # Verify response
        assert response.status_code == 403

        # Verify error metric was recorded
        mock_error_counter.add.assert_called_once_with(
            1,
            {
                "http.method": "GET",
                "http.route": "/test/endpoint",
                "http.status_code": "403",
                "error.type": "HTTPException",
                "error.code": ErrorCode.INTERNAL_ERROR.value,
            },
        )

    async def test_generic_exception_handler_records_metrics(
        self,
        mock_request: MockType,
        mock_error_counter: MockType,
        mocker: MockerFixture,
    ) -> None:
        """Test that generic_exception_handler records error metrics."""
        # Mock logger and settings
        mocker.patch("src.api.middleware.error_handler.logger")
        mock_log_exception = mocker.patch(
            "src.api.middleware.error_handler.log_exception"
        )
        mock_settings = mocker.Mock()
        mock_settings.app_name = "TestApp"
        mock_settings.app_version = "1.0.0"
        mock_settings.environment = "development"
        mocker.patch(
            "src.api.middleware.error_handler.get_settings",
            return_value=mock_settings,
        )

        # Create a generic exception
        error = RuntimeError("Something went wrong")

        # Call the handler
        response = await generic_exception_handler(mock_request, error)

        # Verify response
        assert response.status_code == 500

        # Verify error metric was recorded
        mock_error_counter.add.assert_called_once_with(
            1,
            {
                "http.method": "GET",
                "http.route": "/test/endpoint",
                "http.status_code": "500",
                "error.type": "RuntimeError",
                "error.code": ErrorCode.INTERNAL_ERROR.value,
            },
        )

        # Verify exception was logged
        mock_log_exception.assert_called_once()

    async def test_starlette_http_exception_handler_records_metrics(
        self,
        mock_request: MockType,
        mock_error_counter: MockType,
        mocker: MockerFixture,
    ) -> None:
        """Test that http_exception_handler works with Starlette HTTPException."""
        # Mock logger and settings
        mocker.patch("src.api.middleware.error_handler.logger")
        mock_settings = mocker.Mock()
        mock_settings.app_name = "TestApp"
        mock_settings.app_version = "1.0.0"
        mock_settings.environment = "test"
        mocker.patch(
            "src.api.middleware.error_handler.get_settings", return_value=mock_settings
        )

        # Create a Starlette HTTP exception
        error = StarletteHTTPException(status_code=429, detail="Too Many Requests")

        # Call the handler
        response = await http_exception_handler(mock_request, error)

        # Verify response
        assert response.status_code == 429

        # Verify error metric was recorded
        mock_error_counter.add.assert_called_once_with(
            1,
            {
                "http.method": "GET",
                "http.route": "/test/endpoint",
                "http.status_code": "429",
                "error.type": "HTTPException",
                "error.code": ErrorCode.INTERNAL_ERROR.value,
            },
        )

    async def test_all_handlers_check_error_counter_exists(
        self,
        mock_request: MockType,
        mocker: MockerFixture,
    ) -> None:
        """Test that all handlers check if error_counter exists before using it."""
        # Mock logger and settings
        mocker.patch("src.api.middleware.error_handler.logger")
        mock_settings = mocker.Mock()
        mock_settings.app_name = "TestApp"
        mock_settings.app_version = "1.0.0"
        mock_settings.environment = "test"
        mocker.patch(
            "src.api.middleware.error_handler.get_settings", return_value=mock_settings
        )

        # Set error_counter to None
        mocker.patch("src.api.middleware.error_handler.error_counter", None)

        # Create a RequestValidationError for testing
        pydantic_errors = [
            {"loc": ("body",), "msg": "field required", "type": "value_error"}
        ]
        request_validation_error = RequestValidationError(pydantic_errors)

        # Test each handler with error_counter = None
        handlers_and_errors = [
            (tributum_error_handler, NotFoundError("Not found")),
            (validation_error_handler, request_validation_error),
            (http_exception_handler, HTTPException(status_code=400, detail="Bad")),
            (generic_exception_handler, RuntimeError("Error")),
        ]

        for handler, error in handlers_and_errors:
            # Call handler - should not raise
            response = await handler(mock_request, error)
            assert isinstance(response, Response)
