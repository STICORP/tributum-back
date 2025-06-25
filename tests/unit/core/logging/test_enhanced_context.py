"""Unit tests for enhanced context management features."""

from collections.abc import Generator

import pytest
from pytest_mock import MockerFixture

from src.core.constants import MAX_VALUE_SIZE
from src.core.logging import (
    _context_manager,
    bind_logger_context,
    clear_logger_context,
    configure_structlog,
    get_logger_context,
    inject_logger_context,
    unbind_logger_context,
)


@pytest.mark.unit
class TestEnhancedContextManagement:
    """Test the enhanced context management features."""

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self) -> Generator[None]:
        """Set up structlog and clean up context after each test."""
        configure_structlog()
        # Clear any existing context
        clear_logger_context()
        # Reset the global context manager
        _context_manager._context_stack.clear()
        yield
        # Clean up after test
        clear_logger_context()
        _context_manager._context_stack.clear()

    def test_get_logger_context_empty(self) -> None:
        """Test get_logger_context returns empty dict when no context."""
        context = get_logger_context()
        assert context == {}

    def test_get_logger_context_with_data(self) -> None:
        """Test get_logger_context returns copy of current context."""
        bind_logger_context(user_id=123, session_id="abc")

        context = get_logger_context()
        assert context == {"user_id": 123, "session_id": "abc"}

        # Verify it's a copy, not a reference
        context["user_id"] = 456
        new_context = get_logger_context()
        assert new_context["user_id"] == 123

    def test_unbind_logger_context_single_key(self) -> None:
        """Test unbinding a single key from context."""
        bind_logger_context(user_id=123, session_id="abc", temp="value")

        unbind_logger_context("temp")

        context = get_logger_context()
        assert context == {"user_id": 123, "session_id": "abc"}
        assert "temp" not in context

    def test_unbind_logger_context_multiple_keys(self) -> None:
        """Test unbinding multiple keys from context."""
        bind_logger_context(a=1, b=2, c=3, d=4)

        unbind_logger_context("b", "d")

        context = get_logger_context()
        assert context == {"a": 1, "c": 3}

    def test_unbind_logger_context_nonexistent_key(self) -> None:
        """Test unbinding nonexistent key doesn't raise error."""
        bind_logger_context(user_id=123)

        unbind_logger_context("nonexistent")

        context = get_logger_context()
        assert context == {"user_id": 123}

    def test_unbind_logger_context_clears_when_empty(self) -> None:
        """Test context is set to None when all keys are unbound."""
        bind_logger_context(only_key="value")

        unbind_logger_context("only_key")

        context = get_logger_context()
        assert context == {}


@pytest.mark.unit
class TestEnhancedInjectLoggerContext:
    """Test the enhanced inject_logger_context processor."""

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self) -> Generator[None]:
        """Set up and clean up for each test."""
        clear_logger_context()
        _context_manager._context_stack.clear()
        yield
        clear_logger_context()
        _context_manager._context_stack.clear()

    def test_inject_with_none_values_filtered(self, mocker: MockerFixture) -> None:
        """Test that None values are filtered out."""
        bind_logger_context(user_id=123, session_id=None, action="login")

        logger = mocker.MagicMock()
        event_dict: dict[str, object] = {"event": "test"}

        result = inject_logger_context(logger, "info", event_dict)

        assert result["user_id"] == 123
        assert result["action"] == "login"
        assert "session_id" not in result

    def test_inject_with_context_depth(self, mocker: MockerFixture) -> None:
        """Test that context depth is added when using LogContextManager."""
        _context_manager.push(layer1="value1")
        _context_manager.push(layer2="value2")

        logger = mocker.MagicMock()
        event_dict: dict[str, object] = {"event": "test"}

        result = inject_logger_context(logger, "info", event_dict)

        assert result["context_depth"] == 2
        assert result["layer1"] == "value1"
        assert result["layer2"] == "value2"

    def test_inject_with_value_truncation(self, mocker: MockerFixture) -> None:
        """Test that large values are truncated."""
        large_value = "x" * (MAX_VALUE_SIZE + 100)
        bind_logger_context(large_field=large_value)

        logger = mocker.MagicMock()
        event_dict: dict[str, object] = {"event": "test"}

        result = inject_logger_context(logger, "info", event_dict)

        # Check that the field was injected and truncated
        assert "large_field" in result
        # Should be truncated to MAX_VALUE_SIZE characters total
        assert len(result["large_field"]) == MAX_VALUE_SIZE
        assert result["large_field"].endswith("...")
        # The actual content should be MAX_VALUE_SIZE - 3 characters plus "..."
        assert result["large_field"] == large_value[: MAX_VALUE_SIZE - 3] + "..."

    def test_inject_with_total_size_limit(self, mocker: MockerFixture) -> None:
        """Test that total context size is limited."""
        # Create context that exceeds total size
        context_data = {}
        for i in range(100):
            key = f"field_{i:03d}"
            value = "x" * 200  # Each field is ~200 bytes
            context_data[key] = value

        bind_logger_context(**context_data)

        logger = mocker.MagicMock()
        event_dict: dict[str, object] = {"event": "test"}

        result = inject_logger_context(logger, "info", event_dict)

        # Should have truncation indicator
        assert result["context_truncated"] is True

        # Should have some fields but not all
        injected_fields = [k for k in result if k.startswith("field_")]
        assert len(injected_fields) > 0
        assert len(injected_fields) < 100

    def test_inject_preserves_event_dict_priority(self, mocker: MockerFixture) -> None:
        """Test that event_dict values take precedence over context."""
        bind_logger_context(user_id=123, action="context_action")

        logger = mocker.MagicMock()
        event_dict: dict[str, object] = {
            "event": "test",
            "user_id": 456,  # Should override context
        }

        result = inject_logger_context(logger, "info", event_dict)

        assert result["user_id"] == 456  # Event dict value
        assert result["action"] == "context_action"  # From context
