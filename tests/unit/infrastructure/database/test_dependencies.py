"""Unit tests for database dependencies."""

import types
from typing import Annotated, get_args, get_origin

import pytest
import pytest_check
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.dependencies import DatabaseSession, get_db


@pytest.mark.unit
class TestGetDb:
    """Test cases for get_db dependency function."""

    @pytest.mark.asyncio
    async def test_get_db_provides_session(self, mocker: MockerFixture) -> None:
        """Test that get_db yields a database session."""
        # Create a mock session
        mock_session = mocker.MagicMock(spec=AsyncSession)

        # Mock the get_async_session context manager
        mock_get_async_session = mocker.patch(
            "src.infrastructure.database.dependencies.get_async_session"
        )

        # Configure the mock to be an async context manager
        mock_get_async_session.return_value.__aenter__.return_value = mock_session
        mock_get_async_session.return_value.__aexit__.return_value = None

        # Test the dependency
        async for session in get_db():
            # Verify we got the mock session
            assert session is mock_session

        # Verify get_async_session was called
        mock_get_async_session.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_db_logs_lifecycle(self, mocker: MockerFixture) -> None:
        """Test that get_db logs session lifecycle events."""
        # Create a mock session
        mock_session = mocker.MagicMock(spec=AsyncSession)

        # Mock the get_async_session context manager
        mock_get_async_session = mocker.patch(
            "src.infrastructure.database.dependencies.get_async_session"
        )
        mock_get_async_session.return_value.__aenter__.return_value = mock_session
        mock_get_async_session.return_value.__aexit__.return_value = None

        # Mock the logger
        mock_logger = mocker.patch("src.infrastructure.database.dependencies.logger")

        # Test the dependency
        async for _ in get_db():
            # Verify initial log
            mock_logger.debug.assert_any_call("Providing database session for request")

        # Verify completion log
        mock_logger.debug.assert_any_call("Database session dependency completed")
        # Should be exactly 2 debug calls
        assert mock_logger.debug.call_count == 2

    @pytest.mark.asyncio
    async def test_get_db_handles_exception(self, mocker: MockerFixture) -> None:
        """Test that get_db properly propagates exceptions."""
        # Create exception to raise
        test_exception = RuntimeError("Test database error")

        # Mock the get_async_session to raise during context manager
        mock_get_async_session = mocker.patch(
            "src.infrastructure.database.dependencies.get_async_session"
        )

        # Configure context manager to raise on enter
        mock_get_async_session.return_value.__aenter__.side_effect = test_exception

        # Test that exception is propagated
        with pytest.raises(RuntimeError, match="Test database error"):
            async for _ in get_db():
                pass  # pragma: no cover - should not reach here

    @pytest.mark.asyncio
    async def test_get_db_cleanup_on_generator_close(
        self, mocker: MockerFixture
    ) -> None:
        """Test that get_db properly cleans up when generator is closed early."""
        # Create a mock session
        mock_session = mocker.MagicMock(spec=AsyncSession)

        # Track if exit was called
        exit_called = False

        # Create a proper async context manager
        class MockAsyncContextManager:
            def __init__(self, session: AsyncSession) -> None:
                self._session = session

            async def __aenter__(self) -> AsyncSession:
                return self._session

            async def __aexit__(
                self,
                exc_type: type[BaseException] | None,
                exc_val: BaseException | None,
                exc_tb: types.TracebackType | None,
            ) -> None:
                nonlocal exit_called
                exit_called = True
                # Use all parameters to satisfy vulture
                _ = (exc_type, exc_val, exc_tb)

        # Mock get_async_session to return our context manager instance
        mocker.patch(
            "src.infrastructure.database.dependencies.get_async_session",
            return_value=MockAsyncContextManager(mock_session),
        )

        # Mock the logger
        mock_logger = mocker.patch("src.infrastructure.database.dependencies.logger")

        # Create generator but close it early
        gen = get_db()
        session = await gen.__anext__()

        # Verify we got the session
        assert session is mock_session
        mock_logger.debug.assert_called_with("Providing database session for request")

        # Close the generator without exhausting it
        await gen.aclose()

        # When a generator is closed early, the finally block is executed
        # but we won't see the "completed" log because we're not exiting normally
        # Verify that the context manager's exit was still called
        assert exit_called, "Context manager __aexit__ should have been called"


