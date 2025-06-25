"""Unit tests for logging processors."""

import os
import sys

import pytest
from pytest_mock import MockerFixture

from src.core.context import RequestContext
from src.core.logging import (
    _environment_cache,
    add_log_level_upper,
    bind_logger_context,
    clear_logger_context,
    environment_processor,
    error_context_processor,
    inject_correlation_id,
    inject_logger_context,
    performance_processor,
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


@pytest.mark.unit
class TestPerformanceProcessor:
    """Test the performance_processor function."""

    def test_adds_process_and_thread_info(self, mocker: MockerFixture) -> None:
        """Test that process ID and thread ID are always added."""
        logger = mocker.MagicMock()
        event_dict: dict[str, object] = {}

        # Mock os.getpid and threading.get_ident
        mocker.patch("os.getpid", return_value=12345)
        mocker.patch("threading.get_ident", return_value=67890)

        # Also mock psutil to prevent it from trying to use the fake PID
        mocker.patch("psutil.Process", side_effect=OSError("Mocked"))

        result = performance_processor(logger, "info", event_dict)

        assert result["process_id"] == 12345
        assert result["thread_id"] == "67890"

    def test_adds_memory_when_psutil_available(self, mocker: MockerFixture) -> None:
        """Test that memory usage is added when psutil is available."""
        logger = mocker.MagicMock()
        event_dict: dict[str, object] = {}

        # Mock psutil.Process
        mock_memory_info = mocker.MagicMock()
        mock_memory_info.rss = 104857600  # 100 MB in bytes
        mock_process = mocker.MagicMock()
        mock_process.memory_info.return_value = mock_memory_info

        mocker.patch("psutil.Process", return_value=mock_process)

        result = performance_processor(logger, "info", event_dict)

        assert result["memory_mb"] == 100.0

    def test_handles_psutil_error_gracefully(self, mocker: MockerFixture) -> None:
        """Test that psutil errors are handled gracefully."""
        logger = mocker.MagicMock()
        event_dict: dict[str, object] = {}

        # Make psutil.Process raise an error
        mocker.patch("psutil.Process", side_effect=OSError("Process error"))

        result = performance_processor(logger, "info", event_dict)

        assert "memory_mb" not in result
        # Should still have process/thread info
        assert "process_id" in result
        assert "thread_id" in result

    def test_adds_active_tasks_in_async_context(self, mocker: MockerFixture) -> None:
        """Test that active task count is added in async context."""
        logger = mocker.MagicMock()
        event_dict: dict[str, object] = {}

        # Mock asyncio context
        mock_loop = mocker.MagicMock()
        mock_tasks = [mocker.MagicMock(), mocker.MagicMock(), mocker.MagicMock()]
        mocker.patch("asyncio.get_running_loop", return_value=mock_loop)
        mocker.patch("asyncio.all_tasks", return_value=mock_tasks)

        result = performance_processor(logger, "info", event_dict)

        assert result["active_tasks"] == 3

    def test_handles_no_async_context_gracefully(self, mocker: MockerFixture) -> None:
        """Test that missing async context is handled gracefully."""
        logger = mocker.MagicMock()
        event_dict: dict[str, object] = {}

        # Make asyncio calls fail
        mocker.patch(
            "asyncio.get_running_loop", side_effect=RuntimeError("No running loop")
        )

        result = performance_processor(logger, "info", event_dict)

        assert "active_tasks" not in result
        # Should still have process/thread info
        assert "process_id" in result
        assert "thread_id" in result


@pytest.mark.unit
class TestEnvironmentProcessor:
    """Test the environment_processor function."""

    def setup_method(self) -> None:
        """Clear the environment cache before each test."""
        _environment_cache.clear()

    def test_adds_hostname(self, mocker: MockerFixture) -> None:
        """Test that hostname is added and cached."""
        logger = mocker.MagicMock()
        event_dict: dict[str, object] = {}

        # Mock socket.gethostname
        mocker.patch("socket.gethostname", return_value="test-host")

        result = environment_processor(logger, "info", event_dict)

        assert result["hostname"] == "test-host"
        # Check it was cached
        assert _environment_cache["hostname"] == "test-host"

    def test_handles_hostname_error_gracefully(self, mocker: MockerFixture) -> None:
        """Test that hostname errors are handled gracefully."""
        logger = mocker.MagicMock()
        event_dict: dict[str, object] = {}

        # Make gethostname fail
        mocker.patch("socket.gethostname", side_effect=OSError("Network error"))

        result = environment_processor(logger, "info", event_dict)

        assert result["hostname"] == "unknown"

    def test_extracts_docker_container_id(self, mocker: MockerFixture) -> None:
        """Test that Docker container ID is extracted from cgroup."""
        logger = mocker.MagicMock()
        event_dict: dict[str, object] = {}

        # Mock cgroup file with Docker container
        cgroup_content = (
            "12:cpuset:/docker/1234567890abcdef1234567890abcdef"
            "1234567890abcdef1234567890abcdef\n"
            "11:cpu,cpuacct:/docker/1234567890abcdef1234567890abcdef"
            "1234567890abcdef1234567890abcdef\n"
        )
        mocker.patch("pathlib.Path.open", mocker.mock_open(read_data=cgroup_content))

        result = environment_processor(logger, "info", event_dict)

        assert result["container_id"] == "1234567890ab"

    def test_extracts_containerd_container_id(self, mocker: MockerFixture) -> None:
        """Test that containerd container ID is extracted from cgroup."""
        logger = mocker.MagicMock()
        event_dict: dict[str, object] = {}

        # Mock cgroup file with containerd container
        cgroup_content = """12:cpuset:/containerd/abcdef123456abcdef123456abcdef123456
11:cpu,cpuacct:/containerd/abcdef123456abcdef123456abcdef123456
"""
        mocker.patch("pathlib.Path.open", mocker.mock_open(read_data=cgroup_content))

        result = environment_processor(logger, "info", event_dict)

        assert result["container_id"] == "abcdef123456"

    def test_no_container_id_when_not_in_container(self, mocker: MockerFixture) -> None:
        """Test that no container ID is added when not in a container."""
        logger = mocker.MagicMock()
        event_dict: dict[str, object] = {}

        # Mock cgroup file without container info
        cgroup_content = """12:cpuset:/
11:cpu,cpuacct:/user.slice
"""
        mocker.patch("pathlib.Path.open", mocker.mock_open(read_data=cgroup_content))

        result = environment_processor(logger, "info", event_dict)

        assert "container_id" not in result

    def test_handles_missing_cgroup_file(self, mocker: MockerFixture) -> None:
        """Test that missing cgroup file is handled gracefully."""
        logger = mocker.MagicMock()
        event_dict: dict[str, object] = {}

        # Make file open fail
        mocker.patch("pathlib.Path.open", side_effect=OSError("File not found"))

        result = environment_processor(logger, "info", event_dict)

        assert "container_id" not in result
        # Should still have hostname
        assert "hostname" in result

    def test_adds_kubernetes_info_from_env(self, mocker: MockerFixture) -> None:
        """Test that Kubernetes information is added from environment."""
        logger = mocker.MagicMock()
        event_dict: dict[str, object] = {}

        # Set K8s environment variables
        mocker.patch.dict(
            os.environ,
            {"K8S_POD_NAME": "my-app-pod-abc123", "K8S_NAMESPACE": "production"},
        )

        result = environment_processor(logger, "info", event_dict)

        assert result["k8s_pod"] == "my-app-pod-abc123"
        assert result["k8s_namespace"] == "production"

    def test_no_kubernetes_info_when_not_in_k8s(self, mocker: MockerFixture) -> None:
        """Test that no K8s info is added when not in Kubernetes."""
        logger = mocker.MagicMock()
        event_dict: dict[str, object] = {}

        # Ensure K8s env vars are not set
        mocker.patch.dict(os.environ, {}, clear=True)

        result = environment_processor(logger, "info", event_dict)

        assert "k8s_pod" not in result
        assert "k8s_namespace" not in result

    def test_uses_cached_values_on_subsequent_calls(
        self, mocker: MockerFixture
    ) -> None:
        """Test that cached values are used on subsequent calls."""
        logger = mocker.MagicMock()

        # Mock all external calls
        mock_gethostname = mocker.patch("socket.gethostname", return_value="test-host")
        # Need to mock Path.open() instead of builtins.open
        mock_path_open = mocker.patch(
            "pathlib.Path.open", mocker.mock_open(read_data="")
        )
        mocker.patch.dict(os.environ, {"K8S_POD_NAME": "test-pod"})

        # First call
        result1 = environment_processor(logger, "info", {})

        # Second call
        result2 = environment_processor(logger, "info", {})

        # Both results should be the same
        assert result1 == result2

        # External calls should only happen once
        mock_gethostname.assert_called_once()
        mock_path_open.assert_called_once()


@pytest.mark.unit
class TestErrorContextProcessor:
    """Test the error_context_processor function."""

    def test_no_processing_without_exc_info(self, mocker: MockerFixture) -> None:
        """Test that processor does nothing without exc_info."""
        logger = mocker.MagicMock()
        event_dict: dict[str, object] = {"message": "test"}

        result = error_context_processor(logger, "error", event_dict)

        assert result == event_dict
        assert "exception_module" not in result
        assert "exception_fingerprint" not in result

    def test_processes_exception_tuple(self, mocker: MockerFixture) -> None:
        """Test processing of exc_info tuple."""
        logger = mocker.MagicMock()

        # Create a real exception with traceback
        try:
            raise ValueError("Test error")
        except ValueError:
            exc_info = sys.exc_info()

        event_dict: dict[str, object] = {"exc_info": exc_info}

        result = error_context_processor(logger, "error", event_dict)

        assert result["exception_module"] == "builtins"
        assert "exception_fingerprint" in result
        # Fingerprint should be 8 chars
        assert len(result["exception_fingerprint"]) == 8

    def test_processes_exception_object(self, mocker: MockerFixture) -> None:
        """Test processing of direct exception object."""
        logger = mocker.MagicMock()

        # Create exception with traceback
        try:
            raise RuntimeError("Direct error")
        except RuntimeError as e:
            exception = e

        event_dict: dict[str, object] = {"exc_info": exception}

        result = error_context_processor(logger, "error", event_dict)

        assert result["exception_module"] == "builtins"
        assert "exception_fingerprint" in result

    def test_processes_exc_info_true(self, mocker: MockerFixture) -> None:
        """Test processing when exc_info=True."""
        logger = mocker.MagicMock()

        # Set up current exception
        try:
            raise KeyError("Current exception")
        except KeyError:
            # Mock sys.exc_info to return our exception
            exc_info = sys.exc_info()
            mocker.patch("sys.exc_info", return_value=exc_info)

            event_dict: dict[str, object] = {"exc_info": True}
            result = error_context_processor(logger, "error", event_dict)

        assert result["exception_module"] == "builtins"
        assert "exception_fingerprint" in result

    def test_fingerprint_includes_traceback_info(self, mocker: MockerFixture) -> None:
        """Test that fingerprint includes traceback information."""
        logger = mocker.MagicMock()

        # Create exception with specific traceback
        def inner_function() -> None:
            raise TypeError("Specific error")

        def outer_function() -> None:
            inner_function()

        exc_info = None
        try:
            outer_function()
        except TypeError:
            exc_info = sys.exc_info()

        assert exc_info is not None
        event_dict: dict[str, object] = {"exc_info": exc_info}

        # Mock Path.name to ensure consistent filenames
        mocker.patch(
            "pathlib.Path.name",
            new_callable=mocker.PropertyMock,
            return_value="test_file.py",
        )

        result = error_context_processor(logger, "error", event_dict)

        # Fingerprint should be deterministic for same exception
        fingerprint1 = result["exception_fingerprint"]

        # Process again
        result2 = error_context_processor(logger, "error", event_dict)
        fingerprint2 = result2["exception_fingerprint"]

        assert fingerprint1 == fingerprint2

    def test_sanitizes_error_context(self, mocker: MockerFixture) -> None:
        """Test that error_context is sanitized."""
        logger = mocker.MagicMock()

        try:
            raise ValueError("Test")
        except ValueError:
            exc_info = sys.exc_info()

        event_dict: dict[str, object] = {
            "exc_info": exc_info,
            "error_context": {
                "user_id": "123",
                "password": "secret123",
                "api_key": "key-abc",
            },
        }

        # Mock sanitize_context to verify it's called
        mock_sanitize = mocker.patch(
            "src.core.logging.sanitize_context",
            return_value={
                "user_id": "123",
                "password": "[REDACTED]",
                "api_key": "[REDACTED]",
            },
        )

        result = error_context_processor(logger, "error", event_dict)

        # Verify sanitize_context was called with the original values
        mock_sanitize.assert_called_once_with(
            {"user_id": "123", "password": "secret123", "api_key": "key-abc"}
        )
        # The result should have the sanitized values
        assert result["error_context"]["password"] == "[REDACTED]"
        assert result["error_context"]["api_key"] == "[REDACTED]"
        assert result["error_context"]["user_id"] == "123"

    def test_handles_missing_traceback(self, mocker: MockerFixture) -> None:
        """Test handling of exception without traceback."""
        logger = mocker.MagicMock()

        # Create exception without traceback
        exc_type = ValueError
        exc_value = ValueError("No traceback")
        exc_traceback = None

        event_dict: dict[str, object] = {
            "exc_info": (exc_type, exc_value, exc_traceback)
        }

        result = error_context_processor(logger, "error", event_dict)

        assert result["exception_module"] == "builtins"
        assert "exception_fingerprint" in result
        # Fingerprint should still be generated
        assert len(result["exception_fingerprint"]) == 8

    def test_handles_invalid_exc_info_format(self, mocker: MockerFixture) -> None:
        """Test handling of invalid exc_info format."""
        logger = mocker.MagicMock()

        # Test with invalid exc_info format (not tuple, bool, or BaseException)
        event_dict: dict[str, object] = {"exc_info": "invalid"}

        result = error_context_processor(logger, "error", event_dict)

        # Should return unchanged event_dict
        assert result == event_dict
        assert "exception_module" not in result
        assert "exception_fingerprint" not in result
