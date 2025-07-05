"""Tests for is_expected and should_alert properties on TributumError."""

import pytest

from src.core.exceptions import (
    BusinessRuleError,
    NotFoundError,
    Severity,
    TributumError,
    UnauthorizedError,
    ValidationError,
)


@pytest.mark.unit
class TestExpectedErrorClassification:
    """Test is_expected property for different error types."""

    def test_low_severity_errors_are_expected(self) -> None:
        """Low severity errors should be marked as expected."""
        # ValidationError has LOW severity by default
        error = ValidationError("Invalid email format")
        assert error.is_expected is True
        assert error.should_alert is False

    def test_medium_severity_errors_are_expected(self) -> None:
        """Medium severity errors should be marked as expected."""
        # BusinessRuleError has MEDIUM severity by default
        error = BusinessRuleError("Insufficient balance")
        assert error.is_expected is True
        assert error.should_alert is False

    def test_high_severity_errors_are_unexpected(self) -> None:
        """High severity errors should be marked as unexpected."""
        # UnauthorizedError has HIGH severity by default
        error = UnauthorizedError("Invalid API key")
        assert error.is_expected is False
        assert error.should_alert is True

    def test_critical_severity_errors_are_unexpected(self) -> None:
        """Critical severity errors should be marked as unexpected."""
        error = TributumError(
            error_code="CRITICAL_ERROR",
            message="System failure",
            severity=Severity.CRITICAL,
        )
        assert error.is_expected is False
        assert error.should_alert is True

    def test_custom_severity_overrides_default(self) -> None:
        """Custom severity should override default classification."""
        # ValidationError normally has LOW severity, but we override it
        error = ValidationError(
            message="Critical validation failure",
            context={"critical": True},
        )
        # Manually set severity after creation (since constructor doesn't take it)
        error.severity = Severity.HIGH
        assert error.is_expected is False
        assert error.should_alert is True


@pytest.mark.unit
class TestAlertingBehavior:
    """Test should_alert property for different error types."""

    def test_not_found_error_should_not_alert(self) -> None:
        """NotFoundError should not trigger alerts."""
        error = NotFoundError("User not found")
        assert error.severity == Severity.LOW
        assert error.should_alert is False

    def test_validation_error_should_not_alert(self) -> None:
        """ValidationError should not trigger alerts."""
        error = ValidationError("Invalid input")
        assert error.severity == Severity.LOW
        assert error.should_alert is False

    def test_business_rule_error_should_not_alert(self) -> None:
        """BusinessRuleError should not trigger alerts."""
        error = BusinessRuleError("Operation not allowed")
        assert error.severity == Severity.MEDIUM
        assert error.should_alert is False

    def test_unauthorized_error_should_alert(self) -> None:
        """UnauthorizedError should trigger alerts."""
        error = UnauthorizedError("Authentication failed")
        assert error.severity == Severity.HIGH
        assert error.should_alert is True

    def test_explicit_critical_error_should_alert(self) -> None:
        """Explicitly critical errors should trigger alerts."""
        error = TributumError(
            error_code="SYSTEM_FAILURE",
            message="Database connection lost",
            severity=Severity.CRITICAL,
        )
        assert error.should_alert is True


@pytest.mark.unit
class TestPropertyConsistency:
    """Test that is_expected and should_alert are consistent."""

    @pytest.mark.parametrize(
        ("severity", "expected_is_expected", "expected_should_alert"),
        [
            (Severity.LOW, True, False),
            (Severity.MEDIUM, True, False),
            (Severity.HIGH, False, True),
            (Severity.CRITICAL, False, True),
        ],
    )
    def test_severity_property_consistency(
        self,
        severity: Severity,
        expected_is_expected: bool,
        expected_should_alert: bool,
    ) -> None:
        """Properties should be consistent with severity levels."""
        error = TributumError(
            error_code="TEST_ERROR",
            message="Test message",
            severity=severity,
        )
        assert error.is_expected == expected_is_expected
        assert error.should_alert == expected_should_alert

    def test_properties_are_inverse(self) -> None:
        """is_expected and should_alert should generally be inverses."""
        # Test all default error types
        errors = [
            ValidationError("test"),
            NotFoundError("test"),
            BusinessRuleError("test"),
            UnauthorizedError("test"),
        ]

        for error in errors:
            # For our current implementation, these should be inverses
            # (expected errors don't alert, unexpected errors do alert)
            if error.is_expected:
                assert not error.should_alert
            else:
                assert error.should_alert
