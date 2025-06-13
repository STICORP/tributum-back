"""Unit tests for main.py entry point."""

from unittest.mock import patch

import pytest

from main import main


@pytest.mark.unit
def test_main_function_runs_uvicorn() -> None:
    """Test that main() calls uvicorn.run with correct parameters."""
    with patch("main.uvicorn.run") as mock_run:
        main()

        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args

        # Verify app is passed
        assert args[0] is not None

        # Verify host and port
        assert kwargs.get("host") == "127.0.0.1"
        assert kwargs.get("port") == 8000


@pytest.mark.unit
def test_main_module_can_be_imported() -> None:
    """Test that the main module can be imported without errors."""
    import main

    assert hasattr(main, "main")
    assert callable(main.main)
    assert hasattr(main, "app")
