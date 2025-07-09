"""Fixtures for database infrastructure unit tests."""

from collections.abc import Generator
from typing import cast

import pytest
from pytest_mock import MockerFixture, MockType
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from src.infrastructure.database.base import BaseModel
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
