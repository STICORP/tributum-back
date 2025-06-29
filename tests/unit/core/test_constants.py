"""Unit tests for core constants."""

import pytest

from src.core.constants import (
    MILLISECONDS_PER_SECOND,
    REDACTED,
    SENSITIVE_FIELD_PATTERNS,
)


@pytest.mark.unit
class TestConstants:
    """Test cases for core constants."""

    def test_time_constants(self) -> None:
        """Test that time constants have expected values."""
        assert MILLISECONDS_PER_SECOND == 1000

    def test_security_constants(self) -> None:
        """Test that security constants have expected values."""
        assert REDACTED == "[REDACTED]"

    def test_sensitive_field_patterns(self) -> None:
        """Test that sensitive field patterns are properly defined."""
        # Should be a list of regex patterns
        assert isinstance(SENSITIVE_FIELD_PATTERNS, list)
        assert len(SENSITIVE_FIELD_PATTERNS) > 0

        # Check some expected patterns are present
        expected_patterns = [
            r".*password.*",
            r".*secret.*",
            r".*token.*",
            r".*key.*",
            r".*auth.*",
            r".*credential.*",
            r".*api[-_]?key.*",
            r".*credit[-_]?card.*",
        ]

        for pattern in expected_patterns:
            assert pattern in SENSITIVE_FIELD_PATTERNS, (
                f"Expected pattern {pattern} not found"
            )

        # All patterns should be strings
        for pattern in SENSITIVE_FIELD_PATTERNS:
            assert isinstance(pattern, str)
