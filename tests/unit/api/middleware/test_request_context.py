"""Unit tests for RequestContextMiddleware.

This module contains comprehensive unit tests for the RequestContextMiddleware class,
which manages correlation IDs for distributed tracing across service boundaries.
"""

import asyncio
from typing import Any

import pytest
from pytest_mock import MockerFixture, MockType
from starlette.middleware.base import RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from src.api.middleware.request_context import (
    CORRELATION_ID_HEADER,
    RequestContextMiddleware,
)
from src.core.context import RequestContext


@pytest.mark.unit
class TestRequestContextMiddleware:
    """Test suite for RequestContextMiddleware."""

    @pytest.mark.usefixtures("clean_context")
    async def test_middleware_generates_correlation_id_when_not_present(
        self,
        mock_starlette_request: MockType,
        mock_starlette_response: MockType,
        mock_starlette_call_next: MockType,
        request_context_middleware: RequestContextMiddleware,
        mocker: MockerFixture,
    ) -> None:
        """Test middleware generates a new UUID4 correlation ID when not present."""
        # Arrange
        test_uuid = "test-uuid-12345678-1234-5678-1234-567812345678"
        mock_uuid = mocker.patch("src.api.middleware.request_context.uuid.uuid4")
        mock_uuid.return_value = test_uuid

        mock_ctx = mocker.MagicMock()
        mock_ctx.__enter__ = mocker.MagicMock(return_value=None)
        mock_ctx.__exit__ = mocker.MagicMock(return_value=None)

        mock_contextualize = mocker.patch(
            "src.api.middleware.request_context.logger.contextualize"
        )
        mock_contextualize.return_value = mock_ctx

        mock_set_correlation_id = mocker.patch(
            "src.api.middleware.request_context.RequestContext.set_correlation_id"
        )

        # Act
        result = await request_context_middleware.dispatch(
            mock_starlette_request, mock_starlette_call_next
        )

        # Assert
        assert result is mock_starlette_response
        mock_uuid.assert_called_once()
        mock_set_correlation_id.assert_called_once_with(test_uuid)
        mock_contextualize.assert_called_once_with(correlation_id=test_uuid)
        assert mock_ctx.__enter__.called
        assert mock_ctx.__exit__.called
        assert mock_starlette_response.headers[CORRELATION_ID_HEADER] == test_uuid

    @pytest.mark.usefixtures("clean_context")
    async def test_middleware_uses_existing_correlation_id_from_header(
        self,
        mock_starlette_request: MockType,
        mock_starlette_response: MockType,
        mock_starlette_call_next: MockType,
        request_context_middleware: RequestContextMiddleware,
        mocker: MockerFixture,
    ) -> None:
        """Test middleware uses correlation ID from X-Correlation-ID header."""
        # Arrange
        existing_correlation_id = "existing-correlation-id-123"
        mock_starlette_request.headers = {
            CORRELATION_ID_HEADER: existing_correlation_id
        }

        mock_uuid = mocker.patch("src.api.middleware.request_context.uuid.uuid4")

        mock_ctx = mocker.MagicMock()
        mock_ctx.__enter__ = mocker.MagicMock(return_value=None)
        mock_ctx.__exit__ = mocker.MagicMock(return_value=None)

        mock_contextualize = mocker.patch(
            "src.api.middleware.request_context.logger.contextualize"
        )
        mock_contextualize.return_value = mock_ctx

        mock_set_correlation_id = mocker.patch(
            "src.api.middleware.request_context.RequestContext.set_correlation_id"
        )

        # Act
        result = await request_context_middleware.dispatch(
            mock_starlette_request, mock_starlette_call_next
        )

        # Assert
        assert result is mock_starlette_response
        mock_uuid.assert_not_called()  # UUID should NOT be generated
        mock_set_correlation_id.assert_called_once_with(existing_correlation_id)
        mock_contextualize.assert_called_once_with(
            correlation_id=existing_correlation_id
        )
        assert (
            mock_starlette_response.headers[CORRELATION_ID_HEADER]
            == existing_correlation_id
        )

    @pytest.mark.usefixtures("clean_context")
    async def test_middleware_sets_correlation_id_in_response_headers(
        self,
        mock_starlette_request: MockType,
        mock_starlette_response: MockType,
        mock_starlette_call_next: MockType,
        request_context_middleware: RequestContextMiddleware,
    ) -> None:
        """Test that middleware adds X-Correlation-ID header to response."""
        # Arrange
        correlation_id = "test-correlation-id-789"
        mock_starlette_request.headers = {CORRELATION_ID_HEADER: correlation_id}

        # Act
        result = await request_context_middleware.dispatch(
            mock_starlette_request, mock_starlette_call_next
        )

        # Assert
        assert result is mock_starlette_response
        assert CORRELATION_ID_HEADER in mock_starlette_response.headers
        assert mock_starlette_response.headers[CORRELATION_ID_HEADER] == correlation_id

    @pytest.mark.usefixtures("clean_context", "mock_starlette_response")
    async def test_middleware_propagates_correlation_id_through_context(
        self,
        mock_starlette_request: MockType,
        mock_starlette_call_next: MockType,
        request_context_middleware: RequestContextMiddleware,
        mocker: MockerFixture,
    ) -> None:
        """Test that correlation ID is set in RequestContext for propagation."""
        # Arrange
        correlation_id = "propagation-test-id-456"
        mock_starlette_request.headers = {CORRELATION_ID_HEADER: correlation_id}

        # Spy on RequestContext.set_correlation_id
        spy_set_correlation_id = mocker.spy(RequestContext, "set_correlation_id")

        # Act
        await request_context_middleware.dispatch(
            mock_starlette_request, mock_starlette_call_next
        )

        # Assert
        spy_set_correlation_id.assert_called_once_with(correlation_id)

    @pytest.mark.usefixtures("clean_context", "mock_starlette_response")
    async def test_middleware_uses_loguru_contextualize_for_request_scope(
        self,
        mock_starlette_request: MockType,
        mock_starlette_call_next: MockType,
        request_context_middleware: RequestContextMiddleware,
        mocker: MockerFixture,
    ) -> None:
        """Test that middleware uses logger.contextualize as context manager."""
        # Arrange
        correlation_id = "logger-test-id-123"
        mock_starlette_request.headers = {CORRELATION_ID_HEADER: correlation_id}

        # Track context manager usage
        ctx_enter_called = False
        ctx_exit_called = False

        def mock_enter(*_args: object, **_kwargs: object) -> None:
            nonlocal ctx_enter_called
            ctx_enter_called = True

        def mock_exit(*_args: object, **_kwargs: object) -> None:
            nonlocal ctx_exit_called
            ctx_exit_called = True

        mock_ctx = mocker.MagicMock()
        mock_ctx.__enter__ = mocker.MagicMock(side_effect=mock_enter)
        mock_ctx.__exit__ = mocker.MagicMock(side_effect=mock_exit)

        mock_contextualize = mocker.patch(
            "src.api.middleware.request_context.logger.contextualize",
            return_value=mock_ctx,
        )

        # Act
        await request_context_middleware.dispatch(
            mock_starlette_request, mock_starlette_call_next
        )

        # Assert
        mock_contextualize.assert_called_once_with(correlation_id=correlation_id)
        assert ctx_enter_called
        assert ctx_exit_called

    @pytest.mark.usefixtures("clean_context")
    async def test_middleware_handles_request_processing_errors(
        self,
        mock_starlette_request: MockType,
        mock_starlette_call_next: MockType,
        request_context_middleware: RequestContextMiddleware,
        mocker: MockerFixture,
    ) -> None:
        """Test middleware behavior when call_next raises an exception."""
        # Arrange
        test_error = ValueError("Test error during request processing")
        mock_starlette_call_next.side_effect = test_error

        mock_ctx = mocker.MagicMock()
        mock_ctx.__enter__ = mocker.MagicMock(return_value=None)
        mock_ctx.__exit__ = mocker.MagicMock(return_value=None)

        mock_contextualize = mocker.patch(
            "src.api.middleware.request_context.logger.contextualize"
        )
        mock_contextualize.return_value = mock_ctx

        # Act & Assert
        with pytest.raises(
            ValueError, match="Test error during request processing"
        ) as exc_info:
            await request_context_middleware.dispatch(
                mock_starlette_request, mock_starlette_call_next
            )

        assert exc_info.value is test_error
        # Verify context manager properly exits even on error
        assert mock_ctx.__enter__.called
        assert mock_ctx.__exit__.called

    @pytest.mark.usefixtures(
        "clean_context",
        "mock_starlette_request",
        "mock_starlette_response",
        "mock_starlette_call_next",
    )
    async def test_middleware_thread_safety_in_concurrent_requests(
        self,
        request_context_middleware: RequestContextMiddleware,
        thread_sync: dict[str, Any],
        mocker: MockerFixture,
    ) -> None:
        """Test that correlation IDs remain isolated between concurrent requests."""
        # Arrange
        num_requests = 5
        results = thread_sync["create_results"]()

        async def process_request(request_id: int) -> None:
            """Process a single request with unique correlation ID."""
            # Create unique request with its own correlation ID
            request = mocker.Mock(spec=Request)
            request.headers = {CORRELATION_ID_HEADER: f"correlation-{request_id}"}

            # Create unique response
            response = mocker.Mock(spec=Response)
            response.headers = {}

            # Create unique call_next that returns the response
            call_next = mocker.AsyncMock(spec=RequestResponseEndpoint)
            call_next.return_value = response

            # Wait for all tasks to be ready
            await asyncio.sleep(0.01 * request_id)  # Stagger slightly

            # Process request
            result = await request_context_middleware.dispatch(request, call_next)

            # Store result
            results.append(
                {
                    "request_id": request_id,
                    "correlation_id": result.headers[CORRELATION_ID_HEADER],
                    "expected_id": f"correlation-{request_id}",
                }
            )

        # Act
        tasks = [process_request(i) for i in range(num_requests)]
        await asyncio.gather(*tasks)

        # Assert
        assert len(results) == num_requests
        for result in results:
            assert result["correlation_id"] == result["expected_id"], (
                f"Request {result['request_id']} got wrong correlation ID"
            )

    @pytest.mark.usefixtures("clean_context")
    async def test_middleware_header_name_constant_usage(
        self,
        mock_starlette_request: MockType,
        mock_starlette_response: MockType,
        mock_starlette_call_next: MockType,
        request_context_middleware: RequestContextMiddleware,
    ) -> None:
        """Test that middleware uses CORRELATION_ID_HEADER constant consistently."""
        # Arrange
        correlation_id = "constant-test-id"
        mock_starlette_request.headers = {CORRELATION_ID_HEADER: correlation_id}

        # Act
        await request_context_middleware.dispatch(
            mock_starlette_request, mock_starlette_call_next
        )

        # Assert
        # Verify the constant value is used in response
        assert CORRELATION_ID_HEADER == "X-Correlation-ID"
        assert mock_starlette_response.headers[CORRELATION_ID_HEADER] == correlation_id

    @pytest.mark.usefixtures("clean_context", "mock_asgi_scope")
    async def test_middleware_integration_with_fastapi_app(
        self,
        mock_fastapi_app: MockType,
    ) -> None:
        """Test that middleware can be properly added to FastAPI application."""
        # Arrange
        middleware = RequestContextMiddleware

        # Act
        mock_fastapi_app.add_middleware(middleware)

        # Assert
        mock_fastapi_app.add_middleware.assert_called_once_with(middleware)

    @pytest.mark.parametrize(
        ("header_value", "should_generate_uuid"),
        [
            (None, True),  # No header
            ("", True),  # Empty string
            ("valid-uuid-12345678-1234-5678-1234-567812345678", False),  # Valid UUID
            ("invalid-format-not-uuid", False),  # Invalid format (non-UUID)
            ("a" * 1000, False),  # Very long string
            ("special!@#$%^&*()chars", False),  # Special characters
        ],
        ids=[
            "no_header",
            "empty_string",
            "valid_uuid",
            "invalid_format",
            "very_long_string",
            "special_characters",
        ],
    )
    @pytest.mark.usefixtures("clean_context", "mock_starlette_response")
    async def test_parametrized_header_variations(
        self,
        mock_starlette_request: MockType,
        mock_starlette_call_next: MockType,
        request_context_middleware: RequestContextMiddleware,
        mocker: MockerFixture,
        header_value: str | None,
        should_generate_uuid: bool,
    ) -> None:
        """Test various header value scenarios using parametrization."""
        # Arrange
        if header_value is not None:
            mock_starlette_request.headers = {CORRELATION_ID_HEADER: header_value}

        generated_uuid = "generated-uuid-12345678-1234-5678-1234-567812345678"
        mock_uuid = mocker.patch("src.api.middleware.request_context.uuid.uuid4")
        mock_uuid.return_value = generated_uuid

        mock_ctx = mocker.MagicMock()
        mock_ctx.__enter__ = mocker.MagicMock(return_value=None)
        mock_ctx.__exit__ = mocker.MagicMock(return_value=None)

        mocker.patch(
            "src.api.middleware.request_context.logger.contextualize",
            return_value=mock_ctx,
        )

        # Act
        result = await request_context_middleware.dispatch(
            mock_starlette_request, mock_starlette_call_next
        )

        # Assert
        if should_generate_uuid:
            mock_uuid.assert_called_once()
            expected_id = generated_uuid
        else:
            mock_uuid.assert_not_called()
            expected_id = header_value or ""

        assert result.headers[CORRELATION_ID_HEADER] == expected_id

    @pytest.mark.usefixtures("clean_context", "mock_starlette_response")
    async def test_middleware_calls_next_handler_in_chain(
        self,
        mock_starlette_request: MockType,
        mock_starlette_call_next: MockType,
        request_context_middleware: RequestContextMiddleware,
    ) -> None:
        """Test that middleware properly calls call_next with the request."""
        # Act
        await request_context_middleware.dispatch(
            mock_starlette_request, mock_starlette_call_next
        )

        # Assert
        mock_starlette_call_next.assert_called_once_with(mock_starlette_request)

    @pytest.mark.usefixtures("clean_context")
    async def test_response_without_headers_attribute(
        self,
        mock_starlette_request: MockType,
        mock_starlette_call_next: MockType,
        request_context_middleware: RequestContextMiddleware,
        mocker: MockerFixture,
    ) -> None:
        """Test middleware handles responses that might not have mutable headers."""
        # Arrange
        # Create a response without headers attribute
        response_without_headers = mocker.Mock(spec=Response)
        # Delete headers attribute if it exists
        if hasattr(response_without_headers, "headers"):
            delattr(response_without_headers, "headers")

        mock_starlette_call_next.return_value = response_without_headers

        mock_ctx = mocker.MagicMock()
        mock_ctx.__enter__ = mocker.MagicMock(return_value=None)
        mock_ctx.__exit__ = mocker.MagicMock(return_value=None)

        mocker.patch(
            "src.api.middleware.request_context.logger.contextualize",
            return_value=mock_ctx,
        )

        # Act & Assert
        with pytest.raises(AttributeError):
            await request_context_middleware.dispatch(
                mock_starlette_request, mock_starlette_call_next
            )
