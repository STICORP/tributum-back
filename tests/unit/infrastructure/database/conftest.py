"""Fixtures for database infrastructure unit tests."""

from collections.abc import AsyncGenerator, Generator
from contextlib import asynccontextmanager
from typing import cast

import pytest
from pytest_mock import MockerFixture, MockType
from sqlalchemy import String
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import BaseModel
from src.infrastructure.database.repository import BaseRepository
from src.infrastructure.database.session import _DatabaseManager


@pytest.fixture
def concrete_base_model_class() -> type[BaseModel]:
    """Create a concrete test model class that inherits from BaseModel.

    Returns:
        type[BaseModel]: A concrete model class for testing.
    """

    class TestModel(BaseModel):
        """Concrete test model for testing BaseModel functionality."""

        __tablename__ = "test_model"

    return TestModel


@pytest.fixture
def mock_base_model_instance(mocker: MockerFixture) -> MockType:
    """Mock BaseModel instance with test data.

    Args:
        mocker: Pytest mocker fixture.

    Returns:
        MockType: Mock instance with test attributes.
    """
    instance = mocker.Mock()
    instance.id = 123
    instance.__class__.__name__ = "TestModel"

    # Configure the mock to return the correct repr string
    def mock_repr() -> str:
        return f"<{instance.__class__.__name__}(id={instance.id})>"

    instance.__repr__ = mocker.Mock(return_value=mock_repr())

    return cast("MockType", instance)


@pytest.fixture
def mock_async_engine(mocker: MockerFixture) -> MockType:
    """Mock AsyncEngine with required methods.

    Args:
        mocker: Pytest mocker fixture.

    Returns:
        MockType: Mock AsyncEngine with connect, dispose methods.
    """
    engine = mocker.Mock(spec=AsyncEngine)
    engine.dispose = mocker.AsyncMock()

    # Mock sync_engine for event listeners
    engine.sync_engine = mocker.Mock()

    # Mock connect method to return async context manager
    mock_connection = mocker.AsyncMock()
    mock_connection.__aenter__ = mocker.AsyncMock(return_value=mock_connection)
    mock_connection.__aexit__ = mocker.AsyncMock(return_value=None)

    # Mock execute method for health check
    mock_result = mocker.Mock()
    mock_result.scalar = mocker.Mock(return_value=1)
    mock_connection.execute = mocker.AsyncMock(return_value=mock_result)

    engine.connect = mocker.Mock(return_value=mock_connection)

    return cast("MockType", engine)


@pytest.fixture
def mock_async_session(mocker: MockerFixture) -> MockType:
    """Mock AsyncSession with lifecycle methods.

    Args:
        mocker: Pytest mocker fixture.

    Returns:
        MockType: Mock AsyncSession with commit, rollback, close methods
            and context manager protocol.
    """
    session = mocker.Mock(spec=AsyncSession)
    session.commit = mocker.AsyncMock()
    session.rollback = mocker.AsyncMock()
    session.close = mocker.AsyncMock()
    session.execute = mocker.AsyncMock()

    # Configure context manager protocol
    session.__aenter__ = mocker.AsyncMock(return_value=session)
    session.__aexit__ = mocker.AsyncMock(return_value=None)

    return cast("MockType", session)


@pytest.fixture
def mock_session_factory(
    mocker: MockerFixture, mock_async_session: MockType
) -> MockType:
    """Mock async_sessionmaker.

    Args:
        mocker: Pytest mocker fixture.
        mock_async_session: Mock async session fixture.

    Returns:
        MockType: Mock async_sessionmaker that returns mock sessions.
    """
    factory = mocker.Mock()
    factory.return_value = mock_async_session
    factory.__call__ = mocker.Mock(return_value=mock_async_session)

    return cast("MockType", factory)


@pytest.fixture
def mock_execution_context(mocker: MockerFixture) -> MockType:
    """Mock SQLAlchemy ExecutionContext.

    Args:
        mocker: Pytest mocker fixture.

    Returns:
        MockType: Mock ExecutionContext for event listener tests.
    """
    context = mocker.Mock()
    context.execution_options = {}
    context.cursor = mocker.Mock()

    return cast("MockType", context)


@pytest.fixture
def mock_database_connection(mocker: MockerFixture) -> MockType:
    """Mock database connection with query execution.

    Args:
        mocker: Pytest mocker fixture.

    Returns:
        MockType: Mock connection with execute method.
    """
    connection = mocker.Mock()
    connection.execute = mocker.AsyncMock()

    return cast("MockType", connection)


@pytest.fixture
def mock_query_result(mocker: MockerFixture) -> MockType:
    """Mock database query result.

    Args:
        mocker: Pytest mocker fixture.

    Returns:
        MockType: Mock result with scalar method.
    """
    result = mocker.Mock()
    result.scalar = mocker.Mock(return_value=1)
    result.scalars = mocker.Mock()

    return cast("MockType", result)


