"""Unit tests for SecurityHeadersMiddleware.

This module contains comprehensive unit tests for the SecurityHeadersMiddleware class,
which adds security-related HTTP headers to all responses to protect against
common web vulnerabilities.
"""

import asyncio

import pytest
from pytest_mock import MockerFixture, MockType
from starlette.middleware.base import RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from src.api.middleware.security_headers import (
    DEFAULT_HSTS_MAX_AGE,
    SecurityHeadersMiddleware,
)


@pytest.mark.unit
class TestSecurityHeadersMiddleware:
    """Test suite for SecurityHeadersMiddleware."""

    async def test_init_default_parameters(
        self,
        mock_app: MockType,
    ) -> None:
        """Test middleware initializes correctly with default HSTS settings."""
        # Arrange & Act
        middleware = SecurityHeadersMiddleware(mock_app)

        # Assert
        assert middleware.hsts_enabled is True
        assert middleware.hsts_max_age == DEFAULT_HSTS_MAX_AGE
        assert middleware.hsts_include_subdomains is True
        assert middleware.hsts_preload is False

    @pytest.mark.parametrize(
        (
            "hsts_enabled",
            "hsts_max_age",
            "hsts_include_subdomains",
            "hsts_preload",
        ),
        [
            (False, 86400, False, False),
            (True, 86400, False, False),
            (True, 3600, True, False),
            (True, 31536000, True, True),
            (False, 0, False, False),
        ],
    )
    async def test_init_custom_parameters(
        self,
        mock_app: MockType,
        hsts_enabled: bool,
        hsts_max_age: int,
        hsts_include_subdomains: bool,
        hsts_preload: bool,
    ) -> None:
        """Test middleware correctly stores custom HSTS configuration."""
        # Arrange & Act
        middleware = SecurityHeadersMiddleware(
            mock_app,
            hsts_enabled=hsts_enabled,
            hsts_max_age=hsts_max_age,
            hsts_include_subdomains=hsts_include_subdomains,
            hsts_preload=hsts_preload,
        )

        # Assert
        assert middleware.hsts_enabled == hsts_enabled
        assert middleware.hsts_max_age == hsts_max_age
        assert middleware.hsts_include_subdomains == hsts_include_subdomains
        assert middleware.hsts_preload == hsts_preload

    async def test_adds_basic_security_headers(
        self,
        mock_app: MockType,
        mock_starlette_request: MockType,
        mock_starlette_response: MockType,
        mock_starlette_call_next: MockType,
    ) -> None:
        """Test middleware adds the three basic security headers to all responses."""
        # Arrange
        middleware = SecurityHeadersMiddleware(mock_app)

        # Act
        result = await middleware.dispatch(
            mock_starlette_request, mock_starlette_call_next
        )

        # Assert
        assert result is mock_starlette_response
        assert mock_starlette_response.headers["X-Content-Type-Options"] == "nosniff"
        assert mock_starlette_response.headers["X-Frame-Options"] == "DENY"
        assert mock_starlette_response.headers["X-XSS-Protection"] == "1; mode=block"

    async def test_adds_hsts_header_when_enabled(
        self,
        mock_app: MockType,
        mock_starlette_request: MockType,
        mock_starlette_response: MockType,
        mock_starlette_call_next: MockType,
    ) -> None:
        """Test HSTS header is added when enabled."""
        # Arrange
        middleware = SecurityHeadersMiddleware(mock_app, hsts_enabled=True)

        # Act
        result = await middleware.dispatch(
            mock_starlette_request, mock_starlette_call_next
        )

        # Assert
        assert result is mock_starlette_response
        assert "Strict-Transport-Security" in mock_starlette_response.headers
        assert (
            "max-age=31536000"
            in mock_starlette_response.headers["Strict-Transport-Security"]
        )

    async def test_no_hsts_header_when_disabled(
        self,
        mock_app: MockType,
        mock_starlette_request: MockType,
        mock_starlette_response: MockType,
        mock_starlette_call_next: MockType,
    ) -> None:
        """Test HSTS header is not added when disabled."""
        # Arrange
        middleware = SecurityHeadersMiddleware(mock_app, hsts_enabled=False)

        # Act
        result = await middleware.dispatch(
            mock_starlette_request, mock_starlette_call_next
        )

        # Assert
        assert result is mock_starlette_response
        assert "Strict-Transport-Security" not in mock_starlette_response.headers

    @pytest.mark.parametrize(
        (
            "hsts_max_age",
            "hsts_include_subdomains",
            "hsts_preload",
            "expected_header",
        ),
        [
            (86400, False, False, "max-age=86400"),
            (86400, True, False, "max-age=86400; includeSubDomains"),
            (86400, False, True, "max-age=86400; preload"),
            (86400, True, True, "max-age=86400; includeSubDomains; preload"),
            (3600, True, True, "max-age=3600; includeSubDomains; preload"),
            (31536000, True, False, "max-age=31536000; includeSubDomains"),
        ],
    )
    async def test_hsts_header_variations(
        self,
        mock_app: MockType,
        mock_starlette_request: MockType,
        mock_starlette_response: MockType,
        mock_starlette_call_next: MockType,
        hsts_max_age: int,
        hsts_include_subdomains: bool,
        hsts_preload: bool,
        expected_header: str,
    ) -> None:
        """Test different HSTS header configurations."""
        # Arrange
        middleware = SecurityHeadersMiddleware(
            mock_app,
            hsts_enabled=True,
            hsts_max_age=hsts_max_age,
            hsts_include_subdomains=hsts_include_subdomains,
            hsts_preload=hsts_preload,
        )

        # Act
        result = await middleware.dispatch(
            mock_starlette_request, mock_starlette_call_next
        )

        # Assert
        assert result is mock_starlette_response
        assert (
            mock_starlette_response.headers["Strict-Transport-Security"]
            == expected_header
        )

    async def test_request_passthrough(
        self,
        mock_app: MockType,
        mock_starlette_request: MockType,
        mock_starlette_response: MockType,
        mock_starlette_call_next: MockType,
    ) -> None:
        """Test middleware correctly passes request to next handler."""
        # Arrange
        middleware = SecurityHeadersMiddleware(mock_app)

        # Act
        result = await middleware.dispatch(
            mock_starlette_request, mock_starlette_call_next
        )

        # Assert
        assert result is mock_starlette_response
        mock_starlette_call_next.assert_called_once_with(mock_starlette_request)

    async def test_preserves_existing_response_attributes(
        self,
        mock_app: MockType,
        mock_starlette_request: MockType,
        mock_starlette_response: MockType,
        mock_starlette_call_next: MockType,
    ) -> None:
        """Test middleware only adds headers without modifying other attributes."""
        # Arrange
        middleware = SecurityHeadersMiddleware(mock_app)
        # Set up existing response attributes
        mock_starlette_response.headers["Content-Type"] = "application/json"
        mock_starlette_response.headers["X-Custom-Header"] = "custom-value"
        mock_starlette_response.status_code = 200

        # Act
        result = await middleware.dispatch(
            mock_starlette_request, mock_starlette_call_next
        )

        # Assert
        assert result is mock_starlette_response
        # Original headers preserved
        assert mock_starlette_response.headers["Content-Type"] == "application/json"
        assert mock_starlette_response.headers["X-Custom-Header"] == "custom-value"
        # Status code unchanged
        assert mock_starlette_response.status_code == 200
        # Security headers added
        assert mock_starlette_response.headers["X-Content-Type-Options"] == "nosniff"
        assert mock_starlette_response.headers["X-Frame-Options"] == "DENY"
        assert mock_starlette_response.headers["X-XSS-Protection"] == "1; mode=block"

    async def test_concurrent_request_handling(
        self,
        mock_app: MockType,
        mocker: MockerFixture,
    ) -> None:
        """Test middleware handles multiple concurrent requests correctly."""
        # Arrange
        middleware = SecurityHeadersMiddleware(mock_app)

        # Create multiple request/response pairs
        requests = []
        responses = []
        call_nexts = []

        for _ in range(5):
            request = mocker.Mock(spec=Request)
            response = mocker.Mock(spec=Response)
            response.headers = {}
            call_next = mocker.AsyncMock(spec=RequestResponseEndpoint)
            call_next.return_value = response

            requests.append(request)
            responses.append(response)
            call_nexts.append(call_next)

        # Act
        results = await asyncio.gather(
            *[
                middleware.dispatch(request, call_next)
                for request, call_next in zip(requests, call_nexts, strict=True)
            ]
        )

        # Assert
        for i, result in enumerate(results):
            assert result is responses[i]
            assert responses[i].headers["X-Content-Type-Options"] == "nosniff"
            assert responses[i].headers["X-Frame-Options"] == "DENY"
            assert responses[i].headers["X-XSS-Protection"] == "1; mode=block"

    async def test_asgi_app_integration(
        self,
        mock_app: MockType,
    ) -> None:
        """Test middleware correctly integrates with ASGI app."""
        # Arrange & Act
        middleware = SecurityHeadersMiddleware(mock_app)

        # Assert
        assert middleware.app is mock_app

    @pytest.mark.parametrize(
        ("exception_type", "exception_message"),
        [
            (ValueError, "Test value error"),
            (KeyError, "Test key error"),
            (RuntimeError, "Test runtime error"),
            (Exception, "Generic exception"),
        ],
    )
    async def test_exception_handling_in_call_next(
        self,
        mock_app: MockType,
        mock_starlette_request: MockType,
        mock_starlette_call_next: MockType,
        exception_type: type[Exception],
        exception_message: str,
    ) -> None:
        """Test middleware properly propagates exceptions from downstream handlers."""
        # Arrange
        middleware = SecurityHeadersMiddleware(mock_app)
        mock_starlette_call_next.side_effect = exception_type(exception_message)

        # Act & Assert
        with pytest.raises(exception_type, match=exception_message):
            await middleware.dispatch(mock_starlette_request, mock_starlette_call_next)

    async def test_build_hsts_header_logic(
        self,
        mock_app: MockType,
    ) -> None:
        """Test the _build_hsts_header method directly."""
        # Test basic header (max-age only)
        middleware = SecurityHeadersMiddleware(
            mock_app,
            hsts_max_age=31536000,
            hsts_include_subdomains=False,
            hsts_preload=False,
        )
        assert middleware._build_hsts_header() == "max-age=31536000"

        # Test with subdomains
        middleware = SecurityHeadersMiddleware(
            mock_app,
            hsts_max_age=31536000,
            hsts_include_subdomains=True,
            hsts_preload=False,
        )
        assert middleware._build_hsts_header() == "max-age=31536000; includeSubDomains"

        # Test with preload
        middleware = SecurityHeadersMiddleware(
            mock_app,
            hsts_max_age=31536000,
            hsts_include_subdomains=True,
            hsts_preload=True,
        )
        assert (
            middleware._build_hsts_header()
            == "max-age=31536000; includeSubDomains; preload"
        )

        # Test custom age
        middleware = SecurityHeadersMiddleware(
            mock_app,
            hsts_max_age=86400,
            hsts_include_subdomains=True,
            hsts_preload=False,
        )
        assert middleware._build_hsts_header() == "max-age=86400; includeSubDomains"

    async def test_hsts_header_format_compliance(
        self,
        mock_app: MockType,
        mock_starlette_request: MockType,
        mock_starlette_response: MockType,
        mock_starlette_call_next: MockType,
    ) -> None:
        """Test HSTS header format meets RFC 6797 specification."""
        # Arrange
        middleware = SecurityHeadersMiddleware(
            mock_app,
            hsts_enabled=True,
            hsts_max_age=86400,
            hsts_include_subdomains=True,
            hsts_preload=True,
        )

        # Act
        result = await middleware.dispatch(
            mock_starlette_request, mock_starlette_call_next
        )

        # Assert
        assert result is mock_starlette_response
        hsts_header = mock_starlette_response.headers["Strict-Transport-Security"]

        # Test correct directive order
        assert hsts_header.startswith("max-age=")

        # Test proper semicolon separation
        parts = hsts_header.split("; ")
        assert len(parts) == 3
        assert parts[0] == "max-age=86400"
        assert parts[1] == "includeSubDomains"
        assert parts[2] == "preload"

        # Test no trailing semicolons
        assert not hsts_header.endswith(";")

    async def test_security_header_values(
        self,
        mock_app: MockType,
        mock_starlette_request: MockType,
        mock_starlette_response: MockType,
        mock_starlette_call_next: MockType,
    ) -> None:
        """Test security header values meet security standards."""
        # Arrange
        middleware = SecurityHeadersMiddleware(mock_app)

        # Act
        result = await middleware.dispatch(
            mock_starlette_request, mock_starlette_call_next
        )

        # Assert
        assert result is mock_starlette_response

        # Test exact header values
        assert mock_starlette_response.headers["X-Content-Type-Options"] == "nosniff"
        assert mock_starlette_response.headers["X-Frame-Options"] == "DENY"
        assert mock_starlette_response.headers["X-XSS-Protection"] == "1; mode=block"

    async def test_header_overwriting(
        self,
        mock_app: MockType,
        mock_starlette_request: MockType,
        mock_starlette_response: MockType,
        mock_starlette_call_next: MockType,
    ) -> None:
        """Test security headers overwrite conflicting headers."""
        # Arrange
        middleware = SecurityHeadersMiddleware(mock_app)
        # Set conflicting headers
        mock_starlette_response.headers["X-Content-Type-Options"] = "wrong-value"
        mock_starlette_response.headers["X-Frame-Options"] = "SAMEORIGIN"
        mock_starlette_response.headers["X-XSS-Protection"] = "0"

        # Act
        result = await middleware.dispatch(
            mock_starlette_request, mock_starlette_call_next
        )

        # Assert
        assert result is mock_starlette_response
        # Security headers should have correct values (overwritten)
        assert mock_starlette_response.headers["X-Content-Type-Options"] == "nosniff"
        assert mock_starlette_response.headers["X-Frame-Options"] == "DENY"
        assert mock_starlette_response.headers["X-XSS-Protection"] == "1; mode=block"

    @pytest.mark.parametrize("status_code", [200, 201, 400, 401, 403, 404, 500])
    async def test_status_code_preservation(
        self,
        mock_app: MockType,
        mock_starlette_request: MockType,
        mock_starlette_response: MockType,
        mock_starlette_call_next: MockType,
        status_code: int,
    ) -> None:
        """Test middleware preserves response status codes."""
        # Arrange
        middleware = SecurityHeadersMiddleware(mock_app)
        mock_starlette_response.status_code = status_code

        # Act
        result = await middleware.dispatch(
            mock_starlette_request, mock_starlette_call_next
        )

        # Assert
        assert result is mock_starlette_response
        assert mock_starlette_response.status_code == status_code

    async def test_extreme_hsts_configuration(
        self,
        mock_app: MockType,
        mock_starlette_request: MockType,
        mock_starlette_response: MockType,
        mock_starlette_call_next: MockType,
    ) -> None:
        """Test boundary conditions for HSTS settings."""
        # Test maximum reasonable max-age (2 years)
        middleware = SecurityHeadersMiddleware(
            mock_app,
            hsts_enabled=True,
            hsts_max_age=63072000,  # 2 years
            hsts_include_subdomains=True,
            hsts_preload=True,
        )

        result = await middleware.dispatch(
            mock_starlette_request, mock_starlette_call_next
        )

        assert result is mock_starlette_response
        assert mock_starlette_response.headers["Strict-Transport-Security"] == (
            "max-age=63072000; includeSubDomains; preload"
        )

        # Test minimum practical max-age (1 minute)
        middleware = SecurityHeadersMiddleware(
            mock_app,
            hsts_enabled=True,
            hsts_max_age=60,  # 1 minute
            hsts_include_subdomains=False,
            hsts_preload=False,
        )

        # Reset response headers for second test
        mock_starlette_response.headers = {}

        result = await middleware.dispatch(
            mock_starlette_request, mock_starlette_call_next
        )

        assert result is mock_starlette_response
        assert (
            mock_starlette_response.headers["Strict-Transport-Security"] == "max-age=60"
        )

    @pytest.mark.parametrize(
        "method",
        ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"],
    )
    async def test_multiple_http_methods(
        self,
        mock_app: MockType,
        mock_starlette_request: MockType,
        mock_starlette_response: MockType,
        mock_starlette_call_next: MockType,
        method: str,
    ) -> None:
        """Test middleware works with all HTTP methods."""
        # Arrange
        middleware = SecurityHeadersMiddleware(mock_app)
        mock_starlette_request.method = method

        # Act
        result = await middleware.dispatch(
            mock_starlette_request, mock_starlette_call_next
        )

        # Assert
        assert result is mock_starlette_response
        assert mock_starlette_response.headers["X-Content-Type-Options"] == "nosniff"
        assert mock_starlette_response.headers["X-Frame-Options"] == "DENY"
        assert mock_starlette_response.headers["X-XSS-Protection"] == "1; mode=block"
