"""Integration tests for configuration with FastAPI."""

import os
from unittest.mock import patch

from fastapi.testclient import TestClient

from src.api.main import create_app
from src.core.config import Settings, get_settings


class TestConfigurationIntegration:
    """Test configuration integration with FastAPI."""

    def test_app_created_with_settings(self) -> None:
        """Test that FastAPI app is created with correct settings."""
        settings = Settings(
            app_name="Test App",
            app_version="1.0.0",
            debug=False,
            docs_url="/test-docs",
            redoc_url="/test-redoc",
            openapi_url="/test-openapi.json",
        )

        app = create_app(settings)

        assert app.title == "Test App"
        assert app.version == "1.0.0"
        assert app.debug is False
        assert app.docs_url == "/test-docs"
        assert app.redoc_url == "/test-redoc"
        assert app.openapi_url == "/test-openapi.json"

    def test_info_endpoint_with_settings(self) -> None:
        """Test that /info endpoint returns correct settings."""
        # Clear the cache to ensure fresh settings
        get_settings.cache_clear()

        settings = Settings(
            app_name="Integration Test App",
            app_version="2.0.0",
            environment="staging",
            debug=True,
        )

        # Create a fresh app with test settings
        app = create_app(settings)

        # Override the dependency
        app.dependency_overrides[get_settings] = lambda: settings

        client = TestClient(app)

        response = client.get("/info")
        assert response.status_code == 200

        data = response.json()
        assert data["app_name"] == "Integration Test App"
        assert data["version"] == "2.0.0"
        assert data["environment"] == "staging"
        assert data["debug"] is True

        # Clean up
        app.dependency_overrides.clear()

    def test_app_with_environment_variables(self) -> None:
        """Test that app correctly uses environment variables."""
        # Clear cache first
        get_settings.cache_clear()

        with patch.dict(
            os.environ,
            {
                "APP_NAME": "Env Test App",
                "APP_VERSION": "3.0.0",
                "ENVIRONMENT": "production",
                "DEBUG": "false",
                "DOCS_URL": "",  # Should be converted to None
                "REDOC_URL": "",
                "OPENAPI_URL": "",
            },
        ):
            settings = get_settings()
            app = create_app(settings)

            assert app.title == "Env Test App"
            assert app.version == "3.0.0"
            assert app.debug is False
            assert app.docs_url is None
            assert app.redoc_url is None
            assert app.openapi_url is None

    def test_docs_disabled_with_empty_strings(self) -> None:
        """Test that empty string environment variables disable docs."""
        settings = Settings(docs_url="", redoc_url="", openapi_url="")

        assert settings.docs_url is None
        assert settings.redoc_url is None
        assert settings.openapi_url is None

        app = create_app(settings)
        assert app.docs_url is None
        assert app.redoc_url is None
        assert app.openapi_url is None
