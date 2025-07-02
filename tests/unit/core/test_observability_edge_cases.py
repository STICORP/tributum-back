"""Tests for edge cases in observability module."""

import pytest
from pytest_mock import MockerFixture

from src.core.observability import LoguruSpanExporter


@pytest.mark.unit
class TestObservabilityEdgeCases:
    """Test edge cases in observability module."""

    def test_loguru_span_exporter_filters_noisy_spans(
        self, mocker: MockerFixture
    ) -> None:
        """Test that LoguruSpanExporter filters out noisy internal spans."""
        exporter = LoguruSpanExporter()

        # Mock logger to check it's not called for filtered spans
        mock_logger = mocker.patch("src.core.observability.logger")

        # Create mock spans with noisy names
        noisy_span_names = ["connect", "http send", "http receive", "cursor.execute"]

        for span_name in noisy_span_names:
            # Create a simple mock span with just the name property
            span = mocker.MagicMock()
            span.name = span_name

            # Export the span
            exporter.export([span])

            # Logger should not be called for noisy spans
            mock_logger.bind.assert_not_called()

        # Reset the mock for the next test
        mock_logger.reset_mock()

        # Test with a non-noisy span
        normal_span = mocker.MagicMock()
        normal_span.name = "GET /api/users"
        normal_span.get_span_context.return_value.trace_id = 12345
        normal_span.get_span_context.return_value.span_id = 67890
        normal_span.parent = None
        normal_span.kind.name = "SERVER"
        normal_span.status.status_code.name = "OK"
        normal_span.start_time = 1000000000
        normal_span.end_time = 1001000000
        normal_span.attributes = {"http.method": "GET", "http.path": "/api/users"}
        normal_span.events = []

        # Export the normal span
        exporter.export([normal_span])

        # Logger should be called for normal spans
        mock_logger.bind.assert_called_once()
