"""Tests for RequestLoggingMiddleware configuration options."""

from typing import Any

import pytest
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture
from starlette.datastructures import Headers

from src.api.middleware.request_logging import RequestLoggingMiddleware
from src.core.constants import MAX_BODY_SIZE, TRUNCATED_SUFFIX

from .conftest import create_test_app


@pytest.mark.unit
class TestMiddlewareConfiguration:
    """Test middleware configuration options."""

    def test_custom_max_body_size(self, mocker: MockerFixture) -> None:
        """Test that custom max body size is respected."""
        middleware = RequestLoggingMiddleware(
            mocker.Mock(), log_request_body=True, max_body_size=100
        )
        assert middleware.max_body_size == 100

    def test_default_configuration(self, mocker: MockerFixture) -> None:
        """Test default middleware configuration."""
        middleware = RequestLoggingMiddleware(mocker.Mock())
        assert middleware.log_request_body is False
        assert middleware.log_response_body is False
        assert middleware.max_body_size == MAX_BODY_SIZE

    def test_truncate_body_method(self, mocker: MockerFixture) -> None:
        """Test the truncate body method."""
        middleware = RequestLoggingMiddleware(mocker.Mock(), max_body_size=10)

        # Test string truncation
        result = middleware._truncate_body("Hello World!")
        assert result == "Hello Worl" + TRUNCATED_SUFFIX

        # Test bytes truncation
        result = middleware._truncate_body(b"Hello World!")
        assert result == "Hello Worl" + TRUNCATED_SUFFIX

        # Test no truncation needed
        result = middleware._truncate_body("Short")
        assert result == "Short"

        # Test binary data that can't be decoded - within size limit
        # The method tries to decode with errors='replace'
        # so it will show replacement chars
        result = middleware._truncate_body(b"\xff\xfe\xfd")
        assert len(result) == 3  # Should be decoded with replacement characters

        # Test binary data that can't be decoded - needs truncation
        # This covers lines 126-131
        binary_data = bytes([0xFF, 0xFE] * 20)  # 40 bytes of non-UTF8 data
        result = middleware._truncate_body(binary_data)
        assert result.endswith(TRUNCATED_SUFFIX)
        # The method decodes with errors='replace' so we get replacement chars
        assert len(result) > 10  # Should be truncated

    def test_truncate_body_decode_exception(self, mocker: MockerFixture) -> None:
        """Test _truncate_body handles decode exceptions (lines 123-124, 130-131)."""
        middleware = RequestLoggingMiddleware(mocker.Mock(), max_body_size=50)

        # Create a custom bytes class that raises exception on decode
        class BadBytes(bytes):
            def decode(self, *_args: Any, **_kwargs: Any) -> str:  # noqa: ANN401 - test mock accepts any args
                raise UnicodeDecodeError("utf-8", b"", 0, 1, "Simulated decode error")

            def __getitem__(self, key: Any) -> Any:  # noqa: ANN401 - test mock for bytes operations
                # Ensure slicing returns BadBytes to maintain the decode override
                result = super().__getitem__(key)
                if isinstance(key, slice):
                    return BadBytes(result)
                return result

        # Test case 1: decode exception for body within max size (lines 123-124)
        bad_short = BadBytes(b"short")
        result = middleware._truncate_body(bad_short)
        assert result == "<binary data: 5 bytes>"

        # Test case 2: decode exception for truncated body (lines 130-131)
        bad_long = BadBytes(b"a" * 100)
        result = middleware._truncate_body(bad_long)
        assert result == f"<binary data: 100 bytes>{TRUNCATED_SUFFIX}"

    def test_handles_missing_content_type(self, mocker: MockerFixture) -> None:
        """Test that middleware handles missing content-type header."""
        mock_logger = mocker.Mock()
        mocker.patch(
            "src.api.middleware.request_logging.get_logger", return_value=mock_logger
        )

        app = create_test_app(log_request_body=True)
        client = TestClient(app)

        # Send request without content-type header
        client.post("/raw-text", content=b"Some binary data")

        # Find the request_started call
        started_calls = [
            c for c in mock_logger.info.call_args_list if c[0][0] == "request_started"
        ]
        assert len(started_calls) == 1

        # Verify unknown content type was handled
        call_kwargs = started_calls[0][1]
        assert "body" in call_kwargs
        assert call_kwargs["body"]["_type"] == "unknown"
        assert call_kwargs["body"]["_size"] == 16
        assert call_kwargs["body"]["_info"] == "Binary content not logged"

    def test_content_type_extraction(self) -> None:
        """Test content type extraction."""
        # Test the static method directly

        headers = Headers({"content-type": "application/json; charset=utf-8"})
        content_type = RequestLoggingMiddleware._get_content_type(headers)
        assert content_type == "application/json"

        headers = Headers({"content-type": "text/plain"})
        content_type = RequestLoggingMiddleware._get_content_type(headers)
        assert content_type == "text/plain"

        headers = Headers({})
        content_type = RequestLoggingMiddleware._get_content_type(headers)
        assert content_type == ""
