"""Unit tests for main.py module."""

from pathlib import Path

import pytest
from pytest_mock import MockerFixture, MockType

import main
from src.core.config import Settings


@pytest.mark.unit
class TestMainFunction:
    """Test class for main() function and module execution."""

    def test_main_loads_settings_and_sets_up_logging(
        self,
        mock_main_dependencies: dict[str, MockType],
        mock_settings: Settings,
    ) -> None:
        """Verify that main() correctly loads settings and initializes logging."""
        # Call main after mocks are in place
        main.main()

        # Assert get_settings was called once
        mock_main_dependencies["get_settings"].assert_called_once()

        # Assert setup_logging was called once with the mock settings
        mock_main_dependencies["setup_logging"].assert_called_once_with(mock_settings)

    @pytest.mark.parametrize(
        ("env_port", "expected_port"),
        [
            ("8080", 8080),  # PORT env var takes precedence
            (None, 3000),  # No PORT env var, use settings.api_port
            ("9999", 9999),  # Different PORT value
        ],
    )
    def test_port_precedence(
        self,
        mocker: MockerFixture,
        mock_uvicorn: MockType,
        mock_settings: Settings,
        isolated_env: pytest.MonkeyPatch,
        env_port: str | None,
        expected_port: int,
    ) -> None:
        """Verify PORT environment variable precedence over settings."""
        # Set or unset PORT environment variable
        if env_port is not None:
            isolated_env.setenv("PORT", env_port)
        else:
            isolated_env.delenv("PORT", raising=False)

        # Mock settings with api_port=3000
        mock_get_settings = mocker.patch("main.get_settings")
        mock_get_settings.return_value = mock_settings

        # Mock other dependencies
        mocker.patch("main.setup_logging")
        mocker.patch("main.logger.info")

        # Call main
        main.main()

        # Assert uvicorn.run called with expected port
        mock_uvicorn.assert_called_once()
        call_kwargs = mock_uvicorn.call_args.kwargs
        assert call_kwargs["port"] == expected_port

    def test_main_configures_uvicorn_logging_correctly(
        self,
        mocker: MockerFixture,
        mock_uvicorn: MockType,
        mock_settings: Settings,
    ) -> None:
        """Verify uvicorn logging configuration structure."""
        # Mock dependencies
        mock_get_settings = mocker.patch("main.get_settings")
        mock_get_settings.return_value = mock_settings
        mocker.patch("main.setup_logging")
        mocker.patch("main.logger.info")

        # Call main
        main.main()

        # Capture the log_config argument passed to uvicorn.run
        mock_uvicorn.assert_called_once()
        call_kwargs = mock_uvicorn.call_args.kwargs
        log_config = call_kwargs["log_config"]

        # Assert log_config has correct structure
        assert log_config["version"] == 1
        assert log_config["disable_existing_loggers"] is False

        # Check handlers
        assert "default" in log_config["handlers"]
        assert (
            log_config["handlers"]["default"]["class"]
            == "src.core.logging.InterceptHandler"
        )

        # Check loggers
        assert "uvicorn" in log_config["loggers"]
        assert "uvicorn.error" in log_config["loggers"]
        assert "uvicorn.access" in log_config["loggers"]

        # Check logger configuration
        for logger_name in ["uvicorn", "uvicorn.error", "uvicorn.access"]:
            logger_config = log_config["loggers"][logger_name]
            assert logger_config["handlers"] == ["default"]
            assert logger_config["level"] == "INFO"
            assert logger_config["propagate"] is False

    @pytest.mark.parametrize(
        ("debug", "expected_app", "expected_reload", "expected_log_contains"),
        [
            (True, "src.api.main:app", True, "development mode with auto-reload"),
            (False, "app", False, "production mode"),
        ],
    )
    def test_main_parametrized_debug_modes(
        self,
        mocker: MockerFixture,
        mock_uvicorn: MockType,
        mock_settings: Settings,
        mock_app: MockType,
        debug: bool,
        expected_app: str,
        expected_reload: bool,
        expected_log_contains: str,
    ) -> None:
        """Test both debug and production modes with parametrization."""
        # Configure mock settings with debug flag
        mock_settings.debug = debug
        mock_get_settings = mocker.patch("main.get_settings")
        mock_get_settings.return_value = mock_settings

        # Mock other dependencies
        mocker.patch("main.setup_logging")
        mock_logger = mocker.patch("main.logger.info")

        # For production mode, we need to mock the app import
        if not debug:
            mocker.patch("main.app", mock_app)

        # Call main
        main.main()

        # Assert uvicorn.run called with correct parameters
        mock_uvicorn.assert_called_once()
        call_args = mock_uvicorn.call_args

        # Check app parameter
        if debug:
            assert call_args.args[0] == expected_app
        else:
            # In production mode, the actual app object is passed
            assert call_args.args[0] == mock_app

        # Check other parameters
        call_kwargs = call_args.kwargs
        assert call_kwargs["host"] == mock_settings.api_host
        assert call_kwargs["port"] == mock_settings.api_port
        assert call_kwargs["reload"] == expected_reload

        # Check logger message
        mock_logger.assert_called_once()
        log_message = mock_logger.call_args.args[0]
        assert expected_log_contains in log_message

    def test_main_module_execution(
        self,
    ) -> None:
        """Verify the if __name__ == '__main__' block exists and calls main()."""
        # Read the main.py file to verify its structure
        with Path("main.py").open() as f:
            content = f.read()

        # Verify the if __name__ == "__main__" block exists
        assert 'if __name__ == "__main__":' in content

        # Find the if __name__ block and verify it calls main()
        lines = content.split("\n")
        found_main_guard = False
        for i, line in enumerate(lines):
            if 'if __name__ == "__main__":' in line:
                found_main_guard = True
                # Check the next non-empty line calls main()
                for j in range(i + 1, len(lines)):
                    next_line = lines[j].strip()
                    if next_line:
                        msg = (
                            f"Expected 'main()' after if __name__ guard, "
                            f"found: {next_line}"
                        )
                        assert next_line == "main()", msg
                        break
                break

        assert found_main_guard, "if __name__ == '__main__': block not found"

    def test_port_environment_variable_type_conversion(
        self,
        mocker: MockerFixture,
        mock_uvicorn: MockType,
        mock_settings: Settings,
        isolated_env: pytest.MonkeyPatch,
    ) -> None:
        """Verify PORT env var is correctly converted to integer."""
        # Set PORT as string
        isolated_env.setenv("PORT", "9999")

        # Mock dependencies
        mock_get_settings = mocker.patch("main.get_settings")
        mock_get_settings.return_value = mock_settings
        mocker.patch("main.setup_logging")
        mocker.patch("main.logger.info")

        # Call main
        main.main()

        # Assert uvicorn.run receives port as integer 9999, not string
        mock_uvicorn.assert_called_once()
        call_kwargs = mock_uvicorn.call_args.kwargs
        port = call_kwargs["port"]
        assert port == 9999
        assert isinstance(port, int)

    @pytest.mark.parametrize(
        ("port_value", "error_pattern"),
        [
            ("invalid", "invalid literal for int"),
            ("", r"invalid literal for int\(\) with base 10: ''"),
            ("12.34", "invalid literal for int"),
            ("8080abc", "invalid literal for int"),
        ],
    )
    def test_invalid_port_environment_variable(
        self,
        mocker: MockerFixture,
        mock_settings: Settings,
        isolated_env: pytest.MonkeyPatch,
        port_value: str,
        error_pattern: str,
    ) -> None:
        """Verify behavior with invalid PORT values raises appropriate error."""
        # Set PORT to invalid value
        isolated_env.setenv("PORT", port_value)

        # Mock dependencies
        mock_get_settings = mocker.patch("main.get_settings")
        mock_get_settings.return_value = mock_settings
        mocker.patch("main.setup_logging")

        # Test will use the imported main module
        # Assert ValueError is raised
        with pytest.raises(ValueError, match=error_pattern):
            main.main()
