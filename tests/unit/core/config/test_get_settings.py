"""Unit tests for get_settings function."""

import pytest

from src.core.config import get_settings


@pytest.mark.unit
class TestGetSettings:
    """Test cases for get_settings function."""

    def test_get_settings_caching(self) -> None:
        """Test that get_settings returns the same instance (cached).

        Note: The clear_settings_cache fixture automatically clears cache
        before and after each test, so we test caching within a single test.
        """
        settings1 = get_settings()
        settings2 = get_settings()

        assert settings1 is settings2

    def test_get_settings_cache_clear(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that cache can be cleared to get new settings.

        The clear_settings_cache fixture handles automatic clearing,
        but we test manual clearing within a test.
        """
        # Get initial settings
        settings1 = get_settings()
        initial_name = settings1.app_name

        # Clear the cache manually
        get_settings.cache_clear()

        # Modify environment and get new settings
        monkeypatch.setenv("APP_NAME", "Modified App")
        settings2 = get_settings()

        assert settings1 is not settings2
        assert settings2.app_name == "Modified App"
        assert initial_name == "Tributum"  # Verify initial was default
