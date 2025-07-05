"""Tests for GCP formatter enhancements."""

import json
from datetime import UTC, datetime

import pytest
from pytest_mock import MockerFixture

from src.core.logging import serialize_for_gcp


@pytest.mark.unit
class TestGCPFormatterServiceContext:
    """Test that GCP formatter includes serviceContext."""

    def test_service_context_included(self, mocker: MockerFixture) -> None:
        """Service context should be included in all logs."""
        # Configure mock settings
        mock_settings = mocker.patch("src.core.config.get_settings")
        mock_settings.return_value.app_name = "Tributum"
        mock_settings.return_value.app_version = "0.3.0"

        # Create mock record
        mock_record = {
            "time": datetime.now(UTC),
            "level": mocker.Mock(name="INFO"),
            "message": "Test message",
            "name": "test_module",
            "function": "test_function",
            "module": "test",
            "line": 42,
            "file": mocker.Mock(path="/app/src/test.py"),
            "extra": {},
            "exception": None,
        }

        # Format the record
        output = serialize_for_gcp(mock_record)
        log_entry = json.loads(output.strip())

        # Verify service context
        assert "serviceContext" in log_entry
        assert log_entry["serviceContext"]["service"] == "Tributum"
        assert log_entry["serviceContext"]["version"] == "0.3.0"


@pytest.mark.unit
class TestGCPFormatterErrorFingerprint:
    """Test that error fingerprints are added to labels."""

    def test_error_fingerprint_in_labels(self, mocker: MockerFixture) -> None:
        """Error fingerprint should be truncated and added to labels."""
        # Configure mock settings
        mock_settings = mocker.patch("src.core.config.get_settings")
        mock_settings.return_value.app_name = "Tributum"
        mock_settings.return_value.app_version = "1.2.3"

        # Create mock record
        mock_record = {
            "time": datetime.now(UTC),
            "level": mocker.Mock(name="INFO"),
            "message": "Test message",
            "name": "test_module",
            "function": "test_function",
            "module": "test",
            "line": 42,
            "file": mocker.Mock(path="/app/src/test.py"),
            "extra": {"fingerprint": "abcdef1234567890"},
            "exception": None,
        }

        output = serialize_for_gcp(mock_record)
        log_entry = json.loads(output.strip())

        # Check labels
        labels = log_entry.get("logging.googleapis.com/labels", {})
        assert "error_fingerprint" in labels
        assert labels["error_fingerprint"] == "abcdef12"  # First 8 chars

    def test_no_fingerprint_no_label(self, mocker: MockerFixture) -> None:
        """No error_fingerprint label should be added if no fingerprint."""
        # Configure mock settings
        mock_settings = mocker.patch("src.core.config.get_settings")
        mock_settings.return_value.app_name = "Tributum"
        mock_settings.return_value.app_version = "1.2.3"

        # Create mock record without fingerprint
        mock_record = {
            "time": datetime.now(UTC),
            "level": mocker.Mock(name="INFO"),
            "message": "Test message",
            "name": "test_module",
            "function": "test_function",
            "module": "test",
            "line": 42,
            "file": mocker.Mock(path="/app/src/test.py"),
            "extra": {},
            "exception": None,
        }

        output = serialize_for_gcp(mock_record)
        log_entry = json.loads(output.strip())

        labels = log_entry.get("logging.googleapis.com/labels", {})
        assert "error_fingerprint" not in labels


