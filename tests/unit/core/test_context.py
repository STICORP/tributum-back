"""Unit tests for the context module."""

import re
import uuid

from src.core.context import CORRELATION_ID_HEADER, generate_correlation_id


class TestCorrelationIDGeneration:
    """Test correlation ID generation functionality."""

    def test_generate_correlation_id_returns_string(self) -> None:
        """Test that generate_correlation_id returns a string."""
        correlation_id = generate_correlation_id()
        assert isinstance(correlation_id, str)

    def test_generate_correlation_id_is_valid_uuid(self) -> None:
        """Test that generated correlation ID is a valid UUID."""
        correlation_id = generate_correlation_id()
        # Should not raise an exception
        parsed_uuid = uuid.UUID(correlation_id)
        assert str(parsed_uuid) == correlation_id

    def test_generate_correlation_id_is_uuid4(self) -> None:
        """Test that generated correlation ID is specifically a UUID4."""
        correlation_id = generate_correlation_id()
        parsed_uuid = uuid.UUID(correlation_id)
        assert parsed_uuid.version == 4

    def test_generate_correlation_id_format(self) -> None:
        """Test that correlation ID has the correct UUID format."""
        correlation_id = generate_correlation_id()
        # UUID4 format: xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx
        # where y is one of 8, 9, A, or B
        uuid_pattern = re.compile(
            r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
            re.IGNORECASE,
        )
        assert uuid_pattern.match(correlation_id) is not None

    def test_generate_correlation_id_uniqueness(self) -> None:
        """Test that each generated correlation ID is unique."""
        # Generate multiple IDs
        ids = [generate_correlation_id() for _ in range(100)]
        # Check all are unique
        assert len(ids) == len(set(ids))

    def test_generate_correlation_id_length(self) -> None:
        """Test that correlation ID has the expected length."""
        correlation_id = generate_correlation_id()
        # UUID string length is always 36 (32 hex chars + 4 hyphens)
        assert len(correlation_id) == 36


class TestCorrelationIDHeader:
    """Test correlation ID header constant."""

    def test_correlation_id_header_value(self) -> None:
        """Test that the correlation ID header has the expected value."""
        assert CORRELATION_ID_HEADER == "X-Correlation-ID"

    def test_correlation_id_header_is_immutable(self) -> None:
        """Test that the correlation ID header cannot be modified."""
        # This test verifies the use of Final typing
        # The actual immutability is enforced by type checkers
        assert isinstance(CORRELATION_ID_HEADER, str)
