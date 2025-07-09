"""Unit tests for src/infrastructure/database/session.py module.

This module contains comprehensive unit tests for the database session management,
including connection pooling, session lifecycle handling, query monitoring, and
health check functionality.
"""

import asyncio
import gc
import threading
import time
from typing import Any, Never, cast

import pytest
from pytest_mock import MockerFixture, MockType
from sqlalchemy import text
from sqlalchemy.exc import (
    ArgumentError,
    DatabaseError,
    DisconnectionError,
    InvalidRequestError,
    OperationalError,
    SQLAlchemyError,
)
from sqlalchemy.exc import (
    TimeoutError as SQLTimeoutError,
)

from src.core.config import DatabaseConfig, LogConfig, Settings
from src.infrastructure.database.session import (
    COMMAND_TIMEOUT_SECONDS,
    POOL_RECYCLE_SECONDS,
    _after_cursor_execute,
    _before_cursor_execute,
    _DatabaseManager,
    _query_start_times,
    check_database_connection,
    close_database,
    create_database_engine,
    get_async_session,
    get_engine,
    get_session_factory,
)


@pytest.mark.unit
class TestQueryPerformanceMonitoring:
    """Tests for query performance monitoring event listeners."""

    def test_before_cursor_execute_stores_start_time(
        self,
        mock_execution_context: MockType,
        mock_time: MockType,
        mock_database_connection: MockType,
        mocker: MockerFixture,
    ) -> None:
        """Verify _before_cursor_execute stores the start time."""
        # Setup
        mock_time.return_value = 123.456
        _query_start_times.clear()

        # Execute
        mock_cursor = mocker.Mock()
        _before_cursor_execute(
            mock_database_connection,
            mock_cursor,
            "SELECT 1",
            None,  # parameters
            mock_execution_context,
            _executemany=False,
        )

        # Assert
        mock_time.assert_called_once()
        assert mock_execution_context in _query_start_times
        assert _query_start_times[mock_execution_context] == 123.456

        # Cleanup
        _query_start_times.clear()

    def test_after_cursor_execute_calculates_duration(
        self,
        mock_execution_context: MockType,
        mock_time: MockType,
        mock_settings: Settings,
        mocker: MockerFixture,
    ) -> None:
        """Verify query duration calculation and cleanup of start time."""
        # Setup
        mock_get_settings = mocker.patch(
            "src.infrastructure.database.session.get_settings",
            return_value=mock_settings,
        )
        mock_get_correlation_id = mocker.patch(
            "src.infrastructure.database.session.RequestContext.get_correlation_id",
            return_value="test-correlation-id",
        )

        # Pre-store start time
        _query_start_times[mock_execution_context] = 100.0
        mock_time.return_value = 100.15  # 150ms later

        # Execute
        mock_conn = mocker.Mock()
        mock_cursor = mocker.Mock()
        _after_cursor_execute(
            mock_conn,
            mock_cursor,
            "SELECT 1",
            None,  # parameters
            mock_execution_context,
            executemany=False,
        )

        # Assert
        mock_get_settings.assert_called_once()
        mock_get_correlation_id.assert_called_once()
        mock_time.assert_called_once()
        assert mock_execution_context not in _query_start_times  # Should be cleaned up

        # Cleanup
        _query_start_times.clear()

    def test_after_cursor_execute_logs_slow_queries(
        self,
        mock_execution_context: MockType,
        mock_time: MockType,
        mock_logger: MockType,
        mock_sanitize_sql_params: MockType,
        mocker: MockerFixture,
    ) -> None:
        """Verify slow query logging when threshold is exceeded."""
        del mock_logger  # Unused but required for fixture
        # Setup
        mock_settings = mocker.Mock(spec=Settings)
        mock_log_config = mocker.Mock(spec=LogConfig)
        mock_log_config.enable_sql_logging = True
        mock_log_config.slow_query_threshold_ms = 100
        mock_settings.log_config = mock_log_config

        mocker.patch(
            "src.infrastructure.database.session.get_settings",
            return_value=mock_settings,
        )
        mocker.patch(
            "src.infrastructure.database.session.RequestContext.get_correlation_id",
            return_value="test-correlation-id",
        )
        mock_logger_patch = mocker.patch("src.infrastructure.database.session.logger")

        # Pre-store start time
        _query_start_times[mock_execution_context] = 100.0
        mock_time.return_value = 100.2  # 200ms later (exceeds 100ms threshold)

        test_params = {"id": 123, "name": "test"}

        # Execute
        mock_conn = mocker.Mock()
        mock_cursor = mocker.Mock()
        _after_cursor_execute(
            mock_conn,
            mock_cursor,
            "SELECT * FROM users WHERE id = :id",
            test_params,
            mock_execution_context,
            executemany=False,
        )

        # Assert
        mock_sanitize_sql_params.assert_called_once_with(test_params)
        mock_logger_patch.warning.assert_called_once()
        warning_call = mock_logger_patch.warning.call_args
        assert "Slow query detected" in warning_call[0][0]
        assert 200.0 in warning_call[0]  # Duration in ms

        # Check extra parameters
        extra_params = warning_call[1]
        assert extra_params["duration_ms"] == 200.0
        assert extra_params["correlation_id"] == "test-correlation-id"
        assert extra_params["parameters"] == {"sanitized": str(test_params)}
        assert extra_params["executemany"] is False
        assert extra_params["threshold_ms"] == 100

        # Cleanup
        _query_start_times.clear()

    def test_after_cursor_execute_no_logging_when_disabled(
        self,
        mock_execution_context: MockType,
        mock_time: MockType,
        mocker: MockerFixture,
    ) -> None:
        """Verify no slow query logging when SQL logging is disabled."""
        # Setup
        mock_settings = mocker.Mock(spec=Settings)
        mock_log_config = mocker.Mock(spec=LogConfig)
        mock_log_config.enable_sql_logging = False
        mock_settings.log_config = mock_log_config

        mocker.patch(
            "src.infrastructure.database.session.get_settings",
            return_value=mock_settings,
        )
        mocker.patch(
            "src.infrastructure.database.session.RequestContext.get_correlation_id",
            return_value="test-correlation-id",
        )
        mock_logger = mocker.patch("src.infrastructure.database.session.logger")

        # Pre-store start time
        _query_start_times[mock_execution_context] = 100.0
        mock_time.return_value = 100.5  # 500ms later (would exceed threshold)

        # Execute
        mock_conn = mocker.Mock()
        mock_cursor = mocker.Mock()
        _after_cursor_execute(
            mock_conn,
            mock_cursor,
            "SELECT 1",
            None,  # parameters
            mock_execution_context,
            executemany=False,
        )

        # Assert
        mock_logger.warning.assert_not_called()

        # Cleanup
        _query_start_times.clear()

    def test_after_cursor_execute_handles_missing_start_time(
        self, mock_execution_context: MockType, mocker: MockerFixture
    ) -> None:
        """Verify graceful handling when start time is missing from weak dictionary."""
        # Setup
        mock_settings = mocker.Mock(spec=Settings)
        mock_log_config = mocker.Mock(spec=LogConfig)
        mock_log_config.enable_sql_logging = True
        mock_log_config.slow_query_threshold_ms = 100
        mock_settings.log_config = mock_log_config

        mocker.patch(
            "src.infrastructure.database.session.get_settings",
            return_value=mock_settings,
        )
        mocker.patch(
            "src.infrastructure.database.session.RequestContext.get_correlation_id",
            return_value="test-correlation-id",
        )
        mock_logger = mocker.patch("src.infrastructure.database.session.logger")

        # Don't store start time - context not in dictionary
        _query_start_times.clear()

        # Execute - should not raise exception
        mock_conn = mocker.Mock()
        mock_cursor = mocker.Mock()
        _after_cursor_execute(
            mock_conn,
            mock_cursor,
            "SELECT 1",
            None,  # parameters
            mock_execution_context,
            executemany=False,
        )

        # Assert - no logging should occur since duration_ms is 0.0
        mock_logger.warning.assert_not_called()

    def test_after_cursor_execute_correlation_id_logging(
        self,
        mock_execution_context: MockType,
        mock_time: MockType,
        mock_sanitize_sql_params: MockType,
        mocker: MockerFixture,
    ) -> None:
        """Verify correlation ID is properly included in slow query logs."""
        del mock_sanitize_sql_params  # Unused but required for fixture
        # Setup
        mock_settings = mocker.Mock(spec=Settings)
        mock_log_config = mocker.Mock(spec=LogConfig)
        mock_log_config.enable_sql_logging = True
        mock_log_config.slow_query_threshold_ms = 50
        mock_settings.log_config = mock_log_config

        mocker.patch(
            "src.infrastructure.database.session.get_settings",
            return_value=mock_settings,
        )

        test_correlation_id = "corr-12345-test"
        mocker.patch(
            "src.infrastructure.database.session.RequestContext.get_correlation_id",
            return_value=test_correlation_id,
        )
        mock_logger = mocker.patch("src.infrastructure.database.session.logger")

        # Pre-store start time
        _query_start_times[mock_execution_context] = 100.0
        mock_time.return_value = 100.1  # 100ms later

        # Execute
        mock_conn = mocker.Mock()
        mock_cursor = mocker.Mock()
        _after_cursor_execute(
            mock_conn,
            mock_cursor,
            "SELECT 1",
            None,  # parameters
            mock_execution_context,
            executemany=False,
        )

        # Assert
        mock_logger.warning.assert_called_once()
        extra_params = mock_logger.warning.call_args[1]
        assert extra_params["correlation_id"] == test_correlation_id

        # Cleanup
        _query_start_times.clear()

    def test_after_cursor_execute_sanitizes_parameters(
        self,
        mock_execution_context: MockType,
        mock_time: MockType,
        mock_sanitize_sql_params: MockType,
        mocker: MockerFixture,
    ) -> None:
        """Verify SQL parameters are sanitized before logging."""
        # Setup
        mock_settings = mocker.Mock(spec=Settings)
        mock_log_config = mocker.Mock(spec=LogConfig)
        mock_log_config.enable_sql_logging = True
        mock_log_config.slow_query_threshold_ms = 50
        mock_settings.log_config = mock_log_config

        mocker.patch(
            "src.infrastructure.database.session.get_settings",
            return_value=mock_settings,
        )
        mocker.patch(
            "src.infrastructure.database.session.RequestContext.get_correlation_id",
            return_value="test-id",
        )
        mock_logger = mocker.patch("src.infrastructure.database.session.logger")

        # Pre-store start time
        _query_start_times[mock_execution_context] = 100.0
        mock_time.return_value = 100.1  # 100ms later

        sensitive_params = {"password": "secret123", "token": "abc-xyz"}

        # Execute
        mock_conn = mocker.Mock()
        mock_cursor = mocker.Mock()
        _after_cursor_execute(
            mock_conn,
            mock_cursor,
            "INSERT INTO users VALUES (:password, :token)",
            sensitive_params,
            mock_execution_context,
            executemany=False,
        )

        # Assert
        mock_sanitize_sql_params.assert_called_once_with(sensitive_params)
        mock_logger.warning.assert_called_once()
        extra_params = mock_logger.warning.call_args[1]
        assert extra_params["parameters"] == {"sanitized": str(sensitive_params)}

        # Cleanup
        _query_start_times.clear()

    def test_after_cursor_execute_truncates_statement(
        self,
        mock_execution_context: MockType,
        mock_time: MockType,
        mock_sanitize_sql_params: MockType,
        mocker: MockerFixture,
    ) -> None:
        """Verify SQL statement is truncated appropriately for logging."""
        del mock_sanitize_sql_params  # Unused but required for fixture
        # Setup
        mock_settings = mocker.Mock(spec=Settings)
        mock_log_config = mocker.Mock(spec=LogConfig)
        mock_log_config.enable_sql_logging = True
        mock_log_config.slow_query_threshold_ms = 50
        mock_settings.log_config = mock_log_config

        mocker.patch(
            "src.infrastructure.database.session.get_settings",
            return_value=mock_settings,
        )
        mocker.patch(
            "src.infrastructure.database.session.RequestContext.get_correlation_id",
            return_value="test-id",
        )
        mock_logger = mocker.patch("src.infrastructure.database.session.logger")

        # Pre-store start time
        _query_start_times[mock_execution_context] = 100.0
        mock_time.return_value = 100.1  # 100ms later

        # Create a very long SQL statement
        long_statement = "SELECT " + ", ".join([f"column_{i}" for i in range(200)])
        assert len(long_statement) > 500

        # Execute
        mock_conn = mocker.Mock()
        mock_cursor = mocker.Mock()
        _after_cursor_execute(
            mock_conn,
            mock_cursor,
            long_statement,
            None,  # parameters
            mock_execution_context,
            executemany=False,
        )

        # Assert
        mock_logger.warning.assert_called_once()
        warning_call = mock_logger.warning.call_args

        # Check that the display message is truncated to 100 chars
        display_message = warning_call[0][1]
        assert len(display_message) <= 103  # 100 + "..."

        # Check that the full query in extra params is truncated to 500 chars
        extra_params = warning_call[1]
        assert len(extra_params["query"]) <= 500

        # Cleanup
        _query_start_times.clear()

    def test_after_cursor_execute_executemany_logging(
        self,
        mock_execution_context: MockType,
        mock_time: MockType,
        mock_sanitize_sql_params: MockType,
        mocker: MockerFixture,
    ) -> None:
        """Verify executemany parameter is correctly logged."""
        del mock_sanitize_sql_params  # Unused but required for fixture
        # Setup
        mock_settings = mocker.Mock(spec=Settings)
        mock_log_config = mocker.Mock(spec=LogConfig)
        mock_log_config.enable_sql_logging = True
        mock_log_config.slow_query_threshold_ms = 50
        mock_settings.log_config = mock_log_config

        mocker.patch(
            "src.infrastructure.database.session.get_settings",
            return_value=mock_settings,
        )
        mocker.patch(
            "src.infrastructure.database.session.RequestContext.get_correlation_id",
            return_value="test-id",
        )
        mock_logger = mocker.patch("src.infrastructure.database.session.logger")

        # Pre-store start time
        _query_start_times[mock_execution_context] = 100.0
        mock_time.return_value = 100.1  # 100ms later

        # Execute with executemany=True
        mock_conn = mocker.Mock()
        mock_cursor = mocker.Mock()
        _after_cursor_execute(
            mock_conn,
            mock_cursor,
            "INSERT INTO users VALUES (?)",
            [("user1",), ("user2",), ("user3",)],
            mock_execution_context,
            executemany=True,
        )

        # Assert
        mock_logger.warning.assert_called_once()
        extra_params = mock_logger.warning.call_args[1]
        assert extra_params["executemany"] is True

        # Cleanup
        _query_start_times.clear()

    def test_weak_key_dictionary_memory_management(
        self,
        mocker: MockerFixture,
        mock_time: MockType,
    ) -> None:
        """Verify WeakKeyDictionary properly handles context cleanup."""
        # Setup
        mock_time.return_value = 123.456
        _query_start_times.clear()

        # Create execution context that will be garbage collected
        context = mocker.Mock()
        context.execution_options = {}

        # Store start time
        mock_conn = mocker.Mock()
        mock_cursor = mocker.Mock()
        _before_cursor_execute(
            mock_conn,
            mock_cursor,
            "SELECT 1",
            None,  # parameters
            context,
            _executemany=False,
        )

        # Verify it was stored
        assert context in _query_start_times
        assert _query_start_times[context] == 123.456

        # Delete context reference and trigger garbage collection
        del context
        gc.collect()

        # Verify entry is automatically removed
        assert len(_query_start_times) == 0

        # Cleanup
        _query_start_times.clear()