@pytest.mark.unit
class TestGCPFormatterErrorReporting:
    """Test Error Reporting specific fields."""

    def test_error_reporting_fields_for_errors(self, mocker: MockerFixture) -> None:
        """Error logs should include Error Reporting fields."""
        # Configure mock settings
        mock_settings = mocker.patch("src.core.config.get_settings")
        mock_settings.return_value.app_name = "Tributum"
        mock_settings.return_value.app_version = "1.2.3"

        # Create mock record with error level
        mock_level = mocker.Mock()
        mock_level.name = "ERROR"

        mock_record = {
            "time": datetime.now(UTC),
            "level": mock_level,
            "message": "Test message",
            "name": "test_module",
            "function": "test_function",
            "module": "test",
            "line": 42,
            "file": mocker.Mock(path="/app/src/test.py"),
            "extra": {"stack_trace": ["frame1", "frame2"]},
            "exception": None,
        }

        output = serialize_for_gcp(mock_record)
        log_entry = json.loads(output.strip())

        # Check Error Reporting fields
        expected_type = (
            "type.googleapis.com/google.devtools.clouderrorreporting.v1beta1."
            "ReportedErrorEvent"
        )
        assert log_entry["@type"] == expected_type
        assert "context" in log_entry
        assert "reportLocation" in log_entry["context"]
        assert log_entry["context"]["reportLocation"]["filePath"] == "/app/src/test.py"
        assert log_entry["context"]["reportLocation"]["lineNumber"] == 42
        assert log_entry["context"]["reportLocation"]["functionName"] == "test_function"
        assert log_entry["stack_trace"] == ["frame1", "frame2"]

    def test_error_reporting_fields_for_critical(self, mocker: MockerFixture) -> None:
        """Critical logs should also include Error Reporting fields."""
        # Configure mock settings
        mock_settings = mocker.patch("src.core.config.get_settings")
        mock_settings.return_value.app_name = "Tributum"
        mock_settings.return_value.app_version = "1.2.3"

        # Create mock record with critical level
        mock_level = mocker.Mock()
        mock_level.name = "CRITICAL"

        mock_record = {
            "time": datetime.now(UTC),
            "level": mock_level,
            "message": "Test message",
            "name": "test_module",
            "function": "test_function",
            "module": "test",
            "line": 42,
            "file": mocker.Mock(path="/app/src/test.py"),
            "extra": {},
            "exception": None,
        }

        output = serialize_for_gcp(mock_record)
        log_entry = json.loads(output.strip())

        expected_type = (
            "type.googleapis.com/google.devtools.clouderrorreporting.v1beta1."
            "ReportedErrorEvent"
        )
        assert log_entry["@type"] == expected_type
        assert "logging.googleapis.com/sourceLocation" in log_entry

    def test_no_error_reporting_for_info(self, mocker: MockerFixture) -> None:
        """Info logs should not include Error Reporting fields."""
        # Configure mock settings
        mock_settings = mocker.patch("src.core.config.get_settings")
        mock_settings.return_value.app_name = "Tributum"
        mock_settings.return_value.app_version = "1.2.3"

        # Create mock record with INFO level
        mock_record = {
            "time": datetime.now(UTC),
            "level": mocker.Mock(name="INFO"),
            "message": "Test message",
            "name": "test_module",
            "function": "test_function",
            "module": "test",
            "line": 42,
            "file": mocker.Mock(path="/app/src/test.py"),
            "extra": {},
            "exception": None,
        }

        output = serialize_for_gcp(mock_record)
        log_entry = json.loads(output.strip())

        assert "@type" not in log_entry
        assert "context" not in log_entry

    def test_exception_logs_get_error_reporting(self, mocker: MockerFixture) -> None:
        """Logs with exceptions should get Error Reporting fields."""
        # Configure mock settings
        mock_settings = mocker.patch("src.core.config.get_settings")
        mock_settings.return_value.app_name = "Tributum"
        mock_settings.return_value.app_version = "1.2.3"

        # Create mock record with exception
        mock_record = {
            "time": datetime.now(UTC),
            "level": mocker.Mock(name="INFO"),
            "message": "Test message",
            "name": "test_module",
            "function": "test_function",
            "module": "test",
            "line": 42,
            "file": mocker.Mock(path="/app/src/test.py"),
            "extra": {},
            "exception": mocker.Mock(),
        }

        output = serialize_for_gcp(mock_record)
        log_entry = json.loads(output.strip())

        expected_type = (
            "type.googleapis.com/google.devtools.clouderrorreporting.v1beta1."
            "ReportedErrorEvent"
        )
        assert log_entry["@type"] == expected_type
        assert "logging.googleapis.com/sourceLocation" in log_entry


@pytest.mark.unit
class TestGCPFormatterBasicFields:
    """Test basic GCP formatter functionality remains intact."""

    def test_correlation_id_as_trace(self, mocker: MockerFixture) -> None:
        """Correlation ID should be mapped to trace field."""
        # Configure mock settings
        mock_settings = mocker.patch("src.core.config.get_settings")
        mock_settings.return_value.app_name = "Tributum"
        mock_settings.return_value.app_version = "1.2.3"

        # Create mock record with correlation_id
        mock_record = {
            "time": datetime.now(UTC),
            "level": mocker.Mock(name="INFO"),
            "message": "Test message",
            "name": "test_module",
            "function": "test_function",
            "module": "test",
            "line": 42,
            "file": mocker.Mock(path="/app/src/test.py"),
            "extra": {"correlation_id": "trace-123"},
            "exception": None,
        }

        output = serialize_for_gcp(mock_record)
        log_entry = json.loads(output.strip())

        assert log_entry["logging.googleapis.com/trace"] == "trace-123"

    def test_severity_mapping(self, mocker: MockerFixture) -> None:
        """Test severity level mapping."""
        # Configure mock settings
        mock_settings = mocker.patch("src.core.config.get_settings")
        mock_settings.return_value.app_name = "Tributum"
        mock_settings.return_value.app_version = "1.2.3"

        severity_map = {
            "DEBUG": "DEBUG",
            "INFO": "INFO",
            "WARNING": "WARNING",
            "ERROR": "ERROR",
            "CRITICAL": "CRITICAL",
        }

        for loguru_level, gcp_severity in severity_map.items():
            # Create mock level for each severity
            mock_level = mocker.Mock()
            mock_level.name = loguru_level

            mock_record = {
                "time": datetime.now(UTC),
                "level": mock_level,
                "message": "Test message",
                "name": "test_module",
                "function": "test_function",
                "module": "test",
                "line": 42,
                "file": mocker.Mock(path="/app/src/test.py"),
                "extra": {},
                "exception": None,
            }

            output = serialize_for_gcp(mock_record)
            log_entry = json.loads(output.strip())
            assert log_entry["severity"] == gcp_severity
