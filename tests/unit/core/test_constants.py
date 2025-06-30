"""Unit tests for core constants."""

import pytest

from src.core.constants import MILLISECONDS_PER_SECOND, REDACTED


@pytest.mark.unit
class TestConstants:
    """Test cases for core constants."""

    def test_time_constants(self) -> None:
        """Test that time constants have expected values."""
        assert MILLISECONDS_PER_SECOND == 1000

    def test_security_constants(self) -> None:
        """Test that security constants have expected values."""
        assert REDACTED == "[REDACTED]"
