"""Unit tests for API constants."""

import pytest

from src.api.constants import CORRELATION_ID_HEADER


@pytest.mark.unit
class TestAPIConstants:
    """Test API constants."""

    def test_correlation_id_header_value(self) -> None:
        """Test that the correlation ID header has the expected value."""
        assert CORRELATION_ID_HEADER == "X-Correlation-ID"

    def test_correlation_id_header_is_string(self) -> None:
        """Test that the correlation ID header is a string."""
        assert isinstance(CORRELATION_ID_HEADER, str)
