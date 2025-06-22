"""Unit tests for database session management."""

from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_check
from sqlalchemy.exc import DatabaseError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

import src.infrastructure.database.session
from src.infrastructure.database.session import (
    close_database,
    create_database_engine,
    get_async_session,
    get_engine,
    get_session_factory,
)


@pytest.mark.unit
class TestCreateDatabaseEngine:
    """Test cases for create_database_engine function."""

    def test_create_engine_with_default_config(self, mocker: MagicMock) -> None:
        """Test creating engine with default configuration."""
        # Mock settings
        mock_settings = MagicMock()
        mock_settings.database_config.database_url = "postgresql+asyncpg://test/db"
        mock_settings.database_config.pool_size = 10
        mock_settings.database_config.max_overflow = 5
        mock_settings.database_config.pool_timeout = 30.0
        mock_settings.database_config.pool_pre_ping = True
        mock_settings.database_config.echo = False

        mocker.patch(
            "src.infrastructure.database.session.get_settings",
            return_value=mock_settings,
        )

        # Mock create_async_engine
        mock_engine = MagicMock(spec=AsyncEngine)
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

    def test_create_engine_with_custom_url(self, mocker: MagicMock) -> None:
        """Test creating engine with custom database URL."""
        # Mock settings
        mock_settings = MagicMock()
        mock_settings.database_config.database_url = "postgresql+asyncpg://default/db"
        mock_settings.database_config.pool_size = 10
        mock_settings.database_config.max_overflow = 5
        mock_settings.database_config.pool_timeout = 30.0
        mock_settings.database_config.pool_pre_ping = True
        mock_settings.database_config.echo = False

        mocker.patch(
            "src.infrastructure.database.session.get_settings",
            return_value=mock_settings,
        )

        # Mock create_async_engine
        mock_engine = MagicMock(spec=AsyncEngine)
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

    def test_create_engine_with_echo_enabled(self, mocker: MagicMock) -> None:
        """Test creating engine with SQL echo enabled."""
        # Mock settings with echo enabled
        mock_settings = MagicMock()
        mock_settings.database_config.database_url = "postgresql+asyncpg://test/db"
        mock_settings.database_config.pool_size = 10
        mock_settings.database_config.max_overflow = 5
        mock_settings.database_config.pool_timeout = 30.0
        mock_settings.database_config.pool_pre_ping = True
        mock_settings.database_config.echo = True  # Echo enabled

        mocker.patch(
            "src.infrastructure.database.session.get_settings",
            return_value=mock_settings,
        )

        # Mock create_async_engine
        mock_engine = MagicMock(spec=AsyncEngine)
        mock_create_engine = mocker.patch(
            "src.infrastructure.database.session.create_async_engine",
            return_value=mock_engine,
        )

        # Create engine
        create_database_engine()

        # Verify echo parameter was passed
        call_kwargs = mock_create_engine.call_args[1]
        assert call_kwargs["echo"] is True


