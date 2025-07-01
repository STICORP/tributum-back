"""Unit tests for configuration auto-detection and helper functions."""

import pytest
from pytest_mock import MockerFixture

from src.core.config import LogConfig, Settings, get_config_defaults


@pytest.mark.unit
class TestAutoDetection:
    """Test auto-detection of formatters and exporters."""

    def test_detect_formatter_aws(
        self, mocker: MockerFixture, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test AWS environment detection for formatter."""
        # First clear the pytest-env ENVIRONMENT variable
        monkeypatch.delenv("ENVIRONMENT", raising=False)

        # Mock os.getenv to return AWS environment
        def mock_getenv(key: str, default: str | None = None) -> str | None:
            return {"AWS_EXECUTION_ENV": "AWS_ECS_FARGATE"}.get(key, default)

        mocker.patch("src.core.config.os.getenv", side_effect=mock_getenv)
        # Cloud env should take precedence even in development
        # We need to explicitly set log_formatter_type to None to trigger auto-detection
        settings = Settings(log_config=LogConfig(log_formatter_type=None))
        assert settings.log_config.log_formatter_type == "aws"

    def test_detect_formatter_json_production(self, mocker: MockerFixture) -> None:
        """Test JSON formatter fallback for production without cloud env."""
        # Mock os.getenv to return None for cloud environments
        mocker.patch("src.core.config.os.getenv", return_value=None)
        # Need to explicitly trigger auto-detection
        settings = Settings(
            environment="production", log_config=LogConfig(log_formatter_type=None)
        )
        assert settings.log_config.log_formatter_type == "json"

    def test_detect_exporter_gcp(self, mocker: MockerFixture) -> None:
        """Test GCP environment detection for exporter."""

        def mock_getenv(key: str, default: str | None = None) -> str | None:
            return {"K_SERVICE": "test-service"}.get(key, default)

        mocker.patch("src.core.config.os.getenv", side_effect=mock_getenv)
        settings = Settings(environment="production")
        assert settings.observability_config.exporter_type == "gcp"

    def test_detect_exporter_aws(self, mocker: MockerFixture) -> None:
        """Test AWS environment detection for exporter."""

        def mock_getenv(key: str, default: str | None = None) -> str | None:
            return {"AWS_EXECUTION_ENV": "AWS_ECS_FARGATE"}.get(key, default)

        mocker.patch("src.core.config.os.getenv", side_effect=mock_getenv)
        settings = Settings(environment="production")
        assert settings.observability_config.exporter_type == "aws"

    def test_detect_exporter_console_development(self, mocker: MockerFixture) -> None:
        """Test console exporter fallback for development."""
        # Mock to return None for cloud env checks
        mocker.patch("src.core.config.os.getenv", return_value=None)
        # Force auto-detection in development by manually calling the method
        settings = Settings(environment="development")
        # Call the private method directly to test the path
        assert settings._detect_exporter() == "console"


@pytest.mark.unit
class TestConfigDefaults:
    """Test configuration default helper function."""

    def test_get_config_defaults_production(self) -> None:
        """Test production config defaults."""
        defaults = get_config_defaults("production")

        assert defaults == {
            "log_config": {
                "log_formatter_type": "gcp",
            },
            "observability_config": {
                "exporter_type": "gcp",
            },
        }

    def test_get_config_defaults_development(self) -> None:
        """Test development config defaults."""
        defaults = get_config_defaults("development")

        assert defaults == {
            "log_config": {
                "log_formatter_type": "console",
            },
            "observability_config": {
                "exporter_type": "console",
            },
        }

    def test_get_config_defaults_other(self) -> None:
        """Test config defaults for other environments."""
        # Should use development defaults for any non-production environment
        defaults = get_config_defaults("staging")

        assert defaults == {
            "log_config": {
                "log_formatter_type": "console",
            },
            "observability_config": {
                "exporter_type": "console",
            },
        }
