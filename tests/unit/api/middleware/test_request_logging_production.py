"""Tests for request logging middleware in production environment."""

import pytest
from pytest_mock import MockerFixture
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Route
from starlette.testclient import TestClient

from src.api.middleware.request_logging import RequestLoggingMiddleware
from src.core.config import LogConfig, Settings


@pytest.mark.unit
class TestRequestLoggingProductionEnvironment:
    """Test request logging middleware behavior in production environment."""

    def test_get_client_ip_with_x_forwarded_for(self, mocker: MockerFixture) -> None:
        """Test client IP extraction from X-Forwarded-For header in production."""
        # Create a production settings mock
        settings = mocker.MagicMock(spec=Settings)
        settings.environment = "production"

        log_config = LogConfig()
        # Use a mock app since we're only testing helper methods
        mock_app = mocker.MagicMock()
        middleware = RequestLoggingMiddleware(mock_app, log_config=log_config)
        middleware.settings = settings

        # Create a mock request with X-Forwarded-For header
        request = mocker.MagicMock(spec=Request)
        request.headers = {"x-forwarded-for": "203.0.113.1, 198.51.100.2, 172.16.0.1"}
        request.client = None

        # Should return the first IP (original client)
        assert middleware._get_client_ip(request) == "203.0.113.1"

    def test_get_client_ip_with_x_real_ip(self, mocker: MockerFixture) -> None:
        """Test client IP extraction from X-Real-IP header in production."""
        # Create a production settings mock
        settings = mocker.MagicMock(spec=Settings)
        settings.environment = "production"

        log_config = LogConfig()
        # Use a mock app since we're only testing helper methods
        mock_app = mocker.MagicMock()
        middleware = RequestLoggingMiddleware(mock_app, log_config=log_config)
        middleware.settings = settings

        # Create a mock request with X-Real-IP header
        request = mocker.MagicMock(spec=Request)
        request.headers = {"x-real-ip": "203.0.113.5"}
        request.client = None

        # Should return the real IP
        assert middleware._get_client_ip(request) == "203.0.113.5"

    def test_get_client_ip_without_proxy_headers(self, mocker: MockerFixture) -> None:
        """Test client IP extraction without proxy headers in production."""
        # Create a production settings mock
        settings = mocker.MagicMock(spec=Settings)
        settings.environment = "production"

        log_config = LogConfig()
        # Use a mock app since we're only testing helper methods
        mock_app = mocker.MagicMock()
        middleware = RequestLoggingMiddleware(mock_app, log_config=log_config)
        middleware.settings = settings

        # Create a mock request without proxy headers
        request = mocker.MagicMock(spec=Request)
        request.headers = {}
        request.client = mocker.MagicMock()
        request.client.host = "192.168.1.100"

        # Should fall back to direct client
        assert middleware._get_client_ip(request) == "192.168.1.100"

    def test_get_client_ip_no_client_in_production(self, mocker: MockerFixture) -> None:
        """Test client IP extraction when no client info is available."""
        # Create a production settings mock
        settings = mocker.MagicMock(spec=Settings)
        settings.environment = "production"

        log_config = LogConfig()
        # Use a mock app since we're only testing helper methods
        mock_app = mocker.MagicMock()
        middleware = RequestLoggingMiddleware(mock_app, log_config=log_config)
        middleware.settings = settings

        # Create a mock request without client info
        request = mocker.MagicMock(spec=Request)
        request.headers = {}
        request.client = None

        # Should return "unknown"
        assert middleware._get_client_ip(request) == "unknown"

    def test_production_request_logging_with_proxy_headers(
        self, mocker: MockerFixture
    ) -> None:
        """Test full request logging flow with proxy headers in production."""
        # Mock the settings to be in production mode
        mock_settings = mocker.MagicMock()
        mock_settings.environment = "production"

        # Patch get_settings to return our mock
        mocker.patch(
            "src.api.middleware.request_logging.get_settings",
            return_value=mock_settings,
        )

        # Create endpoint handler
        async def test_endpoint(request: Request) -> Response:
            # Use request to avoid unused argument warning
            _ = request
            return Response("OK", status_code=200)

        # Create app with routes
        routes = [
            Route("/test", endpoint=test_endpoint),
        ]

        app = Starlette(routes=routes)
        log_config = LogConfig(excluded_paths=[])

        # Add middleware with production settings
        app.add_middleware(RequestLoggingMiddleware, log_config=log_config)

        # Create test client
        client = TestClient(app)

        # Make request with proxy headers
        response = client.get(
            "/test",
            headers={
                "X-Forwarded-For": "203.0.113.10, 10.0.0.1",
                "X-Real-IP": "203.0.113.10",
                "User-Agent": "TestClient/1.0",
            },
        )

        assert response.status_code == 200
        assert response.text == "OK"
