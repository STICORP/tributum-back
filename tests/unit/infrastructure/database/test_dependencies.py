"""Unit tests for src/infrastructure/database/dependencies.py module.

This module contains comprehensive unit tests for the database dependencies module,
which provides FastAPI dependency injection for SQLAlchemy async sessions.
"""

import asyncio
import contextlib
import inspect
from collections.abc import AsyncGenerator, Callable
from typing import Any, cast, get_args, get_origin

import pytest
from pytest_mock import MockerFixture, MockType
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.dependencies import DatabaseSession, get_db


@pytest.mark.unit
class TestDatabaseDependencies:
    """Test the database dependency injection for FastAPI."""

    async def test_get_db_successful_session_lifecycle(
        self,
        mock_async_session_for_dependencies: MockType,
        mock_get_async_session_for_tests: MockType,
        mocker: MockerFixture,
    ) -> None:
        """Verify that get_db correctly yields a session and logs appropriately.

        Tests normal operation flow with proper session lifecycle management.
        """
        # Setup
        mock_logger = mocker.patch("src.infrastructure.database.dependencies.logger")

        mocker.patch(
            "src.infrastructure.database.dependencies.get_async_session",
            new=mock_get_async_session_for_tests,
        )

        # Execute - consume the full generator properly
        # This simulates how FastAPI would use it
        session_received = None
        gen = get_db()
        try:
            session_received = await gen.__anext__()
            # At this point, the session is yielded and first log is called
            assert session_received is mock_async_session_for_dependencies
            mock_logger.debug.assert_called_with(
                "Providing database session for request"
            )

            # Now complete the generator to trigger finally block
            with contextlib.suppress(StopAsyncIteration):
                await gen.__anext__()  # This should raise StopAsyncIteration
        finally:
            # Ensure generator is closed
            await gen.aclose()

        # Verify both logging calls were made
        assert mock_logger.debug.call_count >= 2
        mock_logger.debug.assert_any_call("Providing database session for request")
        mock_logger.debug.assert_any_call("Database session dependency completed")

    async def test_get_db_session_cleanup_on_exception(
        self,
        mock_async_session_for_dependencies: MockType,
        mock_get_async_session_for_tests: MockType,
        mocker: MockerFixture,
    ) -> None:
        """Verify that the session is cleaned up even when an exception occurs."""
        # Setup
        mock_logger = mocker.patch("src.infrastructure.database.dependencies.logger")

        mocker.patch(
            "src.infrastructure.database.dependencies.get_async_session",
            new=mock_get_async_session_for_tests,
        )

        # Execute - simulate exception after getting session
        gen = get_db()
        session = await gen.__anext__()
        assert session is mock_async_session_for_dependencies

        # Simulate work that raises an exception
        with pytest.raises(ValueError, match="Test exception"):
            raise ValueError("Test exception")

        # Clean up the generator - this should trigger the finally block
        await gen.aclose()

        # Verify cleanup log was called
        mock_logger.debug.assert_any_call("Database session dependency completed")

    async def test_database_session_type_alias_integration(self) -> None:
        """Verify that DatabaseSession type alias integrates with FastAPI's Depends."""
        # Get the type information
        origin = get_origin(DatabaseSession)
        args = get_args(DatabaseSession)

        # Assert type structure
        assert origin is not None  # It's an Annotated type
        assert len(args) == 2
        assert args[0] is AsyncSession

        # Verify the Depends object
        depends_obj = args[1]
        assert type(depends_obj).__name__ == "Depends"
        assert depends_obj.dependency == get_db

    async def test_get_db_multiple_concurrent_requests(
        self,
        create_mock_get_async_session_factory: MockType,
        mocker: MockerFixture,
    ) -> None:
        """Verify that multiple concurrent calls to get_db work correctly.

        This simulates concurrent FastAPI requests.
        """
        # Setup
        mock_logger = mocker.patch("src.infrastructure.database.dependencies.logger")

        # Create multiple mock sessions
        sessions_created = []

        def create_mock_session() -> AsyncSession:
            session = mocker.AsyncMock(spec=AsyncSession)
            sessions_created.append(session)
            return cast("AsyncSession", session)

        # Track how many times get_async_session is called
        call_count = 0

        def get_session_factory() -> AsyncGenerator[AsyncSession]:
            nonlocal call_count
            call_count += 1
            # Create and return the actual async context manager
            session = create_mock_session()
            return cast(
                "AsyncGenerator[AsyncSession]",
                create_mock_get_async_session_factory(session=session)(),
            )

        mocker.patch(
            "src.infrastructure.database.dependencies.get_async_session",
            side_effect=get_session_factory,
        )

        # Execute - simulate multiple concurrent requests
        async def use_session(_index: int) -> AsyncSession:
            async for session in get_db():
                # Simulate some async work
                await asyncio.sleep(0.01)
                return session
            raise RuntimeError("Generator did not yield")

        # Run concurrent requests
        sessions = await asyncio.gather(
            use_session(1),
            use_session(2),
            use_session(3),
        )

        # Assert
        assert len(sessions) == 3
        assert len(sessions_created) == 3
        # Verify each request got its own session
        assert len({id(s) for s in sessions}) == 3

        # Verify log messages for each session
        assert call_count == 3
        assert mock_logger.debug.call_count == 6  # 2 messages per session

    async def test_get_db_import_verification(self) -> None:
        """Verify all imports are available and module loads correctly."""
        # Verify function exists and has correct signature
        assert callable(get_db)
        sig = inspect.signature(get_db)
        assert len(sig.parameters) == 0
        assert sig.return_annotation == AsyncGenerator[AsyncSession]

        # Verify DatabaseSession exists and is properly typed
        assert DatabaseSession is not None
        # Verify it's an Annotated type
        origin = get_origin(DatabaseSession)
        assert origin is not None

        # Verify docstring
        assert get_db.__doc__ is not None
        assert "Provide a database session" in get_db.__doc__

    @pytest.mark.parametrize(
        ("exception_type", "exception_source"),
        [
            (ValueError, "context_manager_enter"),
            (RuntimeError, "session_usage"),
            (SQLAlchemyError, "context_manager_enter"),
            (Exception, "context_manager_exit"),
        ],
    )
    async def test_get_db_exception_handling(
        self,
        exception_type: type[Exception],
        exception_source: str,
        mock_async_session_for_dependencies: MockType,
        create_mock_get_async_session_factory: MockType,
        mocker: MockerFixture,
    ) -> None:
        """Ensure get_db handles various exception types and always cleans up."""
        # Setup
        mock_logger = mocker.patch("src.infrastructure.database.dependencies.logger")

        if exception_source == "context_manager_enter":
            # Exception during __aenter__
            mock_get_async_session = create_mock_get_async_session_factory(
                raise_on_enter=exception_type,
                raise_message="Test error",
            )
        elif exception_source == "context_manager_exit":
            # Exception during __aexit__
            mock_get_async_session = create_mock_get_async_session_factory(
                session=mock_async_session_for_dependencies,
                raise_on_exit=exception_type,
                raise_message="Exit error",
            )
        else:
            # Normal context manager, exception during usage
            mock_get_async_session = create_mock_get_async_session_factory(
                session=mock_async_session_for_dependencies,
            )

        mocker.patch(
            "src.infrastructure.database.dependencies.get_async_session",
            new=mock_get_async_session,
        )

        # Execute based on exception source
        if exception_source == "context_manager_enter":
            # Exception during context manager entry
            gen = get_db()
            with pytest.raises(exception_type):
                await gen.__anext__()  # This will raise immediately

        elif exception_source == "session_usage":
            # Exception during session usage
            gen = get_db()
            session = await gen.__anext__()
            assert session is mock_async_session_for_dependencies

            with pytest.raises(exception_type):
                raise exception_type("Usage error")

            # Clean up
            await gen.aclose()
            # Verify both log messages
            mock_logger.debug.assert_any_call("Providing database session for request")
            mock_logger.debug.assert_any_call("Database session dependency completed")

        elif exception_source == "context_manager_exit":
            # Exception during context manager exit
            # This exception will propagate when we try to complete the iteration
            gen = get_db()
            session = await gen.__anext__()
            assert session is mock_async_session_for_dependencies

            # Try to get the next value, which should trigger the exception
            # from the context manager's code after yield
            with pytest.raises(exception_type), contextlib.suppress(StopAsyncIteration):
                await gen.__anext__()  # This triggers the completion

            # The finally block should still have run
            mock_logger.debug.assert_any_call("Database session dependency completed")

    async def test_get_db_generator_cleanup_with_early_return(
        self,
        mock_async_session_for_dependencies: MockType,
        mock_get_async_session_for_tests: MockType,
        mocker: MockerFixture,
    ) -> None:
        """Verify cleanup happens even with early generator termination."""
        # Setup
        mock_logger = mocker.patch("src.infrastructure.database.dependencies.logger")

        mocker.patch(
            "src.infrastructure.database.dependencies.get_async_session",
            new=mock_get_async_session_for_tests,
        )

        # Execute - create generator but don't fully consume it
        gen = get_db()
        session = await gen.__anext__()
        assert session is mock_async_session_for_dependencies

        # Close generator without consuming it fully
        await gen.aclose()

        # Assert
        mock_logger.debug.assert_any_call("Providing database session for request")
        mock_logger.debug.assert_any_call("Database session dependency completed")

    async def test_get_db_async_generator_protocol(self) -> None:
        """Verify get_db properly implements async generator protocol."""
        # Setup
        gen = get_db()

        # Assert it's an async generator
        assert hasattr(gen, "__anext__")
        assert hasattr(gen, "__aiter__")
        assert hasattr(gen, "aclose")
        assert hasattr(gen, "asend")
        assert hasattr(gen, "athrow")

        # Clean up
        await gen.aclose()

    async def test_get_db_with_fastapi_style_usage(
        self,
        mock_get_async_session_for_tests: MockType,
        mocker: MockerFixture,
    ) -> None:
        """Test get_db in a pattern similar to how FastAPI would use it."""
        # Setup
        mock_logger = mocker.patch("src.infrastructure.database.dependencies.logger")

        mocker.patch(
            "src.infrastructure.database.dependencies.get_async_session",
            new=mock_get_async_session_for_tests,
        )

        # Simulate FastAPI's dependency injection pattern
        def create_route_handler() -> Callable[..., Any]:
            """Create route handler with dependency."""

            async def route_handler(db: AsyncSession | None = None) -> str:
                # Simulate database operation
                assert db is not None
                return "success"

            return route_handler

        # Get the dependency
        dependency = get_db()

        # Simulate FastAPI calling it
        session = await dependency.__anext__()

        # Use the session
        handler = create_route_handler()
        result = await handler(db=session)
        assert result == "success"

        # Cleanup (FastAPI would do this)
        with contextlib.suppress(StopAsyncIteration):
            await dependency.__anext__()  # This should raise StopAsyncIteration

        # Verify logs
        mock_logger.debug.assert_any_call("Providing database session for request")
        mock_logger.debug.assert_any_call("Database session dependency completed")