@pytest.fixture
def database_manager_fixture() -> Generator[_DatabaseManager]:
    """Clean database manager instance for testing.

    Returns:
        _DatabaseManager: Fresh _DatabaseManager instance, resets after test.
    """
    manager = _DatabaseManager()
    yield manager
    # Reset state after test
    manager.reset()


@pytest.fixture
def mock_create_async_engine(
    mocker: MockerFixture, mock_async_engine: MockType
) -> MockType:
    """Mock create_async_engine function.

    Args:
        mocker: Pytest mocker fixture.
        mock_async_engine: Mock async engine fixture.

    Returns:
        MockType: Mock create_async_engine function.
    """
    return mocker.patch(
        "src.infrastructure.database.session.create_async_engine",
        return_value=mock_async_engine,
    )


@pytest.fixture
def mock_async_sessionmaker(
    mocker: MockerFixture, mock_session_factory: MockType
) -> MockType:
    """Mock async_sessionmaker class.

    Args:
        mocker: Pytest mocker fixture.
        mock_session_factory: Mock session factory fixture.

    Returns:
        MockType: Mock async_sessionmaker class.
    """
    return mocker.patch(
        "src.infrastructure.database.session.async_sessionmaker",
        return_value=mock_session_factory,
    )


@pytest.fixture
def mock_event_listen(mocker: MockerFixture) -> MockType:
    """Mock SQLAlchemy event.listen function.

    Args:
        mocker: Pytest mocker fixture.

    Returns:
        MockType: Mock event.listen function.
    """
    return mocker.patch("src.infrastructure.database.session.event.listen")


@pytest.fixture
def mock_time(mocker: MockerFixture) -> MockType:
    """Mock time.time function for performance testing.

    Args:
        mocker: Pytest mocker fixture.

    Returns:
        MockType: Mock time.time function.
    """
    return mocker.patch("src.infrastructure.database.session.time.time")


@pytest.fixture
def mock_sql_text(mocker: MockerFixture) -> MockType:
    """Mock SQLAlchemy text function.

    Args:
        mocker: Pytest mocker fixture.

    Returns:
        MockType: Mock text function.
    """
    mock_text_result = mocker.Mock()
    return mocker.patch(
        "src.infrastructure.database.session.text", return_value=mock_text_result
    )


@pytest.fixture
def mock_sanitize_sql_params(mocker: MockerFixture) -> MockType:
    """Mock sanitize_sql_params function.

    Args:
        mocker: Pytest mocker fixture.

    Returns:
        MockType: Mock sanitize_sql_params function.
    """

    def mock_sanitize(params: object) -> dict[str, str]:
        return {"sanitized": str(params)}

    return mocker.patch(
        "src.infrastructure.database.session.sanitize_sql_params",
        side_effect=mock_sanitize,
    )


@pytest.fixture
def mock_database_manager(mocker: MockerFixture) -> MockType:
    """Mock the singleton _db_manager instance.

    Args:
        mocker: Pytest mocker fixture.

    Returns:
        MockType: Mock _DatabaseManager instance.
    """
    manager = mocker.Mock(spec=_DatabaseManager)
    manager.get_engine = mocker.Mock()
    manager.get_session_factory = mocker.Mock()
    manager.close = mocker.AsyncMock()
    manager.reset = mocker.Mock()

    result: MockType = mocker.patch(
        "src.infrastructure.database.session._db_manager", manager
    )
    return result


@pytest.fixture
def mock_async_session_for_dependencies(mocker: MockerFixture) -> MockType:
    """Mock AsyncSession for dependency injection tests.

    Provides a mock AsyncSession object that mimics SQLAlchemy's AsyncSession
    behavior specifically for testing FastAPI dependency injection.

    Args:
        mocker: Pytest mocker fixture.

    Returns:
        MockType: Mock AsyncSession with proper type annotations.
    """
    session = mocker.AsyncMock(spec=AsyncSession)
    session.commit = mocker.AsyncMock()
    session.rollback = mocker.AsyncMock()
    session.close = mocker.AsyncMock()
    session.execute = mocker.AsyncMock()
    session.scalar = mocker.AsyncMock()
    session.scalars = mocker.AsyncMock()
    session.get = mocker.AsyncMock()
    session.merge = mocker.AsyncMock()
    session.flush = mocker.AsyncMock()
    session.refresh = mocker.AsyncMock()
    session.expunge = mocker.AsyncMock()
    session.is_active = True
    session.info = {}

    return cast("MockType", session)


@pytest.fixture
def mock_get_async_session_for_tests(
    mock_async_session_for_dependencies: MockType,
) -> MockType:
    """Create a mock get_async_session function that returns an async context manager.

    This fixture provides a reusable mock for the get_async_session function
    that properly yields a mock session through an async context manager.

    Args:
        mocker: Pytest mocker fixture.
        mock_async_session_for_dependencies: Mock async session for dependencies.

    Returns:
        MockType: A function that returns an async context manager yielding a session.
    """

    @asynccontextmanager
    async def mock_get_async_session() -> AsyncGenerator[AsyncSession]:
        yield mock_async_session_for_dependencies

    return cast("MockType", mock_get_async_session)