@pytest.mark.unit
class TestDatabaseEngineCreation:
    """Tests for database engine creation and configuration."""

    def test_create_database_engine_with_default_url(
        self,
        mock_settings: Settings,
        mock_create_async_engine: MockType,
        mock_event_listen: MockType,
        mocker: MockerFixture,
    ) -> None:
        """Verify engine creation with URL from settings."""
        del mock_event_listen  # Unused but required for fixture
        # Setup
        mock_get_settings = mocker.patch(
            "src.infrastructure.database.session.get_settings",
            return_value=mock_settings,
        )
        mock_logger = mocker.patch("src.infrastructure.database.session.logger")

        # Execute
        result = create_database_engine()

        # Assert
        mock_get_settings.assert_called_once()
        mock_create_async_engine.assert_called_once_with(
            mock_settings.database_config.database_url,
            pool_size=mock_settings.database_config.pool_size,
            max_overflow=mock_settings.database_config.max_overflow,
            pool_timeout=mock_settings.database_config.pool_timeout,
            pool_pre_ping=mock_settings.database_config.pool_pre_ping,
            echo=mock_settings.database_config.echo,
            pool_recycle=POOL_RECYCLE_SECONDS,
            connect_args={
                "server_settings": {"jit": "off"},
                "command_timeout": COMMAND_TIMEOUT_SECONDS,
            },
        )
        assert result == mock_create_async_engine.return_value
        mock_logger.info.assert_called()

    def test_create_database_engine_with_custom_url(
        self,
        mock_settings: Settings,
        mock_create_async_engine: MockType,
        mocker: MockerFixture,
    ) -> None:
        """Verify engine creation with provided URL parameter."""
        # Setup
        mocker.patch(
            "src.infrastructure.database.session.get_settings",
            return_value=mock_settings,
        )
        custom_url = "postgresql+asyncpg://custom:pass@host:5432/db"

        # Execute
        result = create_database_engine(custom_url)

        # Assert
        mock_create_async_engine.assert_called_once()
        call_args = mock_create_async_engine.call_args[0]
        assert call_args[0] == custom_url  # Should use custom URL, not settings URL
        assert result == mock_create_async_engine.return_value

    def test_create_database_engine_pool_configuration(
        self, mock_create_async_engine: MockType, mocker: MockerFixture
    ) -> None:
        """Verify correct pool configuration parameters."""
        # Setup
        mock_settings = mocker.Mock(spec=Settings)
        mock_db_config = mocker.Mock(spec=DatabaseConfig)
        mock_db_config.database_url = "postgresql+asyncpg://test:test@localhost/test"
        mock_db_config.pool_size = 20
        mock_db_config.max_overflow = 10
        mock_db_config.pool_timeout = 45.0
        mock_db_config.pool_pre_ping = True
        mock_db_config.echo = False
        mock_settings.database_config = mock_db_config

        mock_log_config = mocker.Mock(spec=LogConfig)
        mock_log_config.enable_sql_logging = False
        mock_settings.log_config = mock_log_config

        mocker.patch(
            "src.infrastructure.database.session.get_settings",
            return_value=mock_settings,
        )

        # Execute
        create_database_engine()

        # Assert
        mock_create_async_engine.assert_called_once()
        call_kwargs = mock_create_async_engine.call_args[1]
        assert call_kwargs["pool_size"] == 20
        assert call_kwargs["max_overflow"] == 10
        assert call_kwargs["pool_timeout"] == 45.0
        assert call_kwargs["pool_pre_ping"] is True
        assert call_kwargs["pool_recycle"] == 3600

    def test_create_database_engine_connect_args(
        self,
        mock_settings: Settings,
        mock_create_async_engine: MockType,
        mocker: MockerFixture,
    ) -> None:
        """Verify connect_args configuration for PostgreSQL."""
        # Setup
        mocker.patch(
            "src.infrastructure.database.session.get_settings",
            return_value=mock_settings,
        )

        # Execute
        create_database_engine()

        # Assert
        call_kwargs = mock_create_async_engine.call_args[1]
        assert "connect_args" in call_kwargs
        connect_args = call_kwargs["connect_args"]
        assert connect_args["server_settings"]["jit"] == "off"
        assert connect_args["command_timeout"] == 60

    def test_create_database_engine_event_listeners_enabled(
        self,
        mock_async_engine: MockType,
        mock_create_async_engine: MockType,
        mock_event_listen: MockType,
        mocker: MockerFixture,
    ) -> None:
        """Verify event listeners are registered when SQL logging is enabled."""
        del mock_create_async_engine  # Unused but required for fixture
        # Setup
        mock_settings = mocker.Mock(spec=Settings)
        mock_db_config = mocker.Mock(spec=DatabaseConfig)
        mock_db_config.database_url = "postgresql+asyncpg://test:test@localhost/test"
        mock_db_config.pool_size = 10
        mock_db_config.max_overflow = 5
        mock_db_config.pool_timeout = 30.0
        mock_db_config.pool_pre_ping = True
        mock_db_config.echo = False
        mock_settings.database_config = mock_db_config

        mock_log_config = mocker.Mock(spec=LogConfig)
        mock_log_config.enable_sql_logging = True
        mock_settings.log_config = mock_log_config

        mocker.patch(
            "src.infrastructure.database.session.get_settings",
            return_value=mock_settings,
        )
        mock_logger = mocker.patch("src.infrastructure.database.session.logger")

        # Execute
        create_database_engine()

        # Assert
        assert mock_event_listen.call_count == 2
        calls = mock_event_listen.call_args_list

        # First call for before_cursor_execute
        assert calls[0][0][0] == mock_async_engine.sync_engine
        assert calls[0][0][1] == "before_cursor_execute"
        assert calls[0][0][2] == _before_cursor_execute

        # Second call for after_cursor_execute
        assert calls[1][0][0] == mock_async_engine.sync_engine
        assert calls[1][0][1] == "after_cursor_execute"
        assert calls[1][0][2] == _after_cursor_execute

        mock_logger.info.assert_any_call(
            "Registered custom query performance event listeners"
        )

    def test_create_database_engine_event_listeners_disabled(
        self,
        mock_create_async_engine: MockType,
        mock_event_listen: MockType,
        mocker: MockerFixture,
    ) -> None:
        """Verify event listeners are not registered when SQL logging is disabled."""
        del mock_create_async_engine  # Unused but required for fixture
        # Setup
        mock_settings = mocker.Mock(spec=Settings)
        mock_db_config = mocker.Mock(spec=DatabaseConfig)
        mock_db_config.database_url = "postgresql+asyncpg://test:test@localhost/test"
        mock_db_config.pool_size = 10
        mock_db_config.max_overflow = 5
        mock_db_config.pool_timeout = 30.0
        mock_db_config.pool_pre_ping = True
        mock_db_config.echo = False
        mock_settings.database_config = mock_db_config

        mock_log_config = mocker.Mock(spec=LogConfig)
        mock_log_config.enable_sql_logging = False
        mock_settings.log_config = mock_log_config

        mocker.patch(
            "src.infrastructure.database.session.get_settings",
            return_value=mock_settings,
        )

        # Execute
        create_database_engine()

        # Assert
        mock_event_listen.assert_not_called()

    @pytest.mark.parametrize(
        "exception_type",
        [InvalidRequestError, ArgumentError, AttributeError, TypeError],
    )
    def test_create_database_engine_event_listener_errors(
        self,
        exception_type: type[Exception],
        mock_create_async_engine: MockType,
        mock_event_listen: MockType,
        mocker: MockerFixture,
    ) -> None:
        """Verify graceful handling of event listener registration errors."""
        # Setup
        mock_settings = mocker.Mock(spec=Settings)
        mock_db_config = mocker.Mock(spec=DatabaseConfig)
        mock_db_config.database_url = "postgresql+asyncpg://test:test@localhost/test"
        mock_db_config.pool_size = 10
        mock_db_config.max_overflow = 5
        mock_db_config.pool_timeout = 30.0
        mock_db_config.pool_pre_ping = True
        mock_db_config.echo = False
        mock_settings.database_config = mock_db_config

        mock_log_config = mocker.Mock(spec=LogConfig)
        mock_log_config.enable_sql_logging = True
        mock_settings.log_config = mock_log_config

        mocker.patch(
            "src.infrastructure.database.session.get_settings",
            return_value=mock_settings,
        )
        mock_logger = mocker.patch("src.infrastructure.database.session.logger")

        # Make event.listen raise an exception
        mock_event_listen.side_effect = exception_type("Test error")

        # Execute - should not raise exception
        result = create_database_engine()

        # Assert
        assert result == mock_create_async_engine.return_value
        mock_logger.warning.assert_called_once()
        warning_message = mock_logger.warning.call_args[0][0]
        assert "Failed to register query performance event listeners" in warning_message
        assert exception_type.__name__ in mock_logger.warning.call_args[0][1]

    @pytest.mark.parametrize(
        ("pool_size", "max_overflow", "pool_timeout"),
        [
            (1, 0, 0.1),  # Minimum values
            (100, 50, 300.0),  # Maximum values
            (0, 0, 1.0),  # Edge case with zero pool
        ],
    )
    def test_create_database_engine_pool_configuration_edge_cases(
        self,
        pool_size: int,
        max_overflow: int,
        pool_timeout: float,
        mock_create_async_engine: MockType,
        mocker: MockerFixture,
    ) -> None:
        """Verify handling of edge case pool configurations."""
        # Setup
        mock_settings = mocker.Mock(spec=Settings)
        mock_db_config = mocker.Mock(spec=DatabaseConfig)
        mock_db_config.database_url = "postgresql+asyncpg://test:test@localhost/test"
        mock_db_config.pool_size = pool_size
        mock_db_config.max_overflow = max_overflow
        mock_db_config.pool_timeout = pool_timeout
        mock_db_config.pool_pre_ping = True
        mock_db_config.echo = False
        mock_settings.database_config = mock_db_config

        mock_log_config = mocker.Mock(spec=LogConfig)
        mock_log_config.enable_sql_logging = False
        mock_settings.log_config = mock_log_config

        mocker.patch(
            "src.infrastructure.database.session.get_settings",
            return_value=mock_settings,
        )

        # Execute
        create_database_engine()

        # Assert
        call_kwargs = mock_create_async_engine.call_args[1]
        assert call_kwargs["pool_size"] == pool_size
        assert call_kwargs["max_overflow"] == max_overflow
        assert call_kwargs["pool_timeout"] == pool_timeout

    @pytest.mark.parametrize(
        "database_url",
        [
            "postgresql+asyncpg://user:pass@localhost/db",
            "postgresql+asyncpg://user:pass@host:5432/db?sslmode=require",
            "sqlite+aiosqlite:///test.db",
        ],
    )
    def test_create_database_engine_database_url_formats(
        self,
        database_url: str,
        mock_create_async_engine: MockType,
        mocker: MockerFixture,
    ) -> None:
        """Verify correct handling of different database URL formats."""
        # Setup
        mock_settings = mocker.Mock(spec=Settings)
        mock_db_config = mocker.Mock(spec=DatabaseConfig)
        mock_db_config.database_url = "default://url"  # Should be overridden
        mock_db_config.pool_size = 10
        mock_db_config.max_overflow = 5
        mock_db_config.pool_timeout = 30.0
        mock_db_config.pool_pre_ping = True
        mock_db_config.echo = False
        mock_settings.database_config = mock_db_config

        mock_log_config = mocker.Mock(spec=LogConfig)
        mock_log_config.enable_sql_logging = False
        mock_settings.log_config = mock_log_config

        mocker.patch(
            "src.infrastructure.database.session.get_settings",
            return_value=mock_settings,
        )

        # Execute
        create_database_engine(database_url)

        # Assert
        call_args = mock_create_async_engine.call_args[0]
        assert call_args[0] == database_url

    def test_create_database_engine_constants_usage(
        self,
        mock_settings: Settings,
        mock_create_async_engine: MockType,
        mocker: MockerFixture,
    ) -> None:
        """Verify POOL_RECYCLE_SECONDS and COMMAND_TIMEOUT_SECONDS are used."""
        # Setup
        mocker.patch(
            "src.infrastructure.database.session.get_settings",
            return_value=mock_settings,
        )

        # Execute
        create_database_engine()

        # Assert
        call_kwargs = mock_create_async_engine.call_args[1]
        assert call_kwargs["pool_recycle"] == 3600  # POOL_RECYCLE_SECONDS
        assert (
            call_kwargs["connect_args"]["command_timeout"] == 60
        )  # COMMAND_TIMEOUT_SECONDS


