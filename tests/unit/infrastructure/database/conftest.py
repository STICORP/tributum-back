"""Fixtures for database infrastructure unit tests."""

from typing import cast

import pytest
from pytest_mock import MockerFixture, MockType

from src.infrastructure.database.base import BaseModel


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