@pytest.fixture(scope="session")
def mock_model_class() -> type[BaseModel]:
    """Create a concrete test model class for repository testing.

    Returns:
        type[BaseModel]: A concrete model class with test attributes.
    """

    class TestRepositoryModel(BaseModel):
        """Concrete test model for repository testing."""

        __tablename__ = "test_repo_model"

        name: Mapped[str] = mapped_column(String, nullable=True)
        status: Mapped[str] = mapped_column(String, nullable=True)
        email: Mapped[str] = mapped_column(String, nullable=True)

    # Set the __name__ attribute to match expected logging
    TestRepositoryModel.__name__ = "TestModel"

    return TestRepositoryModel


@pytest.fixture
def mock_repository_query_result(mocker: MockerFixture) -> MockType:
    """Mock query execution results for repository test scenarios.

    Args:
        mocker: Pytest mocker fixture.

    Returns:
        MockType: Mock with scalar_one_or_none, scalars, scalar methods.
    """
    result = mocker.Mock()
    result.scalar_one_or_none = mocker.Mock(return_value=None)
    result.scalar = mocker.Mock(return_value=0)
    result.scalars = mocker.Mock()
    result.scalars.return_value.all = mocker.Mock(return_value=[])

    return cast("MockType", result)


@pytest.fixture
def sample_model_instances(mock_model_class: type[BaseModel]) -> list[BaseModel]:
    """Provide test model instances with various configurations.

    Args:
        mock_model_class: Concrete model class fixture.

    Returns:
        list[BaseModel]: List of model instances with different id values
            and attributes.
    """
    instances = []
    for i in range(1, 6):
        instance = mock_model_class()
        instance.id = i
        if hasattr(instance, "name"):
            instance.name = f"Test{i}"
        if hasattr(instance, "status"):
            instance.status = "active" if i % 2 == 0 else "inactive"
        if hasattr(instance, "email"):
            instance.email = f"test{i}@example.com"
        instances.append(instance)

    return instances


@pytest.fixture
def repository_factory() -> MockType:
    """Factory fixture to create BaseRepository instances with mocked dependencies.

    Returns:
        MockType: Function that creates repositories with specified model class.
    """

    def _create_repository(
        session: MockType, model_class: type[BaseModel]
    ) -> BaseRepository[BaseModel]:
        """Create a repository instance with given session and model class."""
        return BaseRepository(session, model_class)

    return cast("MockType", _create_repository)


@pytest.fixture
def create_mock_get_async_session_factory(
    mocker: MockerFixture,
) -> MockType:
    """Factory for creating mock get_async_session functions with different behaviors.

    This fixture provides a factory function that can create mock get_async_session
    functions with custom behavior for testing different scenarios.

    Args:
        mocker: Pytest mocker fixture.

    Returns:
        MockType: A factory function for creating mock get_async_session functions.
    """

    def factory(
        session: MockType | None = None,
        raise_on_enter: type[Exception] | None = None,
        raise_on_exit: type[Exception] | None = None,
        raise_message: str = "Test error",
    ) -> MockType:
        """Create a mock get_async_session with custom behavior.

        Args:
            session: The session to yield (if None, creates a mock).
            raise_on_enter: Exception type to raise on __aenter__.
            raise_on_exit: Exception type to raise on __aexit__.
            raise_message: Message for the raised exception.

        Returns:
            Mock async context manager.
        """
        if session is None:
            session = mocker.AsyncMock(spec=AsyncSession)

        @asynccontextmanager
        async def mock_get_async_session() -> AsyncGenerator[AsyncSession]:
            if raise_on_enter:
                raise raise_on_enter(raise_message)
            yield session
            if raise_on_exit:
                raise raise_on_exit(raise_message)

        return cast("MockType", mock_get_async_session)

    return cast("MockType", factory)


@pytest.fixture
def mock_get_async_session_context(
    mocker: MockerFixture, mock_async_session_for_dependencies: MockType
) -> MockType:
    """Mock the get_async_session context manager from session module.

    Creates an async context manager that yields the mock_async_session,
    supporting async with syntax for dependency injection tests.

    Args:
        mocker: Pytest mocker fixture.
        mock_async_session_for_dependencies: Mock async session for dependencies.

    Returns:
        MockType: Mock that can be used with pytest_mock's patch.
    """

    async def mock_context_manager() -> AsyncGenerator[AsyncSession]:
        """Mock async context manager for get_async_session."""
        yield mock_async_session_for_dependencies

    return mocker.patch(
        "src.infrastructure.database.dependencies.get_async_session",
        return_value=mock_context_manager(),
    )