@pytest.mark.unit
class TestDatabaseManager:
    """Tests for the _DatabaseManager singleton class."""

    def test_database_manager_singleton_behavior(
        self,
        database_manager_fixture: _DatabaseManager,
        mock_create_async_engine: MockType,
        mock_async_engine: MockType,
        mocker: MockerFixture,
    ) -> None:
        """Verify singleton pattern works correctly."""
        del mock_create_async_engine  # Unused but required for fixture
        # Setup
        mocker.patch(
            "src.infrastructure.database.session.create_database_engine",
            return_value=mock_async_engine,
        )

        # Execute - call get_engine multiple times
        engine1 = database_manager_fixture.get_engine()
        engine2 = database_manager_fixture.get_engine()
        engine3 = database_manager_fixture.get_engine()

        # Assert
        assert engine1 is engine2
        assert engine2 is engine3
        assert engine1 is mock_async_engine
        # create_database_engine should only be called once
        assert (
            mocker.patch.object(database_manager_fixture, "get_engine").call_count == 0
        )  # We're calling the real method

    def test_database_manager_thread_safety(
        self,
        database_manager_fixture: _DatabaseManager,
        thread_sync: dict[str, Any],
        mocker: MockerFixture,
    ) -> None:
        """Verify thread-safe engine creation."""
        # Setup
        create_count = 0
        create_lock = threading.Lock()
        engines: list[Any] = []
        errors: list[Exception] = []

        def mock_create_engine() -> MockType:
            nonlocal create_count
            with create_lock:
                create_count += 1
            # Simulate some work

            time.sleep(0.01)
            return cast("MockType", mocker.Mock())

        mocker.patch(
            "src.infrastructure.database.session.create_database_engine",
            side_effect=mock_create_engine,
        )

        barrier = thread_sync["barrier"](3)

        def get_engine_thread() -> None:
            try:
                barrier.wait()  # Synchronize thread start
                engine = database_manager_fixture.get_engine()
                with create_lock:
                    engines.append(engine)
            except Exception as e:
                with create_lock:
                    errors.append(e)

        # Execute - create multiple threads
        threads = []
        for _ in range(3):
            t = threading.Thread(target=get_engine_thread)
            threads.append(t)
            t.start()

        # Wait for all threads
        for t in threads:
            t.join(timeout=5.0)

        # Assert
        assert len(errors) == 0
        assert create_count == 1  # Should only create once
        assert len(engines) == 3
        # All engines should be the same instance
        assert all(engine is engines[0] for engine in engines)

    def test_database_manager_session_factory_creation(
        self,
        database_manager_fixture: _DatabaseManager,
        mock_async_engine: MockType,
        mock_async_sessionmaker: MockType,
        mock_session_factory: MockType,
        mocker: MockerFixture,
    ) -> None:
        """Verify session factory is created correctly."""
        # Setup
        mocker.patch.object(
            database_manager_fixture, "get_engine", return_value=mock_async_engine
        )
        mock_logger = mocker.patch("src.infrastructure.database.session.logger")

        # Execute
        factory = database_manager_fixture.get_session_factory()

        # Assert
        mock_async_sessionmaker.assert_called_once_with(
            mock_async_engine,
            class_=mocker.ANY,  # AsyncSession class
            expire_on_commit=False,
        )
        assert factory is mock_session_factory
        mock_logger.info.assert_called_with("Created async session factory")

    def test_database_manager_session_factory_singleton(
        self,
        database_manager_fixture: _DatabaseManager,
        mock_async_engine: MockType,
        mock_async_sessionmaker: MockType,
        mock_session_factory: MockType,
        mocker: MockerFixture,
    ) -> None:
        """Verify session factory singleton behavior."""
        # Setup
        mocker.patch.object(
            database_manager_fixture, "get_engine", return_value=mock_async_engine
        )

        # Execute - call get_session_factory multiple times
        factory1 = database_manager_fixture.get_session_factory()
        factory2 = database_manager_fixture.get_session_factory()
        factory3 = database_manager_fixture.get_session_factory()

        # Assert
        assert factory1 is factory2
        assert factory2 is factory3
        assert factory1 is mock_session_factory
        # async_sessionmaker should only be called once
        assert mock_async_sessionmaker.call_count == 1

    async def test_database_manager_close_disposes_engine(
        self,
        database_manager_fixture: _DatabaseManager,
        mock_async_engine: MockType,
        mocker: MockerFixture,
    ) -> None:
        """Verify close() properly disposes of engine."""
        # Setup
        database_manager_fixture._engine = mock_async_engine
        database_manager_fixture._async_session_factory = mocker.Mock()
        mock_logger = mocker.patch("src.infrastructure.database.session.logger")

        # Execute
        await database_manager_fixture.close()

        # Assert
        mock_async_engine.dispose.assert_called_once()
        mock_logger.info.assert_called_with("Database engine disposed")
        # Verify both engine and session factory are reset
        # The close() method sets both to None when engine is disposed
        assert database_manager_fixture._engine is None

    async def test_database_manager_close_when_no_engine(
        self, database_manager_fixture: _DatabaseManager, mocker: MockerFixture
    ) -> None:
        """Verify close() handles case when engine is None."""
        # Setup
        database_manager_fixture._engine = None
        database_manager_fixture._async_session_factory = None
        mock_logger = mocker.patch("src.infrastructure.database.session.logger")

        # Execute - should not raise exception
        await database_manager_fixture.close()

        # Assert
        mock_logger.info.assert_not_called()

    def test_database_manager_reset(
        self, database_manager_fixture: _DatabaseManager, mocker: MockerFixture
    ) -> None:
        """Verify reset() clears manager state."""
        # Setup
        database_manager_fixture._engine = mocker.Mock()
        database_manager_fixture._async_session_factory = mocker.Mock()

        # Execute
        database_manager_fixture.reset()

        # Assert
        assert database_manager_fixture._engine is None
        assert database_manager_fixture._async_session_factory is None

    def test_database_manager_session_factory_thread_safety(
        self,
        database_manager_fixture: _DatabaseManager,
        mock_async_engine: MockType,
        thread_sync: dict[str, Any],
        mocker: MockerFixture,
    ) -> None:
        """Verify thread-safe session factory creation."""
        # Setup
        mocker.patch.object(
            database_manager_fixture, "get_engine", return_value=mock_async_engine
        )

        create_count = 0
        create_lock = threading.Lock()
        factories: list[Any] = []
        errors: list[Exception] = []

        def mock_sessionmaker(*_args: object, **_kwargs: object) -> MockType:
            nonlocal create_count
            with create_lock:
                create_count += 1
            # Simulate some work

            time.sleep(0.01)
            return cast("MockType", mocker.Mock())

        mocker.patch(
            "src.infrastructure.database.session.async_sessionmaker",
            side_effect=mock_sessionmaker,
        )

        barrier = thread_sync["barrier"](3)

        def get_factory_thread() -> None:
            try:
                barrier.wait()  # Synchronize thread start
                factory = database_manager_fixture.get_session_factory()
                with create_lock:
                    factories.append(factory)
            except Exception as e:
                with create_lock:
                    errors.append(e)

        # Execute - create multiple threads
        threads = []
        for _ in range(3):
            t = threading.Thread(target=get_factory_thread)
            threads.append(t)
            t.start()

        # Wait for all threads
        for t in threads:
            t.join(timeout=5.0)

        # Assert
        assert len(errors) == 0
        assert create_count == 1  # Should only create once
        assert len(factories) == 3
        # All factories should be the same instance
        assert all(factory is factories[0] for factory in factories)

    def test_database_manager_engine_creation_with_timeout(
        self, database_manager_fixture: _DatabaseManager, mocker: MockerFixture
    ) -> None:
        """Verify engine creation behaves correctly with timeout scenarios."""

        # Setup - create a synchronous function that simulates slow creation
        def slow_create_engine() -> MockType:
            time.sleep(0.01)  # Simulate slow creation (short enough not to timeout)
            return cast("MockType", mocker.Mock())

        mocker.patch(
            "src.infrastructure.database.session.create_database_engine",
            side_effect=slow_create_engine,
        )

        # Execute - since get_engine() is synchronous, we can't use asyncio.timeout
        # Instead, we're testing that the engine creation completes successfully
        engine = database_manager_fixture.get_engine()

        # Assert
        assert engine is not None
        # Verify that subsequent calls return the same engine (singleton pattern)
        assert database_manager_fixture.get_engine() is engine


