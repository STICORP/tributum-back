"""Fixtures for API utils tests."""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, cast
from uuid import UUID

import pytest
from pydantic import BaseModel, Field
from pytest_mock import MockerFixture, MockType


class SimpleModel(BaseModel):
    """Simple Pydantic model for testing."""

    name: str
    age: int
    active: bool


class ModelWithOptional(BaseModel):
    """Model with optional fields and defaults."""

    required_field: str
    optional_field: str | None = None
    with_default: int = 42


class ModelWithDateTime(BaseModel):
    """Model with datetime and UUID fields."""

    id: UUID
    created_at: datetime
    updated_at: datetime | None = None


class NestedInnerModel(BaseModel):
    """Inner model for nesting."""

    value: str
    count: int


class ModelWithNested(BaseModel):
    """Model with nested Pydantic models."""

    title: str
    inner: NestedInnerModel
    items: list[NestedInnerModel] = Field(default_factory=list)


class ComplexModel(BaseModel):
    """Model with complex field types."""

    tags: list[str]
    metadata: dict[str, Any]
    scores: list[float]
    settings: dict[str, bool]


@pytest.fixture
def sample_dict_data() -> list[dict[str, Any]]:
    """Provide various dictionary structures for comprehensive testing.

    Returns:
        list[dict[str, Any]]: List of test dictionaries.
    """
    return [
        {},  # Empty dict
        {"key": "value", "number": 42},  # Simple key-value pairs
        {"nested": {"inner": {"deep": "value"}}},  # Nested dictionaries
        {  # Lists and mixed types
            "list": [1, 2, 3],
            "mixed": {"str": "text", "int": 123, "bool": True},
        },
        {  # Special characters in keys/values
            "key with spaces": "value",
            "unicode": "🚀",
            "escaped": '"quoted"',
        },
    ]


@pytest.fixture
def sample_pydantic_models() -> list[BaseModel]:
    """Various Pydantic model instances for model_dump testing.

    Returns:
        list[BaseModel]: List of Pydantic model instances.
    """
    return [
        # Simple model with basic fields
        SimpleModel(name="John Doe", age=30, active=True),
        # Model with optional fields and defaults
        ModelWithOptional(required_field="test", optional_field="present"),
        ModelWithOptional(required_field="test"),  # optional_field is None
        # Model with datetime and UUID fields
        ModelWithDateTime(
            id=UUID("12345678-1234-5678-1234-567812345678"),
            created_at=datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
            updated_at=datetime(2024, 1, 2, 12, 0, 0, tzinfo=UTC),
        ),
        # Model with nested Pydantic models
        ModelWithNested(
            title="Parent",
            inner=NestedInnerModel(value="nested", count=5),
            items=[
                NestedInnerModel(value="item1", count=1),
                NestedInnerModel(value="item2", count=2),
            ],
        ),
        # Model with complex field types
        ComplexModel(
            tags=["python", "fastapi", "testing"],
            metadata={"version": "1.0", "author": "test"},
            scores=[0.95, 0.87, 0.92],
            settings={"debug": True, "verbose": False},
        ),
    ]


@pytest.fixture
def mock_orjson_module(mocker: MockerFixture) -> MockType:
    """Provide a mock orjson module with configurable behavior.

    Args:
        mocker: Pytest mocker fixture.

    Returns:
        MockType: Mock orjson module.
    """
    mock_orjson = mocker.Mock()
    mock_orjson.dumps = mocker.Mock(return_value=b'{"mocked": "json"}')
    mock_orjson.OPT_SORT_KEYS = 1  # Mock the constant
    return cast("MockType", mock_orjson)


@pytest.fixture
def sample_content_types() -> list[Any]:
    """Various content types for comprehensive render testing.

    Returns:
        list[Any]: List of various content types.
    """
    return [
        None,
        "",  # Empty string
        "Hello, World!",  # Normal string
        "Unicode: 🌍🚀💻",  # Unicode string
        42,  # Integer
        3.14159,  # Float
        Decimal("123.45"),  # Decimal
        [],  # Empty list
        [1, "two", 3.0, True, None],  # Mixed content list
        ("tuple", "values", 123),  # Tuple
        True,  # Boolean True
        False,  # Boolean False
        {  # Complex nested structure
            "users": [
                {"id": 1, "name": "Alice"},
                {"id": 2, "name": "Bob"},
            ],
            "metadata": {
                "total": 2,
                "page": 1,
                "per_page": 10,
            },
        },
    ]


@pytest.fixture
def edge_case_data() -> list[Any]:
    """Edge cases and boundary conditions for robust testing.

    Returns:
        list[Any]: List of edge case data.
    """
    # Create a large data structure
    large_list = list(range(10000))
    large_dict = {f"key_{i}": f"value_{i}" for i in range(1000)}

    return [
        None,  # None value
        {},  # Empty dict
        [],  # Empty list
        "",  # Empty string
        0,  # Zero
        0.0,  # Float zero
        -1,  # Negative number
        float("inf"),  # Positive infinity
        float("-inf"),  # Negative infinity
        1e308,  # Very large number (near float max)
        -1e308,  # Very large negative number
        1e-308,  # Very small positive number
        {  # Unicode and special characters
            "emoji": "🎉🎊🎈",
            "chinese": "你好世界",
            "arabic": "مرحبا بالعالم",
            "special": "\n\t\r\\\"'",
        },
        large_list,  # Very large list
        large_dict,  # Very large dict
        {  # Deeply nested structure
            "level1": {
                "level2": {
                    "level3": {
                        "level4": {
                            "level5": {"value": "deep"},
                        }
                    }
                }
            }
        },
    ]
