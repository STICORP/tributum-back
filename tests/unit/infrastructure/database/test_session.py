"""Unit tests for database session management."""

import time

import pytest
import pytest_check
from pytest_mock import MockerFixture
from sqlalchemy.exc import DatabaseError, InvalidRequestError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

import src.infrastructure.database.session
from src.infrastructure.database.session import (
    _after_cursor_execute,
    _before_cursor_execute,
    _query_start_times,
    check_database_connection,
    close_database,
    create_database_engine,
    get_async_session,
    get_engine,
    get_session_factory,
)


@pytest.mark.unit
class TestCreateDatabaseEngine:
    """Test cases for create_database_engine function."""

    def test_create_engine_with_default_config(self, mocker: MockerFixture) -> None:
        """Test creating engine with default configuration."""
        # Mock settings
        mock_settings = mocker.MagicMock()
        mock_settings.database_config.database_url = "postgresql+asyncpg://test/db"
        mock_settings.database_config.pool_size = 10
        mock_settings.database_config.max_overflow = 5
        mock_settings.database_config.pool_timeout = 30.0
        mock_settings.database_config.pool_pre_ping = True
        mock_settings.database_config.echo = False
        mock_settings.log_config.enable_sql_logging = False  # Disable SQL logging

        mocker.patch(
            "src.infrastructure.database.session.get_settings",
            return_value=mock_settings,
        )

        # Mock create_async_engine
        mock_engine = mocker.MagicMock(spec=AsyncEngine)
        mock_create_engine = mocker.patch(
            "src.infrastructure.database.session.create_async_engine",
            return_value=mock_engine,
        )

        # Create engine
        engine = create_database_engine()

        # Verify engine was created with correct parameters
        mock_create_engine.assert_called_once_with(
            "postgresql+asyncpg://test/db",
            pool_size=10,
            max_overflow=5,
            pool_timeout=30.0,
            pool_pre_ping=True,
            echo=False,
            pool_recycle=3600,
            connect_args={
                "server_settings": {"jit": "off"},
                "command_timeout": 60,
            },
        )

        assert engine is mock_engine

    def test_create_engine_with_custom_url(self, mocker: MockerFixture) -> None:
        """Test creating engine with custom database URL."""
        # Mock settings
        mock_settings = mocker.MagicMock()
        mock_settings.database_config.database_url = "postgresql+asyncpg://default/db"
        mock_settings.database_config.pool_size = 10
        mock_settings.database_config.max_overflow = 5
        mock_settings.database_config.pool_timeout = 30.0
        mock_settings.database_config.pool_pre_ping = True
        mock_settings.database_config.echo = False
        mock_settings.log_config.enable_sql_logging = False  # Disable SQL logging

        mocker.patch(
            "src.infrastructure.database.session.get_settings",
            return_value=mock_settings,
        )

        # Mock create_async_engine
        mock_engine = mocker.MagicMock(spec=AsyncEngine)
        mock_create_engine = mocker.patch(
            "src.infrastructure.database.session.create_async_engine",
            return_value=mock_engine,
        )

        # Create engine with custom URL
        custom_url = "postgresql+asyncpg://custom/test"
        engine = create_database_engine(custom_url)

        # Verify custom URL was used
        mock_create_engine.assert_called_once()
        call_args = mock_create_engine.call_args[0]
        assert call_args[0] == custom_url

        assert engine is mock_engine

    def test_create_engine_with_echo_enabled(self, mocker: MockerFixture) -> None:
        """Test creating engine with SQL echo enabled."""
        # Mock settings with echo enabled
        mock_settings = mocker.MagicMock()
        mock_settings.database_config.database_url = "postgresql+asyncpg://test/db"
        mock_settings.database_config.pool_size = 10
        mock_settings.database_config.max_overflow = 5
        mock_settings.database_config.pool_timeout = 30.0
        mock_settings.database_config.pool_pre_ping = True
        mock_settings.database_config.echo = True  # Echo enabled
        mock_settings.log_config.enable_sql_logging = (
            False  # Disable SQL logging to avoid event listener setup
        )

        mocker.patch(
            "src.infrastructure.database.session.get_settings",
            return_value=mock_settings,
        )

        # Mock create_async_engine
        mock_engine = mocker.MagicMock(spec=AsyncEngine)
        mock_create_engine = mocker.patch(
            "src.infrastructure.database.session.create_async_engine",
            return_value=mock_engine,
        )

        # Create engine
        create_database_engine()

        # Verify echo parameter was passed
        call_kwargs = mock_create_engine.call_args[1]
        assert call_kwargs["echo"] is True

    def test_create_engine_with_sql_logging_enabled(
        self, mocker: MockerFixture
    ) -> None:
        """Test creating engine with SQL logging and instrumentation enabled."""
        # Mock settings with SQL logging enabled
        mock_settings = mocker.MagicMock()
        mock_settings.database_config.database_url = "postgresql+asyncpg://test/db"
        mock_settings.database_config.pool_size = 10
        mock_settings.database_config.max_overflow = 5
        mock_settings.database_config.pool_timeout = 30.0
        mock_settings.database_config.pool_pre_ping = True
        mock_settings.database_config.echo = False
        mock_settings.log_config.enable_sql_logging = True  # Enable SQL logging

        mocker.patch(
            "src.infrastructure.database.session.get_settings",
            return_value=mock_settings,
        )

        # Mock create_async_engine
        mock_sync_engine = mocker.MagicMock()
        mock_engine = mocker.MagicMock(spec=AsyncEngine)
        mock_engine.sync_engine = mock_sync_engine
        mocker.patch(
            "src.infrastructure.database.session.create_async_engine",
            return_value=mock_engine,
        )

        # Mock SQLAlchemyInstrumentor
        mock_instrumentor = mocker.MagicMock()
        mocker.patch(
            "src.infrastructure.database.session.SQLAlchemyInstrumentor",
            return_value=mock_instrumentor,
        )

        # Mock event.listen to avoid errors
        mock_event_listen = mocker.patch(
            "src.infrastructure.database.session.event.listen"
        )

        # Create engine
        create_database_engine()

        # Verify OpenTelemetry instrumentation was called
        mock_instrumentor.instrument.assert_called_once_with(
            engine=mock_sync_engine,
            enable_commenter=True,
            commenter_options={"opentelemetry_values": True},
        )

        # Verify event listeners were registered
        assert mock_event_listen.call_count == 2  # before and after listeners
        mock_event_listen.assert_any_call(
            mock_sync_engine, "before_cursor_execute", mocker.ANY
        )
        mock_event_listen.assert_any_call(
            mock_sync_engine, "after_cursor_execute", mocker.ANY
        )

    def test_create_engine_with_instrumentation_failure(
        self, mocker: MockerFixture, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test creating engine when OpenTelemetry instrumentation fails."""
        # Mock settings with SQL logging enabled
        mock_settings = mocker.MagicMock()
        mock_settings.database_config.database_url = "postgresql+asyncpg://test/db"
        mock_settings.database_config.pool_size = 10
        mock_settings.database_config.max_overflow = 5
        mock_settings.database_config.pool_timeout = 30.0
        mock_settings.database_config.pool_pre_ping = True
        mock_settings.database_config.echo = False
        mock_settings.log_config.enable_sql_logging = True

        mocker.patch(
            "src.infrastructure.database.session.get_settings",
            return_value=mock_settings,
        )

        # Mock create_async_engine
        mock_sync_engine = mocker.MagicMock()
        mock_engine = mocker.MagicMock(spec=AsyncEngine)
        mock_engine.sync_engine = mock_sync_engine
        mocker.patch(
            "src.infrastructure.database.session.create_async_engine",
            return_value=mock_engine,
        )

        # Mock SQLAlchemyInstrumentor to raise exception
        mock_instrumentor = mocker.MagicMock()
        mock_instrumentor.instrument.side_effect = RuntimeError(
            "Instrumentation failed"
        )
        mocker.patch(
            "src.infrastructure.database.session.SQLAlchemyInstrumentor",
            return_value=mock_instrumentor,
        )

        # Mock event.listen
        mocker.patch("src.infrastructure.database.session.event.listen")

        # Create engine - should not raise exception
        engine = create_database_engine()
        assert engine is mock_engine

        # Verify warning was logged
        warning_found = False
        for record in caplog.records:
            if record.levelname == "WARNING":
                message = str(record.getMessage())
                if "Failed to enable OpenTelemetry" in message:
                    warning_found = True
                    assert "RuntimeError" in message
                    break

        assert warning_found, (
            "No warning logs found. Records: "
            f"{[(r.levelname, r.getMessage()) for r in caplog.records]}"
        )

    def test_create_engine_with_event_listener_failure(
        self, mocker: MockerFixture, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test creating engine when event listener registration fails."""
        # Mock settings with SQL logging enabled
        mock_settings = mocker.MagicMock()
        mock_settings.database_config.database_url = "postgresql+asyncpg://test/db"
        mock_settings.database_config.pool_size = 10
        mock_settings.database_config.max_overflow = 5
        mock_settings.database_config.pool_timeout = 30.0
        mock_settings.database_config.pool_pre_ping = True
        mock_settings.database_config.echo = False
        mock_settings.log_config.enable_sql_logging = True

        mocker.patch(
            "src.infrastructure.database.session.get_settings",
            return_value=mock_settings,
        )

        # Mock create_async_engine
        mock_sync_engine = mocker.MagicMock()
        mock_engine = mocker.MagicMock(spec=AsyncEngine)
        mock_engine.sync_engine = mock_sync_engine
        mocker.patch(
            "src.infrastructure.database.session.create_async_engine",
            return_value=mock_engine,
        )

        # Mock SQLAlchemyInstrumentor to succeed
        mock_instrumentor = mocker.MagicMock()
        mocker.patch(
            "src.infrastructure.database.session.SQLAlchemyInstrumentor",
            return_value=mock_instrumentor,
        )

        # Mock event.listen to raise InvalidRequestError
        mock_event_listen = mocker.patch(
            "src.infrastructure.database.session.event.listen",
            side_effect=InvalidRequestError("No such event 'before_cursor_execute'"),
        )

        # Create engine - should not raise exception
        engine = create_database_engine()
        assert engine is mock_engine

        # Verify event.listen was called
        assert mock_event_listen.call_count >= 1

        # Verify warning was logged
        warning_found = False
        for record in caplog.records:
            if record.levelname == "WARNING":
                message = str(record.getMessage())
                if "Failed to register query performance event listeners" in message:
                    warning_found = True
                    assert "InvalidRequestError" in message
                    break

        assert warning_found, (
            "No warning logs found. Records: "
            f"{[(r.levelname, r.getMessage()) for r in caplog.records]}"
        )


@pytest.mark.unit
class TestGetEngine:
    """Test cases for get_engine function."""

    def test_get_engine_creates_singleton(self, mocker: MockerFixture) -> None:
        """Test that get_engine creates a singleton instance."""
        # Reset database manager
        src.infrastructure.database.session._db_manager.reset()

        # Mock create_database_engine
        mock_engine = mocker.MagicMock(spec=AsyncEngine)
        mock_create = mocker.patch(
            "src.infrastructure.database.session.create_database_engine",
            return_value=mock_engine,
        )

        # First call should create engine
        engine1 = get_engine()
        assert engine1 is mock_engine
        mock_create.assert_called_once()

        # Second call should return same instance
        engine2 = get_engine()
        assert engine2 is engine1
        mock_create.assert_called_once()  # Still only called once

        # Cleanup
        src.infrastructure.database.session._db_manager.reset()

    def test_get_engine_returns_existing_instance(self, mocker: MockerFixture) -> None:
        """Test that get_engine returns existing engine if already created."""
        # Set up existing engine
        existing_engine = mocker.MagicMock(spec=AsyncEngine)
        src.infrastructure.database.session._db_manager._engine = existing_engine

        # Mock create_database_engine (should not be called)
        mock_create = mocker.patch(
            "src.infrastructure.database.session.create_database_engine"
        )

        # Get engine should return existing instance
        engine = get_engine()
        assert engine is existing_engine
        mock_create.assert_not_called()

        # Cleanup
        src.infrastructure.database.session._db_manager.reset()


@pytest.mark.unit
class TestGetSessionFactory:
    """Test cases for get_session_factory function."""

    def test_get_session_factory_creates_singleton(self, mocker: MockerFixture) -> None:
        """Test that get_session_factory creates a singleton instance."""
        # Reset database manager
        src.infrastructure.database.session._db_manager.reset()

        # Mock engine
        mock_engine = mocker.MagicMock(spec=AsyncEngine)
        mocker.patch(
            "src.infrastructure.database.session._db_manager.get_engine",
            return_value=mock_engine,
        )

        # Mock async_sessionmaker
        mock_factory = mocker.MagicMock()
        mock_sessionmaker = mocker.patch(
            "src.infrastructure.database.session.async_sessionmaker",
            return_value=mock_factory,
        )

        # First call should create factory
        factory1 = get_session_factory()
        assert factory1 is mock_factory
        mock_sessionmaker.assert_called_once_with(
            mock_engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

        # Second call should return same instance
        factory2 = get_session_factory()
        assert factory2 is factory1
        mock_sessionmaker.assert_called_once()  # Still only called once

        # Cleanup
        src.infrastructure.database.session._db_manager.reset()

    def test_get_session_factory_returns_existing_instance(
        self, mocker: MockerFixture
    ) -> None:
        """Test that get_session_factory returns existing factory if already created."""
        # Set up existing factory
        existing_factory = mocker.MagicMock()
        src.infrastructure.database.session._db_manager._async_session_factory = (
            existing_factory
        )

        # Mock get_engine (should not be called)
        mock_get_engine = mocker.patch(
            "src.infrastructure.database.session._db_manager.get_engine"
        )

        # Get factory should return existing instance
        factory = get_session_factory()
        assert factory is existing_factory
        mock_get_engine.assert_not_called()

        # Cleanup
        src.infrastructure.database.session._db_manager.reset()


@pytest.mark.unit
@pytest.mark.asyncio
class TestGetAsyncSession:
    """Test cases for get_async_session context manager."""

    async def test_get_async_session_success(self, mocker: MockerFixture) -> None:
        """Test successful session creation and cleanup."""
        # Mock session
        mock_session = mocker.AsyncMock(spec=AsyncSession)

        # Mock session factory
        mock_factory = mocker.AsyncMock()
        mock_factory.__aenter__.return_value = mock_session
        mock_factory.__aexit__.return_value = None

        mock_sessionmaker = mocker.MagicMock()
        mock_sessionmaker.return_value = mock_factory

        mocker.patch(
            "src.infrastructure.database.session.get_session_factory",
            return_value=mock_sessionmaker,
        )

        # Use the context manager
        async with get_async_session() as session:
            assert session is mock_session

        # Verify session lifecycle methods were called
        mock_session.commit.assert_called_once()
        mock_session.close.assert_called_once()
        mock_session.rollback.assert_not_called()

    async def test_get_async_session_with_exception(
        self, mocker: MockerFixture
    ) -> None:
        """Test session rollback on exception."""
        # Mock session
        mock_session = mocker.AsyncMock(spec=AsyncSession)

        # Mock session factory
        mock_factory = mocker.AsyncMock()
        mock_factory.__aenter__.return_value = mock_session
        mock_factory.__aexit__.return_value = None

        mock_sessionmaker = mocker.MagicMock()
        mock_sessionmaker.return_value = mock_factory

        mocker.patch(
            "src.infrastructure.database.session.get_session_factory",
            return_value=mock_sessionmaker,
        )

        # Use the context manager with an exception
        async def session_with_error() -> None:
            async with get_async_session() as session:
                assert session is mock_session
                msg = "Test error"
                raise ValueError(msg)

        with pytest.raises(ValueError, match="Test error"):
            await session_with_error()

        # Verify rollback was called instead of commit
        mock_session.rollback.assert_called_once()
        mock_session.commit.assert_not_called()
        mock_session.close.assert_called_once()

    async def test_get_async_session_database_error(
        self, mocker: MockerFixture
    ) -> None:
        """Test session behavior with database error during commit."""
        # Mock session that raises error on commit
        mock_session = mocker.AsyncMock(spec=AsyncSession)
        mock_session.commit.side_effect = DatabaseError(
            "Connection lost", "", Exception("Connection lost")
        )

        # Mock session factory
        mock_factory = mocker.AsyncMock()
        mock_factory.__aenter__.return_value = mock_session
        mock_factory.__aexit__.return_value = None

        mock_sessionmaker = mocker.MagicMock()
        mock_sessionmaker.return_value = mock_factory

        mocker.patch(
            "src.infrastructure.database.session.get_session_factory",
            return_value=mock_sessionmaker,
        )

        # Use the context manager
        with pytest.raises(DatabaseError, match="Connection lost"):
            async with get_async_session() as session:
                assert session is mock_session

        # Verify rollback and close were still called
        mock_session.rollback.assert_called_once()
        mock_session.close.assert_called_once()

    async def test_get_async_session_cleanup_even_on_close_error(
        self, mocker: MockerFixture
    ) -> None:
        """Test that close is called even if other operations fail."""
        # Mock session that raises error on rollback
        mock_session = mocker.AsyncMock(spec=AsyncSession)
        mock_session.rollback.side_effect = DatabaseError(
            "Rollback failed", "", Exception("Rollback failed")
        )

        # Mock session factory
        mock_factory = mocker.AsyncMock()
        mock_factory.__aenter__.return_value = mock_session
        mock_factory.__aexit__.return_value = None

        mock_sessionmaker = mocker.MagicMock()
        mock_sessionmaker.return_value = mock_factory

        mocker.patch(
            "src.infrastructure.database.session.get_session_factory",
            return_value=mock_sessionmaker,
        )

        # Use the context manager with an exception
        async def session_with_error() -> None:
            async with get_async_session() as session:
                assert session is mock_session
                msg = "Test error"
                raise ValueError(msg)

        # The rollback error will be raised instead of the original ValueError
        with pytest.raises(DatabaseError, match="Rollback failed"):
            await session_with_error()

        # Verify close was still called despite rollback error
        mock_session.close.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
class TestCloseDatabase:
    """Test cases for close_database function."""

    async def test_close_database_disposes_engine(self, mocker: MockerFixture) -> None:
        """Test that close_database properly disposes the engine."""
        # Set up existing engine
        mock_engine = mocker.AsyncMock(spec=AsyncEngine)
        src.infrastructure.database.session._db_manager._engine = mock_engine
        src.infrastructure.database.session._db_manager._async_session_factory = (
            mocker.MagicMock()
        )

        # Call close_database
        await close_database()

        # Verify engine was disposed
        mock_engine.dispose.assert_called_once()

        # Verify manager state was reset
        db_manager = src.infrastructure.database.session._db_manager
        assert db_manager._engine is None
        assert db_manager._async_session_factory is None

    async def test_close_database_when_no_engine(self) -> None:
        """Test that close_database handles case when no engine exists."""
        # Reset database manager
        src.infrastructure.database.session._db_manager.reset()

        # Call close_database - should not raise any errors
        await close_database()

        # Verify manager state is still None
        db_manager = src.infrastructure.database.session._db_manager
        assert db_manager._engine is None
        assert db_manager._async_session_factory is None

    async def test_close_database_handles_dispose_error(
        self, mocker: MockerFixture
    ) -> None:
        """Test that close_database handles errors during engine disposal."""
        # Set up engine that raises error on dispose
        mock_engine = mocker.AsyncMock(spec=AsyncEngine)
        mock_engine.dispose.side_effect = Exception("Dispose failed")
        src.infrastructure.database.session._db_manager._engine = mock_engine
        src.infrastructure.database.session._db_manager._async_session_factory = (
            mocker.MagicMock()
        )

        # Call close_database - should propagate the exception
        with pytest.raises(Exception, match="Dispose failed"):
            await close_database()

        # Engine should still be set since disposal failed
        assert src.infrastructure.database.session._db_manager._engine is mock_engine


@pytest.mark.unit
@pytest.mark.asyncio
class TestIntegrationScenarios:
    """Integration tests for session management."""

    async def test_connection_pool_configuration(self, mocker: MockerFixture) -> None:
        """Test that pool configuration is properly applied."""
        # Mock settings with specific pool config
        mock_settings = mocker.MagicMock()
        mock_settings.database_config.database_url = "postgresql+asyncpg://test/db"
        mock_settings.database_config.pool_size = 20
        mock_settings.database_config.max_overflow = 10
        mock_settings.database_config.pool_timeout = 60.0
        mock_settings.database_config.pool_pre_ping = False
        mock_settings.database_config.echo = False
        mock_settings.log_config.enable_sql_logging = False  # Disable SQL logging

        mocker.patch(
            "src.infrastructure.database.session.get_settings",
            return_value=mock_settings,
        )

        # Mock create_async_engine
        mock_create_engine = mocker.patch(
            "src.infrastructure.database.session.create_async_engine",
            return_value=mocker.MagicMock(spec=AsyncEngine),
        )

        # Reset database manager
        src.infrastructure.database.session._db_manager.reset()

        # Create engine through get_engine
        get_engine()

        # Verify pool configuration was applied
        call_kwargs = mock_create_engine.call_args[1]
        with pytest_check.check:
            assert call_kwargs["pool_size"] == 20
        with pytest_check.check:
            assert call_kwargs["max_overflow"] == 10
        with pytest_check.check:
            assert call_kwargs["pool_timeout"] == 60.0
        with pytest_check.check:
            assert call_kwargs["pool_pre_ping"] is False

        # Cleanup
        src.infrastructure.database.session._db_manager.reset()

    async def test_full_lifecycle(self, mocker: MockerFixture) -> None:
        """Test full lifecycle: create engine, get session, close database."""
        # Reset database manager
        src.infrastructure.database.session._db_manager.reset()

        # Mock dependencies
        mock_settings = mocker.MagicMock()
        mock_settings.database_config.database_url = "postgresql+asyncpg://test/db"
        mock_settings.database_config.pool_size = 10
        mock_settings.database_config.max_overflow = 5
        mock_settings.database_config.pool_timeout = 30.0
        mock_settings.database_config.pool_pre_ping = True
        mock_settings.database_config.echo = False
        mock_settings.log_config.enable_sql_logging = False  # Disable SQL logging

        mocker.patch(
            "src.infrastructure.database.session.get_settings",
            return_value=mock_settings,
        )

        # Mock engine
        mock_engine = mocker.AsyncMock(spec=AsyncEngine)
        mocker.patch(
            "src.infrastructure.database.session.create_async_engine",
            return_value=mock_engine,
        )

        # Mock session
        mock_session = mocker.AsyncMock(spec=AsyncSession)
        mock_factory = mocker.AsyncMock()
        mock_factory.__aenter__.return_value = mock_session
        mock_factory.__aexit__.return_value = None

        mock_sessionmaker_instance = mocker.MagicMock()
        mock_sessionmaker_instance.return_value = mock_factory

        mocker.patch(
            "src.infrastructure.database.session.async_sessionmaker",
            return_value=mock_sessionmaker_instance,
        )

        # Use session
        async with get_async_session() as session:
            assert session is mock_session

        # Verify session was properly managed
        mock_session.commit.assert_called_once()
        mock_session.close.assert_called_once()

        # Close database
        await close_database()

        # Verify cleanup
        mock_engine.dispose.assert_called_once()
        db_manager = src.infrastructure.database.session._db_manager
        assert db_manager._engine is None
        assert db_manager._async_session_factory is None


@pytest.mark.unit
class TestDatabaseManager:
    """Test cases for _DatabaseManager class."""

    def test_reset_method(self, mocker: MockerFixture) -> None:
        """Test that reset method clears all state."""
        # Mock create_database_engine to return a different engine each time
        mock_engine1 = mocker.MagicMock(spec=AsyncEngine)
        mock_engine2 = mocker.MagicMock(spec=AsyncEngine)
        mock_create = mocker.patch(
            "src.infrastructure.database.session.create_database_engine",
            side_effect=[mock_engine1, mock_engine2],
        )

        # Create a fresh manager instance
        manager = src.infrastructure.database.session._DatabaseManager()

        # Get engine and factory - this should create them
        engine1 = manager.get_engine()
        factory1 = manager.get_session_factory()

        # Verify they were created
        assert engine1 is mock_engine1
        assert factory1 is not None
        mock_create.assert_called_once()

        # Reset the manager
        manager.reset()

        # Get engine again - should create a new one
        engine2 = manager.get_engine()
        factory2 = manager.get_session_factory()

        # Verify new instances were created
        assert engine2 is mock_engine2
        assert factory2 is not None
        assert engine2 is not engine1
        assert factory2 is not factory1
        assert mock_create.call_count == 2


@pytest.mark.unit
class TestQueryEventListeners:
    """Test cases for query event listener functions."""

    def test_before_cursor_execute_sets_start_time(self, mocker: MockerFixture) -> None:
        """Test that before_cursor_execute sets query start time."""
        # Create mock context
        mock_context = mocker.MagicMock()

        # Call before_cursor_execute
        _before_cursor_execute(
            _conn=mocker.MagicMock(),
            _cursor=mocker.MagicMock(),
            _statement="SELECT 1",
            _parameters=None,
            context=mock_context,
            _executemany=False,
        )

        # Verify start time was set in the weak dictionary
        assert mock_context in _query_start_times
        assert isinstance(_query_start_times[mock_context], float)
        assert _query_start_times[mock_context] > 0

    def test_after_cursor_execute_tracks_metrics(self, mocker: MockerFixture) -> None:
        """Test that after_cursor_execute tracks query metrics."""
        # Mock dependencies
        mock_settings = mocker.MagicMock()
        mock_settings.log_config.enable_sql_logging = True
        mock_settings.log_config.slow_query_threshold_ms = 100
        mocker.patch(
            "src.infrastructure.database.session.get_settings",
            return_value=mock_settings,
        )

        # Mock logger context functions
        mocker.patch(
            "src.infrastructure.database.session.get_logger_context",
            return_value={"db_query_count": 2, "db_query_duration_ms": 50.0},
        )
        mock_bind_context = mocker.patch(
            "src.infrastructure.database.session.bind_logger_context"
        )

        # Mock RequestContext
        mocker.patch(
            "src.infrastructure.database.session.RequestContext.get_correlation_id",
            return_value="test-correlation-123",
        )

        # Create mock context and set start time
        mock_context = mocker.MagicMock()
        _query_start_times[mock_context] = time.time() - 0.05  # 50ms ago

        # Call after_cursor_execute
        _after_cursor_execute(
            _conn=mocker.MagicMock(),
            _cursor=mocker.MagicMock(),
            statement="SELECT * FROM users",
            parameters={"id": 123},
            context=mock_context,
            executemany=False,
        )

        # Verify bind_logger_context was called with aggregated metrics
        mock_bind_context.assert_called_once()
        call_kwargs = mock_bind_context.call_args[1]
        assert call_kwargs["db_query_count"] == 3  # 2 + 1
        assert call_kwargs["db_query_duration_ms"] >= 100.0  # Previous 50 + new 50+

    def test_after_cursor_execute_logs_slow_queries(
        self, mocker: MockerFixture, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that slow queries are logged."""
        # Mock dependencies
        mock_settings = mocker.MagicMock()
        mock_settings.log_config.enable_sql_logging = True
        mock_settings.log_config.slow_query_threshold_ms = 10  # Low threshold
        mocker.patch(
            "src.infrastructure.database.session.get_settings",
            return_value=mock_settings,
        )

        # Mock logger context
        mocker.patch(
            "src.core.logging.get_logger_context",
            return_value={},
        )
        mocker.patch("src.infrastructure.database.session.bind_logger_context")

        # Mock RequestContext
        mocker.patch(
            "src.infrastructure.database.session.RequestContext.get_correlation_id",
            return_value="test-correlation-123",
        )

        # Create mock context and set start time 50ms ago
        mock_context = mocker.MagicMock()
        _query_start_times[mock_context] = time.time() - 0.05  # 50ms ago

        # Call after_cursor_execute
        _after_cursor_execute(
            _conn=mocker.MagicMock(),
            _cursor=mocker.MagicMock(),
            statement="SELECT * FROM large_table WHERE status = :status",
            parameters={"status": "active"},
            context=mock_context,
            executemany=False,
        )

        # Check that slow query was logged
        caplog.set_level("WARNING")

        # Look through all records for the slow query
        slow_query_found = False
        for record in caplog.records:
            message = str(record.getMessage())
            if "slow_query_detected" in message:
                slow_query_found = True
                # Verify key information is in the log message
                assert "SELECT * FROM large_table" in message
                assert "test-correlation-123" in message
                assert "duration_ms" in message
                assert "threshold_ms" in message
                break

        assert slow_query_found, (
            "No slow query logs found. Records: "
            f"{[r.getMessage() for r in caplog.records]}"
        )


@pytest.mark.unit
class TestCheckDatabaseConnection:
    """Test cases for check_database_connection function."""

    async def test_check_database_connection_success(
        self, mocker: MockerFixture
    ) -> None:
        """Test successful database connection check."""
        # Mock engine and connection
        mock_result = mocker.Mock()
        mock_result.scalar.return_value = 1

        mock_conn = mocker.Mock()
        mock_conn.execute = mocker.AsyncMock(return_value=mock_result)
        mock_conn.__aenter__ = mocker.AsyncMock(return_value=mock_conn)
        mock_conn.__aexit__ = mocker.AsyncMock()

        mock_engine = mocker.Mock()
        mock_engine.connect.return_value = mock_conn

        mocker.patch(
            "src.infrastructure.database.session.get_engine", return_value=mock_engine
        )

        # Call the function
        is_healthy, error_msg = await check_database_connection()

        # Assert success
        assert is_healthy is True
        assert error_msg is None
        mock_result.scalar.assert_called_once()

    async def test_check_database_connection_failure(
        self, mocker: MockerFixture
    ) -> None:
        """Test database connection check when SQLAlchemyError is raised."""
        # Mock engine to raise SQLAlchemyError on connect
        mock_engine = mocker.Mock()
        mock_conn = mocker.Mock()
        mock_conn.__aenter__ = mocker.AsyncMock(
            side_effect=SQLAlchemyError("Connection refused")
        )
        mock_conn.__aexit__ = mocker.AsyncMock()
        mock_engine.connect.return_value = mock_conn

        mocker.patch(
            "src.infrastructure.database.session.get_engine", return_value=mock_engine
        )

        # Call the function
        is_healthy, error_msg = await check_database_connection()

        # Assert failure
        assert is_healthy is False
        assert error_msg == "Connection refused"