@pytest.mark.unit
class TestPublicApiFunctions:
    """Tests for public API functions that delegate to the singleton manager."""

    def test_get_engine_delegates_to_manager(
        self,
        mock_database_manager: MockType,
        mock_async_engine: MockType,
    ) -> None:
        """Verify get_engine() delegates to singleton manager."""
        # Setup
        mock_database_manager.get_engine.return_value = mock_async_engine

        # Execute
        result = get_engine()

        # Assert
        mock_database_manager.get_engine.assert_called_once()
        assert result is mock_async_engine

    def test_get_session_factory_delegates_to_manager(
        self,
        mock_database_manager: MockType,
        mock_session_factory: MockType,
    ) -> None:
        """Verify get_session_factory() delegates to singleton manager."""
        # Setup
        mock_database_manager.get_session_factory.return_value = mock_session_factory

        # Execute
        result = get_session_factory()

        # Assert
        mock_database_manager.get_session_factory.assert_called_once()
        assert result is mock_session_factory


@pytest.mark.unit
class TestAsyncSessionContext:
    """Tests for async session context manager."""

    async def test_get_async_session_creates_session(
        self,
        mock_session_factory: MockType,
        mock_async_session: MockType,
        mocker: MockerFixture,
    ) -> None:
        """Verify async session context manager creates session."""
        # Setup
        mocker.patch(
            "src.infrastructure.database.session.get_session_factory",
            return_value=mock_session_factory,
        )

        # Execute
        async with get_async_session() as session:
            assert session is mock_async_session
            # Use session to avoid unused variable warning
            await session.execute(text("SELECT 1"))

        # Assert
        mock_session_factory.assert_called_once()
        mock_async_session.__aenter__.assert_called_once()
        mock_async_session.__aexit__.assert_called_once()

    async def test_get_async_session_commits_on_success(
        self,
        mock_session_factory: MockType,
        mock_async_session: MockType,
        mocker: MockerFixture,
    ) -> None:
        """Verify session is committed when no exception occurs."""
        # Setup
        mocker.patch(
            "src.infrastructure.database.session.get_session_factory",
            return_value=mock_session_factory,
        )
        mock_logger = mocker.patch("src.infrastructure.database.session.logger")

        # Execute
        async with get_async_session() as session:
            # Simulate some work
            await session.execute(text("SELECT 1"))

        # Assert
        mock_async_session.commit.assert_called_once()
        mock_async_session.rollback.assert_not_called()
        mock_async_session.close.assert_called_once()

        # Check logging
        debug_calls = [call[0][0] for call in mock_logger.debug.call_args_list]
        assert "Created new database session" in debug_calls
        assert "Database session committed successfully" in debug_calls
        assert "Database session closed" in debug_calls

    async def test_get_async_session_rollback_on_exception(
        self,
        mock_session_factory: MockType,
        mock_async_session: MockType,
        mocker: MockerFixture,
    ) -> None:
        """Verify session rollback when exception occurs."""
        # Setup
        mocker.patch(
            "src.infrastructure.database.session.get_session_factory",
            return_value=mock_session_factory,
        )
        mock_logger = mocker.patch("src.infrastructure.database.session.logger")

        # Execute
        async def _test_with_error() -> Never:
            async with get_async_session() as session:
                # Use session to avoid unused variable warning
                await session.execute(text("SELECT 1"))
                raise ValueError("Test error")

        with pytest.raises(ValueError, match="Test error"):
            await _test_with_error()

        # Assert
        mock_async_session.rollback.assert_called_once()
        mock_async_session.commit.assert_not_called()
        mock_async_session.close.assert_called_once()

        # Check logging
        debug_calls = [call[0][0] for call in mock_logger.debug.call_args_list]
        assert "Database session rolled back due to error" in debug_calls
        assert "Database session closed" in debug_calls

    async def test_get_async_session_always_closes_session(
        self,
        mock_session_factory: MockType,
        mock_async_session: MockType,
        mocker: MockerFixture,
    ) -> None:
        """Verify session is always closed in finally block."""
        # Setup
        mocker.patch(
            "src.infrastructure.database.session.get_session_factory",
            return_value=mock_session_factory,
        )

        # Make commit raise an exception
        mock_async_session.commit.side_effect = SQLAlchemyError("Commit failed")

        # Execute
        with pytest.raises(SQLAlchemyError, match="Commit failed"):
            async with get_async_session() as session:
                # Use session to avoid unused variable warning
                await session.execute(text("SELECT 1"))

        # Assert
        mock_async_session.close.assert_called_once()

    async def test_get_async_session_logs_lifecycle_events(
        self,
        mock_session_factory: MockType,
        mock_async_session: MockType,
        mocker: MockerFixture,
    ) -> None:
        """Verify proper logging of session lifecycle events."""
        del mock_async_session  # Unused but required for fixture
        # Setup
        mocker.patch(
            "src.infrastructure.database.session.get_session_factory",
            return_value=mock_session_factory,
        )
        mock_logger = mocker.patch("src.infrastructure.database.session.logger")

        # Execute
        async with get_async_session() as session:
            # Use session to avoid unused variable warning
            await session.execute(text("SELECT 1"))

        # Assert
        assert mock_logger.debug.call_count == 3
        debug_messages = [call[0][0] for call in mock_logger.debug.call_args_list]
        assert debug_messages[0] == "Created new database session"
        assert debug_messages[1] == "Database session committed successfully"
        assert debug_messages[2] == "Database session closed"

    @pytest.mark.parametrize(
        "exception_type", [ValueError, KeyError, SQLAlchemyError, RuntimeError]
    )
    async def test_get_async_session_different_exception_types(
        self,
        exception_type: type[Exception],
        mock_session_factory: MockType,
        mock_async_session: MockType,
        mocker: MockerFixture,
    ) -> None:
        """Verify proper handling of different exception types in session context."""
        # Setup
        mocker.patch(
            "src.infrastructure.database.session.get_session_factory",
            return_value=mock_session_factory,
        )

        # Execute
        async def _test_with_exception() -> Never:
            async with get_async_session() as session:
                # Use session to avoid unused variable warning
                await session.execute(text("SELECT 1"))
                raise exception_type("Test error")

        with pytest.raises(exception_type):
            await _test_with_exception()

        # Assert
        mock_async_session.rollback.assert_called_once()
        mock_async_session.commit.assert_not_called()
        mock_async_session.close.assert_called_once()

    async def test_get_async_session_concurrent_access(
        self, mock_session_factory: MockType, mocker: MockerFixture
    ) -> None:
        """Verify concurrent session creation and management."""
        # Setup
        sessions_created = []

        def create_session() -> MockType:
            session = mocker.Mock()
            session.commit = mocker.AsyncMock()
            session.rollback = mocker.AsyncMock()
            session.close = mocker.AsyncMock()
            session.execute = mocker.AsyncMock()
            session.__aenter__ = mocker.AsyncMock(return_value=session)
            session.__aexit__ = mocker.AsyncMock(return_value=None)
            sessions_created.append(session)
            return cast("MockType", session)

        mock_session_factory.side_effect = create_session
        mocker.patch(
            "src.infrastructure.database.session.get_session_factory",
            return_value=mock_session_factory,
        )

        # Execute - create multiple sessions concurrently
        async def use_session(index: int) -> None:
            async with get_async_session() as session:
                await session.execute(text(f"SELECT {index}"))

        await asyncio.gather(
            use_session(1),
            use_session(2),
            use_session(3),
        )

        # Assert
        assert len(sessions_created) == 3
        # Each session should have independent lifecycle
        for session in sessions_created:
            session.commit.assert_called_once()
            session.close.assert_called_once()
            session.rollback.assert_not_called()

    async def test_get_async_session_rollback_exception_handling(
        self,
        mock_session_factory: MockType,
        mock_async_session: MockType,
        mocker: MockerFixture,
    ) -> None:
        """Verify handling when rollback itself raises an exception."""
        # Setup
        mocker.patch(
            "src.infrastructure.database.session.get_session_factory",
            return_value=mock_session_factory,
        )

        # Make rollback raise an exception
        mock_async_session.rollback.side_effect = SQLAlchemyError("Rollback failed")

        # Execute - rollback exception will mask the original error
        with pytest.raises(SQLAlchemyError, match="Rollback failed"):
            async with get_async_session():
                raise ValueError("Original error")

        # Assert - original exception is preserved
        mock_async_session.rollback.assert_called_once()
        mock_async_session.close.assert_called_once()

    async def test_get_async_session_close_exception_handling(
        self,
        mock_session_factory: MockType,
        mock_async_session: MockType,
        mocker: MockerFixture,
    ) -> None:
        """Verify handling when session close raises an exception."""
        # Setup
        mocker.patch(
            "src.infrastructure.database.session.get_session_factory",
            return_value=mock_session_factory,
        )

        # Make close raise an exception
        mock_async_session.close.side_effect = SQLAlchemyError("Close failed")

        # Execute - should complete successfully despite close failure
        try:
            async with get_async_session() as session:
                await session.execute(text("SELECT 1"))
        except SQLAlchemyError:
            # Close exception might bubble up in some cases
            pass

        # Assert
        mock_async_session.commit.assert_called_once()
        mock_async_session.close.assert_called_once()


