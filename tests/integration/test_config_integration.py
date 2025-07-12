"""Integration tests for configuration with FastAPI."""

from collections.abc import Awaitable, Callable

import pytest
from httpx import AsyncClient

from src.api.main import create_app
from src.core.config import Settings, get_settings


@pytest.mark.integration
class TestConfigurationIntegration:
    """Test configuration integration with FastAPI."""

    async def test_app_created_with_settings(self) -> None:
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

        # Verify app instance properties are set correctly from settings
        assert app.title == "Test App"
        assert app.version == "1.0.0"
        assert app.debug is False
        assert app.docs_url == "/test-docs"
        assert app.redoc_url == "/test-redoc"
        assert app.openapi_url == "/test-openapi.json"

    async def test_info_endpoint_with_settings(
        self, client_with_settings: Callable[[Settings], Awaitable[AsyncClient]]
    ) -> None:
        """Test that /info endpoint returns correct settings."""
        # Note: clear_settings_cache fixture automatically handles cache clearing

        settings = Settings(
            app_name="Integration Test App",
            app_version="2.0.0",
            environment="staging",
            debug=True,
        )

        # Create client with custom settings
        client = await client_with_settings(settings)

        response = await client.get("/info")
        assert response.status_code == 200

        data = response.json()
        assert data["app_name"] == "Integration Test App"
        assert data["version"] == "2.0.0"
        assert data["environment"] == "staging"
        assert data["debug"] is True

    @pytest.mark.usefixtures("production_env")
    async def test_app_with_environment_variables(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that app correctly uses environment variables."""
        # Note: clear_settings_cache fixture automatically handles cache clearing
        # production_env fixture sets up production environment

        # Additional environment overrides on top of production environment
        monkeypatch.setenv("APP_NAME", "Env Test App")
        monkeypatch.setenv("APP_VERSION", "3.0.0")
        monkeypatch.setenv("DOCS_URL", "")  # Should be converted to None
        monkeypatch.setenv("REDOC_URL", "")
        monkeypatch.setenv("OPENAPI_URL", "")

        # Get settings from environment and create app
        settings = get_settings()
        app = create_app(settings)

        # Verify app instance properties reflect environment variables
        assert app.title == "Env Test App"
        assert app.version == "3.0.0"
        assert app.debug is False  # Production env sets debug=false
        assert app.docs_url is None
        assert app.redoc_url is None
        assert app.openapi_url is None

    async def test_docs_disabled_with_empty_strings(self) -> None:
        """Test that empty string environment variables disable docs."""
        settings = Settings(docs_url="", redoc_url="", openapi_url="")

        # Verify settings conversion
        assert settings.docs_url is None
        assert settings.redoc_url is None
        assert settings.openapi_url is None

        # Verify app instance also has docs disabled
        app = create_app(settings)
        assert app.docs_url is None
        assert app.redoc_url is None
        assert app.openapi_url is None

    @pytest.mark.usefixtures("custom_app_env")
    async def test_environment_reflected_in_app_creation(self) -> None:
        """Test that environment variables are properly reflected in app creation."""
        # custom_app_env sets APP_NAME="Custom Test App" and APP_VERSION="99.99.99"

        # Get settings after environment is set up
        settings = get_settings()

        # Create app with environment-based settings
        app = create_app(settings)

        # Verify app instance properties match environment
        assert app.title == "Custom Test App"
        assert app.version == "99.99.99"

    @pytest.mark.usefixtures("no_docs_env")
    async def test_docs_endpoints_disabled_in_app_creation(self) -> None:
        """Test that documentation endpoints can be disabled via environment."""
        # no_docs_env sets all doc URLs to empty strings

        # Get settings after environment is set up
        settings = get_settings()

        # Create app with environment-based settings
        app = create_app(settings)

        # Verify app instance has docs disabled
        assert app.docs_url is None
        assert app.redoc_url is None
        assert app.openapi_url is None
