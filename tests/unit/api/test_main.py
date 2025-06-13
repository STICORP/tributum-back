"""Unit tests for FastAPI app configuration."""

import pytest
from fastapi import FastAPI

from src.api.main import app


@pytest.mark.unit
def test_app_instance() -> None:
    """Test that app is a FastAPI instance."""
    assert isinstance(app, FastAPI)


@pytest.mark.unit
def test_app_title() -> None:
    """Test that app has correct title."""
    assert app.title == "Tributum"


@pytest.mark.unit
def test_app_version() -> None:
    """Test that app has correct version."""
    assert app.version == "0.1.0"


@pytest.mark.unit
def test_app_has_expected_routes() -> None:
    """Test that app has expected routes configured."""
    # FastAPI automatically adds these routes
    response = app.router.url_path_for("root")
    assert response == "/"

    # Check that OpenAPI routes are available
    openapi_url = app.openapi_url
    assert openapi_url == "/openapi.json"

    docs_url = app.docs_url
    assert docs_url == "/docs"

    redoc_url = app.redoc_url
    assert redoc_url == "/redoc"