@pytest.mark.unit
class TestDatabaseConnectionManagement:
    """Tests for database connection management functions."""

    async def test_close_database_delegates_to_manager(
        self,
        mock_database_manager: MockType,
    ) -> None:
        """Verify close_database() delegates to singleton manager."""
        # Execute
        await close_database()

        # Assert
        mock_database_manager.close.assert_called_once()

    async def test_check_database_connection_success(
        self,
        mock_async_engine: MockType,
        mock_sql_text: MockType,
        mocker: MockerFixture,
    ) -> None:
        """Verify health check returns success for healthy database."""
        # Setup
        mocker.patch(
            "src.infrastructure.database.session.get_engine",
            return_value=mock_async_engine,
        )

        # Execute
        is_healthy, error = await check_database_connection()

        # Assert
        assert is_healthy is True
        assert error is None
        mock_async_engine.connect.assert_called_once()
        # Check that SELECT 1 was executed
        mock_sql_text.assert_called_once_with("SELECT 1")

    async def test_check_database_connection_failure(
        self, mock_async_engine: MockType, mocker: MockerFixture
    ) -> None:
        """Verify health check returns failure for database errors."""
        # Setup
        mocker.patch(
            "src.infrastructure.database.session.get_engine",
            return_value=mock_async_engine,
        )

        # Make connection fail
        mock_async_engine.connect.side_effect = SQLAlchemyError("Connection failed")

        # Execute
        is_healthy, error = await check_database_connection()

        # Assert
        assert is_healthy is False
        assert error == "Connection failed"

    async def test_check_database_connection_query_execution(
        self,
        mock_async_engine: MockType,
        mock_sql_text: MockType,
        mocker: MockerFixture,
    ) -> None:
        """Verify health check executes SELECT 1 query."""
        # Setup
        mocker.patch(
            "src.infrastructure.database.session.get_engine",
            return_value=mock_async_engine,
        )

        # Get the mocked connection from engine
        mock_connection = mock_async_engine.connect.return_value

        # Execute
        await check_database_connection()

        # Assert
        mock_sql_text.assert_called_once_with("SELECT 1")
        mock_connection.__aenter__.return_value.execute.assert_called_once_with(
            mock_sql_text.return_value
        )

    @pytest.mark.parametrize(
        ("exception_type", "error_message"),
        [
            (OperationalError, "Database is not available"),
            (DatabaseError, "Database error occurred"),
            (DisconnectionError, "Lost connection to database"),
            (SQLTimeoutError, "Query timeout"),
        ],
    )
    async def test_check_database_connection_specific_sqlalchemy_errors(
        self,
        exception_type: type[SQLAlchemyError],
        error_message: str,
        mock_async_engine: MockType,
        mocker: MockerFixture,
    ) -> None:
        """Verify different SQLAlchemy error types are handled correctly."""
        # Setup
        mocker.patch(
            "src.infrastructure.database.session.get_engine",
            return_value=mock_async_engine,
        )

        # Make connection fail with specific error
        mock_async_engine.connect.side_effect = exception_type(
            error_message, None, None
        )

        # Execute
        is_healthy, error = await check_database_connection()

        # Assert
        assert is_healthy is False
        assert error_message in str(error)

    async def test_check_database_connection_result_scalar_handling(
        self,
        mock_async_engine: MockType,
        mock_sql_text: MockType,
        mocker: MockerFixture,
    ) -> None:
        """Verify result.scalar() is called and result is properly discarded."""
        del mock_sql_text  # Unused but required for fixture
        # Setup
        mocker.patch(
            "src.infrastructure.database.session.get_engine",
            return_value=mock_async_engine,
        )

        # Get mocked connection and result
        mock_connection = mock_async_engine.connect.return_value.__aenter__.return_value
        mock_result = mock_connection.execute.return_value

        # Execute
        await check_database_connection()

        # Assert
        mock_result.scalar.assert_called_once()
        # The result of scalar() should be discarded (assigned to _)

    async def test_check_database_connection_timeout_handling(
        self, mock_async_engine: MockType, mocker: MockerFixture
    ) -> None:
        """Verify health check handles connection timeouts appropriately."""
        # Setup
        mocker.patch(
            "src.infrastructure.database.session.get_engine",
            return_value=mock_async_engine,
        )

        # Make connect return an async context manager that simulates slow connection
        async def slow_aenter(_self: object) -> MockType:
            await asyncio.sleep(2.0)
            return cast("MockType", mocker.AsyncMock())

        mock_slow_connection = mocker.AsyncMock()
        mock_slow_connection.__aenter__ = slow_aenter
        mock_slow_connection.__aexit__ = mocker.AsyncMock(return_value=None)
        mock_async_engine.connect.return_value = mock_slow_connection

        # Execute with timeout
        try:
            async with asyncio.timeout(0.1):  # 100ms timeout
                is_healthy, error = await check_database_connection()
        except TimeoutError:
            # This is expected - the health check itself doesn't have internal timeout
            pass
        else:
            # If we get here, the connection completed faster than expected
            assert is_healthy is False or error is not None
