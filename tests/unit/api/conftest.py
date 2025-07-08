"""Conftest for API unit tests."""

import sys

import pytest
from pytest_mock import MockerFixture


@pytest.fixture(autouse=True)
def mock_api_main_dependencies(mocker: MockerFixture) -> None:
    """Mock all dependencies before importing src.api.main."""
    # This fixture runs before each test to ensure clean mocking
    if "src.api.main" in sys.modules:
        del sys.modules["src.api.main"]

    # Mock all external dependencies at the module level
    mocker.patch(
        "src.api.main.check_database_connection", new_callable=mocker.AsyncMock
    )
    mocker.patch("src.api.main.close_database", new_callable=mocker.AsyncMock)
    mocker.patch("src.api.main.setup_logging")
    mocker.patch("src.api.main.setup_tracing")
    mocker.patch("src.api.main.register_exception_handlers")
    mocker.patch("src.api.main.instrument_app")
    mocker.patch("src.api.main.SecurityHeadersMiddleware")
    mocker.patch("src.api.main.RequestContextMiddleware")
    mocker.patch("src.api.main.RequestLoggingMiddleware")
    mocker.patch("src.api.main.logger")
