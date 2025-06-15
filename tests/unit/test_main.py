"""Unit tests for main.py entry point."""

from unittest.mock import MagicMock, patch

import pytest

from main import main


@pytest.mark.unit
def test_main_function_runs_uvicorn_in_debug_mode() -> None:
    """Test that main() calls uvicorn.run with import string in debug mode."""
    mock_settings = MagicMock()
    mock_settings.debug = True
    mock_settings.api_host = "127.0.0.1"
    mock_settings.api_port = 8000
    mock_settings.log_config.log_level = "INFO"

    with (
        patch("main.get_settings", return_value=mock_settings),
        patch("main.uvicorn.run") as mock_run,
    ):
        main()

        mock_run.assert_called_once_with(
            "src.api.main:app",
            host="127.0.0.1",
            port=8000,
            reload=True,
            log_level="info",
        )


@pytest.mark.unit
def test_main_function_runs_uvicorn_in_production_mode() -> None:
    """Test that main() calls uvicorn.run with app object in production mode."""
    mock_settings = MagicMock()
    mock_settings.debug = False
    mock_settings.api_host = "127.0.0.1"
    mock_settings.api_port = 8000
    mock_settings.log_config.log_level = "INFO"

    with (
        patch("main.get_settings", return_value=mock_settings),
        patch("main.uvicorn.run") as mock_run,
    ):
        main()

        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args

        # In production mode, app object is passed
        assert args[0] is not None
        assert kwargs["host"] == "127.0.0.1"
        assert kwargs["port"] == 8000
        assert kwargs["reload"] is False
        assert kwargs["log_level"] == "info"


@pytest.mark.unit
def test_main_module_can_be_imported() -> None:
    """Test that the main module can be imported without errors."""
    import main

    assert hasattr(main, "main")
    assert callable(main.main)