@pytest.mark.unit
class TestGetEngine:
    """Test cases for get_engine function."""

    def test_get_engine_creates_singleton(self, mocker: MagicMock) -> None:
        """Test that get_engine creates a singleton instance."""
        # Reset database manager
        src.infrastructure.database.session._db_manager.reset()

        # Mock create_database_engine
        mock_engine = MagicMock(spec=AsyncEngine)
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

    def test_get_engine_returns_existing_instance(self, mocker: MagicMock) -> None:
        """Test that get_engine returns existing engine if already created."""
        # Set up existing engine
        existing_engine = MagicMock(spec=AsyncEngine)
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

    def test_get_session_factory_creates_singleton(self, mocker: MagicMock) -> None:
        """Test that get_session_factory creates a singleton instance."""
        # Reset database manager
        src.infrastructure.database.session._db_manager.reset()

        # Mock engine
        mock_engine = MagicMock(spec=AsyncEngine)
        mocker.patch(
            "src.infrastructure.database.session._db_manager.get_engine",
            return_value=mock_engine,
        )

        # Mock async_sessionmaker
        mock_factory = MagicMock()
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
        self, mocker: MagicMock
    ) -> None:
        """Test that get_session_factory returns existing factory if already created."""
        # Set up existing factory
        existing_factory = MagicMock()
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

    async def test_get_async_session_success(self, mocker: MagicMock) -> None:
        """Test successful session creation and cleanup."""
        # Mock session
        mock_session = AsyncMock(spec=AsyncSession)

        # Mock session factory
        mock_factory = AsyncMock()
        mock_factory.__aenter__.return_value = mock_session
        mock_factory.__aexit__.return_value = None

        mock_sessionmaker = MagicMock()
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

    async def test_get_async_session_with_exception(self, mocker: MagicMock) -> None:
        """Test session rollback on exception."""
        # Mock session
        mock_session = AsyncMock(spec=AsyncSession)

        # Mock session factory
        mock_factory = AsyncMock()
        mock_factory.__aenter__.return_value = mock_session
        mock_factory.__aexit__.return_value = None

        mock_sessionmaker = MagicMock()
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

    async def test_get_async_session_database_error(self, mocker: MagicMock) -> None:
        """Test session behavior with database error during commit."""
        # Mock session that raises error on commit
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.commit.side_effect = DatabaseError(
            "Connection lost", "", Exception("Connection lost")
        )

        # Mock session factory
        mock_factory = AsyncMock()
        mock_factory.__aenter__.return_value = mock_session
        mock_factory.__aexit__.return_value = None

        mock_sessionmaker = MagicMock()
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
        self, mocker: MagicMock
    ) -> None:
        """Test that close is called even if other operations fail."""
        # Mock session that raises error on rollback
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.rollback.side_effect = DatabaseError(
            "Rollback failed", "", Exception("Rollback failed")
        )

        # Mock session factory
        mock_factory = AsyncMock()
        mock_factory.__aenter__.return_value = mock_session
        mock_factory.__aexit__.return_value = None

        mock_sessionmaker = MagicMock()
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

    async def test_close_database_disposes_engine(self) -> None:
        """Test that close_database properly disposes the engine."""
        # Set up existing engine
        mock_engine = AsyncMock(spec=AsyncEngine)
        src.infrastructure.database.session._db_manager._engine = mock_engine
        src.infrastructure.database.session._db_manager._async_session_factory = (
            MagicMock()
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

    async def test_close_database_handles_dispose_error(self) -> None:
        """Test that close_database handles errors during engine disposal."""
        # Set up engine that raises error on dispose
        mock_engine = AsyncMock(spec=AsyncEngine)
        mock_engine.dispose.side_effect = Exception("Dispose failed")
        src.infrastructure.database.session._db_manager._engine = mock_engine
        src.infrastructure.database.session._db_manager._async_session_factory = (
            MagicMock()
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

    async def test_connection_pool_configuration(self, mocker: MagicMock) -> None:
        """Test that pool configuration is properly applied."""
        # Mock settings with specific pool config
        mock_settings = MagicMock()
        mock_settings.database_config.database_url = "postgresql+asyncpg://test/db"
        mock_settings.database_config.pool_size = 20
        mock_settings.database_config.max_overflow = 10
        mock_settings.database_config.pool_timeout = 60.0
        mock_settings.database_config.pool_pre_ping = False
        mock_settings.database_config.echo = False

        mocker.patch(
            "src.infrastructure.database.session.get_settings",
            return_value=mock_settings,
        )

        # Mock create_async_engine
        mock_create_engine = mocker.patch(
            "src.infrastructure.database.session.create_async_engine",
            return_value=MagicMock(spec=AsyncEngine),
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

    async def test_full_lifecycle(self, mocker: MagicMock) -> None:
        """Test full lifecycle: create engine, get session, close database."""
        # Reset database manager
        src.infrastructure.database.session._db_manager.reset()

        # Mock dependencies
        mock_settings = MagicMock()
        mock_settings.database_config.database_url = "postgresql+asyncpg://test/db"
        mock_settings.database_config.pool_size = 10
        mock_settings.database_config.max_overflow = 5
        mock_settings.database_config.pool_timeout = 30.0
        mock_settings.database_config.pool_pre_ping = True
        mock_settings.database_config.echo = False

        mocker.patch(
            "src.infrastructure.database.session.get_settings",
            return_value=mock_settings,
        )

        # Mock engine
        mock_engine = AsyncMock(spec=AsyncEngine)
        mocker.patch(
            "src.infrastructure.database.session.create_async_engine",
            return_value=mock_engine,
        )

        # Mock session
        mock_session = AsyncMock(spec=AsyncSession)
        mock_factory = AsyncMock()
        mock_factory.__aenter__.return_value = mock_session
        mock_factory.__aexit__.return_value = None

        mock_sessionmaker_instance = MagicMock()
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

    def test_reset_method(self, mocker: MagicMock) -> None:
        """Test that reset method clears all state."""
        # Mock create_database_engine to return a different engine each time
        mock_engine1 = MagicMock(spec=AsyncEngine)
        mock_engine2 = MagicMock(spec=AsyncEngine)
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
