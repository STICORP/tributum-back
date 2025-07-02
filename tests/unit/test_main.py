"""Unit tests for main.py entry point."""

import pytest
from pytest_mock import MockerFixture

import main as main_module
from main import main


@pytest.mark.unit
class TestMainEntryPoint:
    """Test main.py entry point functionality."""

    def test_main_function_runs_uvicorn_in_debug_mode(
        self, mocker: MockerFixture
    ) -> None:
        """Test that main() calls uvicorn.run with import string in debug mode."""
        mock_settings = mocker.MagicMock()
        mock_settings.debug = True
        mock_settings.api_host = "127.0.0.1"
        mock_settings.api_port = 8000
        mock_settings.log_config.log_level = "INFO"

        mocker.patch("main.get_settings", return_value=mock_settings)
        mocker.patch("main.setup_logging")  # Mock setup_logging to prevent side effects
        mock_run = mocker.patch("main.uvicorn.run")

        main()

        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args

        # In debug mode, app is passed as import string
        assert args[0] == "src.api.main:app"
        assert kwargs["host"] == "127.0.0.1"
        assert kwargs["port"] == 8000
        assert kwargs["reload"] is True
        assert "log_config" in kwargs
        assert isinstance(kwargs["log_config"], dict)

    def test_main_function_runs_uvicorn_in_production_mode(
        self, mocker: MockerFixture
    ) -> None:
        """Test that main() calls uvicorn.run with app object in production mode."""
        mock_settings = mocker.MagicMock()
        mock_settings.debug = False
        mock_settings.api_host = "127.0.0.1"
        mock_settings.api_port = 8000
        mock_settings.log_config.log_level = "INFO"

        mocker.patch("main.get_settings", return_value=mock_settings)
        mocker.patch("main.setup_logging")  # Mock setup_logging to prevent side effects
        mock_run = mocker.patch("main.uvicorn.run")

        main()

        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args

        # In production mode, app object is passed
        assert args[0] is not None
        assert kwargs["host"] == "127.0.0.1"
        assert kwargs["port"] == 8000
        assert kwargs["reload"] is False
        assert "log_config" in kwargs
        assert isinstance(kwargs["log_config"], dict)

    def test_main_module_can_be_imported(self) -> None:
        """Test that the main module can be imported without errors."""
        assert hasattr(main_module, "main")
        assert callable(main_module.main)