@pytest.mark.unit
class TestDatabaseSessionType:
    """Test cases for DatabaseSession type alias."""

    def test_database_session_type_alias(self) -> None:
        """Test that DatabaseSession is properly annotated."""
        # DatabaseSession should be an Annotated type
        assert get_origin(DatabaseSession) is Annotated

        # Get the args (AsyncSession and Depends)
        args = get_args(DatabaseSession)
        assert len(args) == 2
        assert args[0] is AsyncSession

        # Second arg should be Depends instance
        depends_instance = args[1]
        assert isinstance(depends_instance, type(Depends(lambda: None)))
        assert depends_instance.dependency is get_db

    @pytest.mark.asyncio
    async def test_database_session_usage_in_route(self, mocker: MockerFixture) -> None:
        """Test that DatabaseSession can be used in a FastAPI route."""
        # Create a test app
        app = FastAPI()

        # Track if our route was called with the session
        route_called = False
        received_session = None

        @app.get("/test")
        async def test_route(db: DatabaseSession) -> dict[str, str]:
            nonlocal route_called, received_session
            route_called = True
            received_session = db
            return {"status": "ok"}

        # Mock the session
        mock_session = mocker.MagicMock(spec=AsyncSession)
        mock_get_async_session = mocker.patch(
            "src.infrastructure.database.dependencies.get_async_session"
        )
        mock_get_async_session.return_value.__aenter__.return_value = mock_session
        mock_get_async_session.return_value.__aexit__.return_value = None

        # Test the route
        with TestClient(app) as client:
            response = client.get("/test")

        # Verify the route was called and received the session
        assert route_called
        assert received_session is mock_session
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


@pytest.mark.unit
class TestDependencyIntegration:
    """Test integration aspects of database dependencies."""

    @pytest.mark.asyncio
    async def test_multiple_concurrent_dependencies(
        self, mocker: MockerFixture
    ) -> None:
        """Test that multiple concurrent get_db calls work independently."""
        # Create distinct mock sessions
        mock_session1 = mocker.MagicMock(spec=AsyncSession)
        mock_session1.id = "session1"
        mock_session2 = mocker.MagicMock(spec=AsyncSession)
        mock_session2.id = "session2"

        # Create a list of sessions to return
        sessions_to_return = [mock_session1, mock_session2]
        current_index = 0

        # Create a proper async context manager class
        class MockAsyncContextManager:
            def __init__(self, session: AsyncSession) -> None:
                self.session = session

            async def __aenter__(self) -> AsyncSession:
                return self.session

            async def __aexit__(
                self,
                exc_type: type[BaseException] | None,
                exc_val: BaseException | None,
                exc_tb: types.TracebackType | None,
            ) -> None:
                # Use all parameters to satisfy vulture
                _ = (exc_type, exc_val, exc_tb)

        # Mock get_async_session to return different context managers
        def get_next_context_manager() -> MockAsyncContextManager:
            nonlocal current_index
            session = sessions_to_return[current_index]
            current_index += 1
            return MockAsyncContextManager(session)

        mocker.patch(
            "src.infrastructure.database.dependencies.get_async_session",
            side_effect=get_next_context_manager,
        )

        # Get two sessions
        sessions = []
        async for session in get_db():
            sessions.append(session)
            break

        async for session in get_db():
            sessions.append(session)
            break

        # Verify we got different sessions
        assert len(sessions) == 2
        assert sessions[0] is mock_session1
        assert sessions[1] is mock_session2

    @pytest.mark.asyncio
    async def test_get_db_with_real_session_factory(
        self, mocker: MockerFixture
    ) -> None:
        """Test get_db with a more realistic async session factory mock."""
        # Create a mock that behaves like a real async session
        mock_session = mocker.AsyncMock(spec=AsyncSession)
        mock_session.is_active = True
        mock_session.bind = mocker.MagicMock()

        # Create async context manager that behaves like get_async_session
        class MockAsyncContextManager:
            def __init__(self, session: AsyncSession) -> None:
                self._session = session

            async def __aenter__(self) -> AsyncSession:
                return self._session

            async def __aexit__(
                self,
                exc_type: type[BaseException] | None,
                exc_val: BaseException | None,
                exc_tb: types.TracebackType | None,
            ) -> None:
                # Use exc_val and exc_tb to satisfy vulture
                _ = (exc_val, exc_tb)
                if exc_type:
                    await self._session.rollback()
                else:
                    await self._session.commit()
                await self._session.close()

        # Mock get_async_session to return our context manager
        mocker.patch(
            "src.infrastructure.database.dependencies.get_async_session",
            return_value=MockAsyncContextManager(mock_session),
        )

        # Use the dependency
        async for session in get_db():
            # Verify session attributes
            with pytest_check.check:
                assert session.is_active is True
            with pytest_check.check:
                assert hasattr(session, "bind")
            with pytest_check.check:
                assert hasattr(session, "commit")
            with pytest_check.check:
                assert hasattr(session, "rollback")
            with pytest_check.check:
                assert hasattr(session, "close")

        # Verify cleanup was called
        mock_session.commit.assert_called_once()
        mock_session.close.assert_called_once()
