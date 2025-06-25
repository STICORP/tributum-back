"""Unit tests for exception logging functionality."""

from collections.abc import Generator

import pytest
import structlog
from pytest_mock import MockerFixture
from structlog.testing import LogCapture

from src.core.exceptions import (
    BusinessRuleError,
    ErrorCode,
    NotFoundError,
    Severity,
    TributumError,
    UnauthorizedError,
    ValidationError,
)
from src.core.logging import configure_structlog, get_logger, log_exception


@pytest.mark.unit
class TestLogException:
    """Test the log_exception function."""

    @pytest.fixture(autouse=True)
    def setup_structlog(self) -> Generator[None]:
        """Set up structlog for tests."""
        configure_structlog()
        yield
        # Reset structlog
        structlog.reset_defaults()

    def test_log_exception_with_tributum_error(self) -> None:
        """Test logging a TributumError with full context."""
        cap = LogCapture()
        structlog.configure(processors=[cap])

        logger = get_logger("test")
        error = ValidationError(
            "Invalid email format",
            context={"field": "email", "value": "not-an-email"},
        )

        log_exception(logger, error)

        assert len(cap.entries) == 1
        entry = cap.entries[0]
        assert entry["event"] == "[VALIDATION_ERROR] Invalid email format"
        assert entry["error_code"] == "VALIDATION_ERROR"
        assert entry["severity"] == "LOW"
        assert entry["fingerprint"] == error.fingerprint
        assert entry["error_context"] == {"field": "email", "value": "not-an-email"}
        assert entry["exc_info"] is not None

    def test_log_exception_with_custom_message(self) -> None:
        """Test logging with a custom message."""
        cap = LogCapture()
        structlog.configure(processors=[cap])

        logger = get_logger("test")
        error = NotFoundError("User not found")

        log_exception(logger, error, "Failed to fetch user")

        assert len(cap.entries) == 1
        assert cap.entries[0]["event"] == "Failed to fetch user"
        assert cap.entries[0]["error_code"] == "NOT_FOUND"

    def test_log_exception_with_extra_context(self) -> None:
        """Test logging with additional context."""
        cap = LogCapture()
        structlog.configure(processors=[cap])

        logger = get_logger("test")
        error = UnauthorizedError("Invalid token")

        log_exception(logger, error, user_id=123, endpoint="/api/users")

        assert len(cap.entries) == 1
        entry = cap.entries[0]
        assert entry["user_id"] == 123
        assert entry["endpoint"] == "/api/users"
        assert entry["severity"] == "HIGH"

    def test_log_exception_severity_levels(self, mocker: MockerFixture) -> None:
        """Test that different severities use appropriate log levels."""
        # Mock logger to track method calls
        mock_logger = mocker.MagicMock()

        # Test LOW severity - should use warning
        low_error = ValidationError("Low severity")
        log_exception(mock_logger, low_error)
        mock_logger.warning.assert_called_once()
        mock_logger.error.assert_not_called()

        # Reset mock
        mock_logger.reset_mock()

        # Test MEDIUM severity - should use error
        medium_error = BusinessRuleError("Medium severity")
        log_exception(mock_logger, medium_error)
        mock_logger.error.assert_called_once()

        # Reset mock
        mock_logger.reset_mock()

        # Test HIGH severity - should use error
        high_error = UnauthorizedError("High severity")
        log_exception(mock_logger, high_error)
        mock_logger.error.assert_called_once()

        # Reset mock
        mock_logger.reset_mock()

        # Test CRITICAL severity - should use critical
        critical_error = TributumError(
            ErrorCode.INTERNAL_ERROR, "Critical error", severity=Severity.CRITICAL
        )
        log_exception(mock_logger, critical_error)
        mock_logger.critical.assert_called_once()

    def test_log_exception_with_standard_exception(self) -> None:
        """Test logging a standard Python exception."""
        cap = LogCapture()
        structlog.configure(processors=[cap])

        logger = get_logger("test")
        error = ValueError("Invalid value")

        log_exception(logger, error)

        assert len(cap.entries) == 1
        entry = cap.entries[0]
        assert entry["event"] == "Invalid value"
        assert entry["error_type"] == "ValueError"
        assert "error_code" not in entry
        assert "severity" not in entry
        assert entry["exc_info"] is not None

    def test_log_exception_with_cause(self) -> None:
        """Test logging an exception with a cause."""
        cap = LogCapture()
        structlog.configure(processors=[cap])

        logger = get_logger("test")

        try:
            int("not a number")
        except ValueError as e:
            error = ValidationError("Invalid format", cause=e)
            log_exception(logger, error)

        assert len(cap.entries) == 1
        entry = cap.entries[0]
        assert entry["error_code"] == "VALIDATION_ERROR"
        # The cause should be part of the exc_info
        assert entry["exc_info"] is not None

    def test_log_exception_empty_context(self) -> None:
        """Test logging TributumError with empty context."""
        cap = LogCapture()
        structlog.configure(processors=[cap])

        logger = get_logger("test")
        error = TributumError(ErrorCode.INTERNAL_ERROR, "System error")

        log_exception(logger, error)

        assert len(cap.entries) == 1
        entry = cap.entries[0]
        assert "error_context" not in entry
        assert entry["error_code"] == "INTERNAL_ERROR"

    def test_log_exception_chain_handling(self) -> None:
        """Test that exception chains are preserved in logging."""
        cap = LogCapture()
        structlog.configure(processors=[cap])

        logger = get_logger("test")

        try:
            try:
                raise ValueError("Original error")
            except ValueError as e:
                raise BusinessRuleError("Business rule failed", cause=e) from e
        except BusinessRuleError as business_error:
            log_exception(logger, business_error)

        assert len(cap.entries) == 1
        entry = cap.entries[0]
        assert entry["error_code"] == "INTERNAL_ERROR"
        # The exc_info should contain the full exception chain
        assert entry["exc_info"] is not None
