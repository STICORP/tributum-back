"""Unit tests for SecurityHeadersMiddleware."""

import pytest
from fastapi import FastAPI, Response
from fastapi.testclient import TestClient

from src.api.middleware.security_headers import SecurityHeadersMiddleware


@pytest.fixture
def app() -> FastAPI:
    """Create a test FastAPI app with SecurityHeadersMiddleware."""
    test_app = FastAPI()
    test_app.add_middleware(SecurityHeadersMiddleware)

    @test_app.get("/test")
    async def test_endpoint() -> dict[str, str]:
        """Test endpoint that returns a simple response."""
        return {"message": "test"}

    return test_app


@pytest.fixture
def app_without_hsts() -> FastAPI:
    """Create a test FastAPI app with SecurityHeadersMiddleware without HSTS."""
    test_app = FastAPI()
    test_app.add_middleware(SecurityHeadersMiddleware, hsts_enabled=False)

    @test_app.get("/test")
    async def test_endpoint() -> dict[str, str]:
        """Test endpoint that returns a simple response."""
        return {"message": "test"}

    return test_app


@pytest.fixture
def app_with_custom_hsts() -> FastAPI:
    """Create a test FastAPI app with custom HSTS configuration."""
    test_app = FastAPI()
    test_app.add_middleware(
        SecurityHeadersMiddleware,
        hsts_max_age=86400,  # 1 day
        hsts_include_subdomains=False,
        hsts_preload=True,
    )

    @test_app.get("/test")
    async def test_endpoint() -> dict[str, str]:
        """Test endpoint that returns a simple response."""
        return {"message": "test"}

    return test_app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Create a test client for the app with default config."""
    return TestClient(app)


@pytest.fixture
def client_without_hsts(app_without_hsts: FastAPI) -> TestClient:
    """Create a test client for the app without HSTS."""
    return TestClient(app_without_hsts)


@pytest.fixture
def client_custom_hsts(app_with_custom_hsts: FastAPI) -> TestClient:
    """Create a test client for the app with custom HSTS."""
    return TestClient(app_with_custom_hsts)


class TestSecurityHeadersMiddleware:
    """Test cases for SecurityHeadersMiddleware."""

    def test_adds_x_content_type_options_header(self, client: TestClient) -> None:
        """Test that X-Content-Type-Options header is added."""
        response = client.get("/test")

        assert response.status_code == 200
        assert "X-Content-Type-Options" in response.headers
        assert response.headers["X-Content-Type-Options"] == "nosniff"

    def test_adds_x_frame_options_header(self, client: TestClient) -> None:
        """Test that X-Frame-Options header is added."""
        response = client.get("/test")

        assert response.status_code == 200
        assert "X-Frame-Options" in response.headers
        assert response.headers["X-Frame-Options"] == "DENY"

    def test_adds_x_xss_protection_header(self, client: TestClient) -> None:
        """Test that X-XSS-Protection header is added."""
        response = client.get("/test")

        assert response.status_code == 200
        assert "X-XSS-Protection" in response.headers
        assert response.headers["X-XSS-Protection"] == "1; mode=block"

    def test_adds_default_hsts_header(self, client: TestClient) -> None:
        """Test that default Strict-Transport-Security header is added."""
        response = client.get("/test")

        assert response.status_code == 200
        assert "Strict-Transport-Security" in response.headers
        assert (
            response.headers["Strict-Transport-Security"]
            == "max-age=31536000; includeSubDomains"
        )

    def test_no_hsts_header_when_disabled(
        self, client_without_hsts: TestClient
    ) -> None:
        """Test that HSTS header is not added when disabled."""
        response = client_without_hsts.get("/test")

        assert response.status_code == 200
        assert "Strict-Transport-Security" not in response.headers
        # But other security headers should still be present
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["X-Frame-Options"] == "DENY"
        assert response.headers["X-XSS-Protection"] == "1; mode=block"

    def test_custom_hsts_configuration(self, client_custom_hsts: TestClient) -> None:
        """Test custom HSTS configuration."""
        response = client_custom_hsts.get("/test")

        assert response.status_code == 200
        assert "Strict-Transport-Security" in response.headers
        assert response.headers["Strict-Transport-Security"] == "max-age=86400; preload"

    def test_all_headers_present_in_single_response(self, client: TestClient) -> None:
        """Test that all security headers are present in a single response."""
        response = client.get("/test")

        assert response.status_code == 200

        # Check all headers are present
        expected_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
        }

        for header, expected_value in expected_headers.items():
            assert header in response.headers
            assert response.headers[header] == expected_value

    def test_headers_added_to_post_request(self, client: TestClient) -> None:
        """Test that security headers are added to POST requests."""
        # Add a POST endpoint to the app
        app = client.app
        assert isinstance(app, FastAPI)

        @app.post("/test-post")
        async def test_post() -> dict[str, str]:
            """Test POST endpoint."""
            return {"message": "posted"}

        response = client.post("/test-post")

        assert response.status_code == 200
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["X-Frame-Options"] == "DENY"
        assert response.headers["X-XSS-Protection"] == "1; mode=block"
        assert "Strict-Transport-Security" in response.headers

    def test_headers_added_to_error_responses(self, client: TestClient) -> None:
        """Test that security headers are added to error responses."""
        # Make a request to a non-existent endpoint
        response = client.get("/non-existent")

        assert response.status_code == 404
        # Security headers should still be present
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["X-Frame-Options"] == "DENY"
        assert response.headers["X-XSS-Protection"] == "1; mode=block"
        assert "Strict-Transport-Security" in response.headers

    def test_middleware_preserves_existing_headers(self, client: TestClient) -> None:
        """Test that middleware preserves existing response headers."""
        app = client.app
        assert isinstance(app, FastAPI)

        @app.get("/test-custom-header")
        async def test_custom_header() -> Response:
            """Test endpoint with custom header."""
            return Response(
                content='{"message": "custom"}',
                media_type="application/json",
                headers={"X-Custom-Header": "custom-value"},
            )

        response = client.get("/test-custom-header")

        assert response.status_code == 200
        # Custom header should be preserved
        assert response.headers.get("X-Custom-Header") == "custom-value"
        # Security headers should also be present
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["X-Frame-Options"] == "DENY"
