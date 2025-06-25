"""Unit tests for logging processors."""

import pytest
from pytest_mock import MockerFixture

from src.core.context import RequestContext
from src.core.logging import (
    add_log_level_upper,
    bind_logger_context,
    clear_logger_context,
    inject_correlation_id,
    inject_logger_context,
)


@pytest.mark.unit
class TestAddLogLevelUpper:
    """Test the add_log_level_upper processor."""

    def test_adds_uppercase_level(self, mocker: MockerFixture) -> None:
        """Test that log level is added in uppercase."""
        logger = mocker.MagicMock()
        event_dict: dict[str, object] = {}

        result = add_log_level_upper(logger, "info", event_dict)

        assert result["level"] == "INFO"

    def test_converts_warn_to_warning(self, mocker: MockerFixture) -> None:
        """Test that 'warn' is converted to 'WARNING'."""
        logger = mocker.MagicMock()
        event_dict: dict[str, object] = {}

        result = add_log_level_upper(logger, "warn", event_dict)

        assert result["level"] == "WARNING"

    def test_handles_all_log_levels(self, mocker: MockerFixture) -> None:
        """Test all log levels are converted correctly."""
        logger = mocker.MagicMock()
        levels = {
            "debug": "DEBUG",
            "info": "INFO",
            "warning": "WARNING",
            "error": "ERROR",
            "critical": "CRITICAL",
        }

        for method_name, expected_level in levels.items():
            event_dict: dict[str, object] = {}
            result = add_log_level_upper(logger, method_name, event_dict)
            assert result["level"] == expected_level


@pytest.mark.unit
class TestInjectCorrelationId:
    """Test the inject_correlation_id processor."""

    def test_injects_correlation_id_when_present(self, mocker: MockerFixture) -> None:
        """Test that correlation ID is injected when available."""
        # Set correlation ID in context
        test_correlation_id = "test-correlation-123"
        RequestContext.set_correlation_id(test_correlation_id)

        logger = mocker.MagicMock()
        event_dict: dict[str, object] = {}

        result = inject_correlation_id(logger, "info", event_dict)

        assert result["correlation_id"] == test_correlation_id

        # Clean up
        RequestContext.clear()

    def test_no_correlation_id_when_not_set(self, mocker: MockerFixture) -> None:
        """Test that no correlation ID is added when not in context."""
        # Ensure context is clear
        RequestContext.clear()

        logger = mocker.MagicMock()
        event_dict: dict[str, object] = {}

        result = inject_correlation_id(logger, "info", event_dict)

        assert "correlation_id" not in result

    def test_preserves_existing_fields(self, mocker: MockerFixture) -> None:
        """Test that existing fields are preserved."""
        RequestContext.set_correlation_id("test-id")

        logger = mocker.MagicMock()
        event_dict: dict[str, object] = {"existing": "value", "another": 123}

        result = inject_correlation_id(logger, "info", event_dict)

        assert result["existing"] == "value"
        assert result["another"] == 123
        assert result["correlation_id"] == "test-id"

        # Clean up
        RequestContext.clear()


@pytest.mark.unit
class TestInjectLoggerContext:
    """Test the inject_logger_context processor."""

    def test_injects_context_when_present(self, mocker: MockerFixture) -> None:
        """Test that logger context is injected when available."""
        # Set context in contextvar
        bind_logger_context(user_id=123, request_id="test-request")

        logger = mocker.MagicMock()
        event_dict: dict[str, object] = {"event": "test"}

        result = inject_logger_context(logger, "info", event_dict)

        assert result["user_id"] == 123
        assert result["request_id"] == "test-request"
        assert result["event"] == "test"

        # Clean up
        clear_logger_context()

    def test_no_context_when_not_set(self, mocker: MockerFixture) -> None:
        """Test that no context is added when not set."""
        # Ensure context is clear
        clear_logger_context()

        logger = mocker.MagicMock()
        event_dict: dict[str, object] = {"event": "test"}

        result = inject_logger_context(logger, "info", event_dict)

        assert result == {"event": "test"}
        assert "user_id" not in result
        assert "request_id" not in result

    def test_event_dict_takes_precedence(self, mocker: MockerFixture) -> None:
        """Test that event_dict values take precedence over context."""
        bind_logger_context(user_id=123, action="context_action")

        logger = mocker.MagicMock()
        event_dict: dict[str, object] = {"event": "test", "user_id": 456}

        result = inject_logger_context(logger, "info", event_dict)

        assert result["user_id"] == 456  # Event dict value wins
        assert result["action"] == "context_action"  # Context value added
        assert result["event"] == "test"

        # Clean up
        clear_logger_context()
