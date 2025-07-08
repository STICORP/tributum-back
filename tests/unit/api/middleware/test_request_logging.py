"""Unit tests for RequestLoggingMiddleware."""

import asyncio
from collections.abc import Callable
from typing import cast

import pytest
from pytest_mock import MockerFixture, MockType

from src.api.middleware.request_logging import RequestLoggingMiddleware
from src.core.config import Settings


@pytest.mark.unit
class TestRequestLoggingMiddleware:
    """Test suite for RequestLoggingMiddleware."""

    def test_init_middleware(
        self,
        request_logging_middleware: RequestLoggingMiddleware,
        mock_asgi_app: MockType,
        mock_log_config: MockType,
        mock_settings: Settings,
        mock_get_settings: MockType,
    ) -> None:
        """Test middleware initialization with all required attributes."""
        # Assert middleware stores the app correctly
        assert request_logging_middleware.app == mock_asgi_app

        # Assert log_config is stored
        assert request_logging_middleware.log_config == mock_log_config

        # Assert excluded_paths set is created from log_config
        assert request_logging_middleware.excluded_paths == set(
            mock_log_config.excluded_paths
        )

        # Assert settings are retrieved and stored
        mock_get_settings.assert_called_once()
        assert request_logging_middleware.settings == mock_settings

    async def test_excluded_paths_skip_logging(
        self,
        mocker: MockerFixture,
        request_logging_middleware: RequestLoggingMiddleware,
        mock_request_factory: Callable[..., MockType],
        mock_call_next: MockType,
    ) -> None:
        """Test that excluded paths bypass all logging logic."""
        # Create mock request with excluded path
        request = mock_request_factory(path="/health")

        # Mock logger to track calls
        mock_logger = mocker.patch("src.api.middleware.request_logging.logger")

        # Call dispatch with excluded path request
        response = await request_logging_middleware.dispatch(request, mock_call_next)

        # Assert call_next was called exactly once
        mock_call_next.assert_called_once_with(request)

        # Assert no logger methods were called
        mock_logger.contextualize.assert_not_called()
        mock_logger.info.assert_not_called()
        mock_logger.error.assert_not_called()
        mock_logger.warning.assert_not_called()

        # Assert response is returned unmodified
        assert response == mock_call_next.return_value

    @pytest.mark.parametrize(
        ("headers", "expected_ip"),
        [
            ({"x-forwarded-for": "192.168.1.1"}, "192.168.1.1"),
            ({"x-forwarded-for": "192.168.1.1, 10.0.0.1"}, "192.168.1.1"),
            ({"x-real-ip": "192.168.1.2"}, "192.168.1.2"),
            (
                {"x-forwarded-for": "192.168.1.1", "x-real-ip": "192.168.1.2"},
                "192.168.1.1",
            ),
            ({}, "127.0.0.1"),
        ],
    )
    def test_get_client_ip_production_proxy_headers(
        self,
        mocker: MockerFixture,
        mock_asgi_app: MockType,
        mock_log_config: MockType,
        mock_request_factory: Callable[..., MockType],
        headers: dict[str, str],
        expected_ip: str,
    ) -> None:
        """Test IP extraction from proxy headers in production."""
        # Set environment to production
        mock_settings = mocker.Mock()
        mock_settings.environment = "production"

        mocker.patch(
            "src.api.middleware.request_logging.get_settings",
            return_value=mock_settings,
        )

        middleware = RequestLoggingMiddleware(mock_asgi_app, log_config=mock_log_config)

        # Create request with various header combinations
        request = mock_request_factory(headers=headers)

        # Test IP extraction
        actual_ip = middleware._get_client_ip(request)
        assert actual_ip == expected_ip

    def test_get_client_ip_production_no_client(
        self,
        mocker: MockerFixture,
        mock_log_config: MockType,
        mock_request_factory: Callable[..., MockType],
    ) -> None:
        """Test IP extraction when client is None in production."""
        # Set environment to production
        mock_settings = mocker.Mock()
        mock_settings.environment = "production"

        mock_app = mocker.Mock()
        mocker.patch(
            "src.api.middleware.request_logging.get_settings",
            return_value=mock_settings,
        )

        middleware = RequestLoggingMiddleware(mock_app, log_config=mock_log_config)

        # Create request with no client
        request = mock_request_factory()
        request.client = None

        # Test IP extraction
        actual_ip = middleware._get_client_ip(request)
        assert actual_ip == "unknown"

    @pytest.mark.parametrize("environment", ["development", "staging", "testing"])
    def test_get_client_ip_non_production_ignores_proxy(
        self,
        mocker: MockerFixture,
        mock_log_config: MockType,
        mock_request_factory: Callable[..., MockType],
        environment: str,
    ) -> None:
        """Test that proxy headers are ignored in non-production environments."""
        # Set environment to non-production
        mock_settings = mocker.Mock()
        mock_settings.environment = environment

        mock_app = mocker.Mock()
        mocker.patch(
            "src.api.middleware.request_logging.get_settings",
            return_value=mock_settings,
        )

        middleware = RequestLoggingMiddleware(mock_app, log_config=mock_log_config)

        # Create request with proxy headers but also client.host
        request = mock_request_factory(
            headers={"x-forwarded-for": "192.168.1.1", "x-real-ip": "192.168.1.2"},
            client_host="127.0.0.1",
        )

        # Test IP extraction - should ignore proxy headers
        actual_ip = middleware._get_client_ip(request)
        assert actual_ip == "127.0.0.1"

    @pytest.mark.parametrize(
        ("user_agent", "expected"),
        [
            (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            ),
            ("", "unknown"),
            ("x" * 300, "x" * 200),  # Long user agent gets truncated
            ("Normal user agent", "Normal user agent"),
        ],
    )
    def test_get_user_agent_extraction(
        self,
        mocker: MockerFixture,
        mock_log_config: MockType,
        mock_request_factory: Callable[..., MockType],
        user_agent: str,
        expected: str,
    ) -> None:
        """Test user agent extraction and truncation."""
        mock_settings = mocker.Mock()
        mock_app = mocker.Mock()
        mocker.patch(
            "src.api.middleware.request_logging.get_settings",
            return_value=mock_settings,
        )

        middleware = RequestLoggingMiddleware(mock_app, log_config=mock_log_config)

        # Create request with user agent
        headers = {"user-agent": user_agent} if user_agent else {}
        request = mock_request_factory(headers=headers)

        # Test user agent extraction
        actual_ua = middleware._get_user_agent(request)
        assert actual_ua == expected

    def test_get_user_agent_missing_header(
        self,
        mocker: MockerFixture,
        mock_log_config: MockType,
        mock_request_factory: Callable[..., MockType],
    ) -> None:
        """Test user agent extraction when header is missing."""
        mock_settings = mocker.Mock()
        mock_app = mocker.Mock()
        mocker.patch(
            "src.api.middleware.request_logging.get_settings",
            return_value=mock_settings,
        )

        middleware = RequestLoggingMiddleware(mock_app, log_config=mock_log_config)

        # Create request without user-agent header
        request = mock_request_factory(headers={})

        # Test user agent extraction
        actual_ua = middleware._get_user_agent(request)
        assert actual_ua == "unknown"

    async def test_dispatch_successful_request_logging(
        self,
        mocker: MockerFixture,
        request_logging_middleware: RequestLoggingMiddleware,
        mock_request_factory: Callable[..., MockType],
        mock_response_factory: Callable[..., MockType],
        mock_call_next: MockType,
        mock_time: MockType,
    ) -> None:
        """Test complete logging flow for successful requests."""
        # Ensure mock_time is used for controlled timing
        _ = mock_time

        # Mock request and response
        request = mock_request_factory(
            method="POST",
            path="/api/users",
            headers={"content-length": "100", "user-agent": "test-client"},
            query_params={"page": "1", "limit": "10"},
        )

        response = mock_response_factory(
            status_code=201,
            headers={"content-length": "50"},
        )
        mock_call_next.return_value = response

        # Mock UUID generation for predictable request ID
        mock_uuid = mocker.patch("src.api.middleware.request_logging.uuid.uuid4")
        mock_uuid.return_value = "test-request-id"

        # Mock logger with context manager
        mock_logger = mocker.patch("src.api.middleware.request_logging.logger")
        mock_context = mocker.MagicMock()
        mock_logger.contextualize.return_value = mock_context

        # Call dispatch
        result = await request_logging_middleware.dispatch(request, mock_call_next)

        # Assert logger.contextualize called with correct fields
        mock_logger.contextualize.assert_called_once_with(
            request_id="test-request-id",
            method="POST",
            path="/api/users",
            client_host="127.0.0.1",
            user_agent="test-client",
            request_size=100,
        )

        # Assert logger.info called for "Request started"
        mock_logger.info.assert_any_call(
            "Request started",
            query_params={"page": "1", "limit": "10"},
        )

        # Assert logger.info called for "Request completed"
        mock_logger.info.assert_any_call(
            "Request completed",
            status_code=201,
            duration_ms=1000.0,
            response_size=50,
        )

        # Assert response has X-Request-ID header
        assert response.headers["X-Request-ID"] == "test-request-id"

        # Assert response is returned
        assert result == response

    @pytest.mark.parametrize(
        ("has_header", "request_id"),
        [
            (True, "existing-request-id"),
            (False, "generated-uuid"),
        ],
    )
    async def test_request_id_generation_and_extraction(
        self,
        mocker: MockerFixture,
        mock_log_config: MockType,
        mock_settings: Settings,
        mock_request_factory: Callable[..., MockType],
        mock_call_next: MockType,
        has_header: bool,
        request_id: str,
    ) -> None:
        """Test request ID is extracted from header or generated."""
        mock_app = mocker.Mock()
        mocker.patch(
            "src.api.middleware.request_logging.get_settings",
            return_value=mock_settings,
        )

        middleware = RequestLoggingMiddleware(mock_app, log_config=mock_log_config)

        # Mock UUID generation
        mock_uuid = mocker.patch("src.api.middleware.request_logging.uuid.uuid4")
        mock_uuid.return_value = "generated-uuid"

        # Create request with or without X-Request-ID header
        headers = {"X-Request-ID": request_id} if has_header else {}
        request = mock_request_factory(headers=headers)

        # Mock logger
        mock_logger = mocker.patch("src.api.middleware.request_logging.logger")
        mock_context = mocker.MagicMock()
        mock_logger.contextualize.return_value = mock_context

        # Mock response
        response = mock_call_next.return_value

        # Call dispatch
        await middleware.dispatch(request, mock_call_next)

        # Assert correct request ID is used in logging
        mock_logger.contextualize.assert_called_once()
        context_args = mock_logger.contextualize.call_args[1]
        assert context_args["request_id"] == request_id

        # Assert response has correct X-Request-ID header
        assert response.headers["X-Request-ID"] == request_id

    @pytest.mark.parametrize(
        ("exception_type", "exception_message"),
        [
            (ValueError, "Test error"),
            (RuntimeError, "Connection failed"),
            (Exception, "Custom exception"),
        ],
    )
    async def test_dispatch_error_handling(
        self,
        mocker: MockerFixture,
        mock_log_config: MockType,
        mock_settings: Settings,
        mock_request_factory: Callable[..., MockType],
        mock_call_next: MockType,
        mock_time: MockType,
        exception_type: type[Exception],
        exception_message: str,
    ) -> None:
        """Test exceptions are logged and re-raised."""
        # Ensure mock_time is used for controlled timing
        _ = mock_time

        mock_app = mocker.Mock()
        mocker.patch(
            "src.api.middleware.request_logging.get_settings",
            return_value=mock_settings,
        )

        middleware = RequestLoggingMiddleware(mock_app, log_config=mock_log_config)

        # Mock call_next to raise exception
        test_exception = exception_type(exception_message)
        mock_call_next.side_effect = test_exception

        # Create request
        request = mock_request_factory()

        # Mock logger
        mock_logger = mocker.patch("src.api.middleware.request_logging.logger")
        mock_context = mocker.MagicMock()
        mock_logger.contextualize.return_value = mock_context

        # Call dispatch and expect exception
        with pytest.raises(exception_type) as exc_info:
            await middleware.dispatch(request, mock_call_next)

        # Assert exception is re-raised unchanged
        assert exc_info.value == test_exception

        # Assert logger.error called with correct error details
        mock_logger.error.assert_called_once_with(
            "Request failed",
            duration_ms=1000.0,
            error_type=exception_type.__name__,
            error_message=exception_message,
        )

    @pytest.mark.parametrize(
        ("duration_ms", "threshold_ms", "should_warn"),
        [
            (999, 1000, False),  # Just under threshold
            (1000, 1000, True),  # At threshold
            (1500, 1000, True),  # Over threshold
        ],
    )
    async def test_slow_request_warning(
        self,
        mocker: MockerFixture,
        mock_log_config: MockType,
        mock_settings: Settings,
        mock_request_factory: Callable[..., MockType],
        mock_call_next: MockType,
        duration_ms: int,
        threshold_ms: int,
        should_warn: bool,
    ) -> None:
        """Test slow requests trigger warning logs."""
        mock_app = mocker.Mock()
        mocker.patch(
            "src.api.middleware.request_logging.get_settings",
            return_value=mock_settings,
        )

        # Set slow request threshold
        mock_log_config.slow_request_threshold_ms = threshold_ms

        middleware = RequestLoggingMiddleware(mock_app, log_config=mock_log_config)

        # Mock time to simulate specific duration
        mock_time = mocker.patch("src.api.middleware.request_logging.time.perf_counter")
        mock_time.side_effect = [0.0, duration_ms / 1000.0]

        # Create request
        request = mock_request_factory()

        # Mock logger
        mock_logger = mocker.patch("src.api.middleware.request_logging.logger")
        mock_context = mocker.MagicMock()
        mock_logger.contextualize.return_value = mock_context

        # Call dispatch
        await middleware.dispatch(request, mock_call_next)

        # Check if warning was logged
        if should_warn:
            mock_logger.warning.assert_called_once_with(
                "Slow request detected",
                duration_ms=float(duration_ms),
                threshold_ms=threshold_ms,
            )
        else:
            mock_logger.warning.assert_not_called()

    @pytest.mark.parametrize(
        ("headers", "expected_size"),
        [
            ({"content-length": "100"}, 100),
            ({}, 0),
            ({"content-length": "invalid"}, 0),
        ],
    )
    async def test_response_size_tracking(
        self,
        mocker: MockerFixture,
        mock_log_config: MockType,
        mock_settings: Settings,
        mock_request_factory: Callable[..., MockType],
        mock_response_factory: Callable[..., MockType],
        mock_call_next: MockType,
        headers: dict[str, str],
        expected_size: int,
    ) -> None:
        """Test response size is correctly extracted and logged."""
        mock_app = mocker.Mock()
        mocker.patch(
            "src.api.middleware.request_logging.get_settings",
            return_value=mock_settings,
        )

        middleware = RequestLoggingMiddleware(mock_app, log_config=mock_log_config)

        # Mock time to control duration
        mock_time = mocker.patch("src.api.middleware.request_logging.time.perf_counter")
        mock_time.side_effect = [0.0, 1.0]  # 1 second duration

        # Create request and response
        request = mock_request_factory()
        response = mock_response_factory(headers=headers)
        mock_call_next.return_value = response

        # Mock logger
        mock_logger = mocker.patch("src.api.middleware.request_logging.logger")
        mock_context = mocker.MagicMock()
        mock_logger.contextualize.return_value = mock_context

        # Call dispatch
        await middleware.dispatch(request, mock_call_next)

        # Assert response size is logged correctly
        mock_logger.info.assert_any_call(
            "Request completed",
            status_code=200,
            duration_ms=1000.0,
            response_size=expected_size,
        )

    @pytest.mark.parametrize(
        ("query_params", "expected_log"),
        [
            ({"page": "1", "limit": "10"}, {"page": "1", "limit": "10"}),
            ({}, None),
            (
                {"search": "test query", "filter": "active"},
                {"search": "test query", "filter": "active"},
            ),
        ],
    )
    async def test_query_parameter_logging(
        self,
        mocker: MockerFixture,
        mock_log_config: MockType,
        mock_settings: Settings,
        mock_request_factory: Callable[..., MockType],
        mock_call_next: MockType,
        query_params: dict[str, str],
        expected_log: dict[str, str] | None,
    ) -> None:
        """Test query parameters are logged correctly."""
        mock_app = mocker.Mock()
        mocker.patch(
            "src.api.middleware.request_logging.get_settings",
            return_value=mock_settings,
        )

        middleware = RequestLoggingMiddleware(mock_app, log_config=mock_log_config)

        # Create request with query parameters
        request = mock_request_factory(query_params=query_params)

        # Mock logger
        mock_logger = mocker.patch("src.api.middleware.request_logging.logger")
        mock_context = mocker.MagicMock()
        mock_logger.contextualize.return_value = mock_context

        # Call dispatch
        await middleware.dispatch(request, mock_call_next)

        # Assert query params are included in "Request started" log
        mock_logger.info.assert_any_call(
            "Request started",
            query_params=expected_log,
        )

    @pytest.mark.parametrize(
        ("headers", "expected_size"),
        [
            ({"content-length": "500"}, 500),
            ({}, 0),
            ({"content-length": "invalid"}, 0),
        ],
    )
    async def test_request_size_extraction(
        self,
        mocker: MockerFixture,
        mock_log_config: MockType,
        mock_settings: Settings,
        mock_request_factory: Callable[..., MockType],
        mock_call_next: MockType,
        headers: dict[str, str],
        expected_size: int,
    ) -> None:
        """Test request content-length is tracked."""
        mock_app = mocker.Mock()
        mocker.patch(
            "src.api.middleware.request_logging.get_settings",
            return_value=mock_settings,
        )

        middleware = RequestLoggingMiddleware(mock_app, log_config=mock_log_config)

        # Mock time to control duration
        mock_time = mocker.patch("src.api.middleware.request_logging.time.perf_counter")
        mock_time.side_effect = [0.0, 1.0]  # 1 second duration

        # Create request with content-length header
        request = mock_request_factory(headers=headers)

        # Mock logger
        mock_logger = mocker.patch("src.api.middleware.request_logging.logger")
        mock_context = mocker.MagicMock()
        mock_logger.contextualize.return_value = mock_context

        # Call dispatch
        await middleware.dispatch(request, mock_call_next)

        # Assert request size is logged in context
        mock_logger.contextualize.assert_called_once()
        context_args = mock_logger.contextualize.call_args[1]
        assert context_args["request_size"] == expected_size

    async def test_concurrent_request_isolation(
        self,
        mocker: MockerFixture,
        mock_log_config: MockType,
        mock_settings: Settings,
        mock_request_factory: Callable[..., MockType],
        mock_call_next: MockType,
    ) -> None:
        """Test multiple concurrent requests don't interfere."""
        mock_app = mocker.Mock()
        mocker.patch(
            "src.api.middleware.request_logging.get_settings",
            return_value=mock_settings,
        )

        middleware = RequestLoggingMiddleware(mock_app, log_config=mock_log_config)

        # Create multiple request/response pairs
        requests = [
            mock_request_factory(path="/api/users/1", method="GET"),
            mock_request_factory(path="/api/users/2", method="POST"),
            mock_request_factory(path="/api/users/3", method="PUT"),
        ]

        # Mock UUID generation to return predictable request IDs
        mock_uuid = mocker.patch("src.api.middleware.request_logging.uuid.uuid4")
        mock_uuid.side_effect = ["req-1", "req-2", "req-3"]

        # Mock logger
        mock_logger = mocker.patch("src.api.middleware.request_logging.logger")
        mock_context = mocker.MagicMock()
        mock_logger.contextualize.return_value = mock_context

        # Mock call_next to return different responses
        async def mock_call_next_side_effect(_request: MockType) -> MockType:
            response = mocker.Mock()
            response.status_code = 200
            response.headers = {}
            return cast("MockType", response)

        mock_call_next.side_effect = mock_call_next_side_effect

        # Run multiple dispatch calls concurrently
        tasks = [middleware.dispatch(req, mock_call_next) for req in requests]
        results = await asyncio.gather(*tasks)

        # Assert each request maintains its own context
        assert len(results) == 3
        assert mock_logger.contextualize.call_count == 3

        # Check that each request got its own unique ID
        context_calls = mock_logger.contextualize.call_args_list
        request_ids = [call[1]["request_id"] for call in context_calls]
        assert request_ids == ["req-1", "req-2", "req-3"]

    async def test_middleware_chain_call_next(
        self,
        mocker: MockerFixture,
        mock_log_config: MockType,
        mock_settings: Settings,
        mock_request_factory: Callable[..., MockType],
        mock_call_next: MockType,
    ) -> None:
        """Test middleware correctly calls and awaits next handler."""
        mock_app = mocker.Mock()
        mocker.patch(
            "src.api.middleware.request_logging.get_settings",
            return_value=mock_settings,
        )

        middleware = RequestLoggingMiddleware(mock_app, log_config=mock_log_config)

        # Create request
        request = mock_request_factory()

        # Mock logger
        mock_logger = mocker.patch("src.api.middleware.request_logging.logger")
        mock_context = mocker.MagicMock()
        mock_logger.contextualize.return_value = mock_context

        # Call dispatch
        result = await middleware.dispatch(request, mock_call_next)

        # Assert call_next called exactly once with request
        mock_call_next.assert_called_once_with(request)

        # Assert response is returned unchanged
        assert result == mock_call_next.return_value

    async def test_logger_contextualize_cleanup(
        self,
        mocker: MockerFixture,
        mock_log_config: MockType,
        mock_settings: Settings,
        mock_request_factory: Callable[..., MockType],
        mock_call_next: MockType,
    ) -> None:
        """Test logger context is properly managed."""
        mock_app = mocker.Mock()
        mocker.patch(
            "src.api.middleware.request_logging.get_settings",
            return_value=mock_settings,
        )

        middleware = RequestLoggingMiddleware(mock_app, log_config=mock_log_config)

        # Create request
        request = mock_request_factory()

        # Mock logger with context manager tracking
        mock_logger = mocker.patch("src.api.middleware.request_logging.logger")
        mock_context = mocker.MagicMock()
        mock_logger.contextualize.return_value = mock_context

        # Call dispatch
        await middleware.dispatch(request, mock_call_next)

        # Assert context manager was entered
        mock_logger.contextualize.assert_called_once()
        assert mock_context.__enter__.called
        assert mock_context.__exit__.called

        # Assert context contains all expected fields
        context_args = mock_logger.contextualize.call_args[1]
        expected_fields = {
            "request_id",
            "method",
            "path",
            "client_host",
            "user_agent",
            "request_size",
        }
        assert set(context_args.keys()) == expected_fields
