"""Unit tests for API response utilities.

This module tests the ORJSONResponse class which provides high-performance
JSON serialization using orjson for FastAPI applications.
"""

from typing import Any

import pytest
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from pytest_mock import MockerFixture

from src.api.utils.responses import ORJSONResponse


@pytest.mark.unit
class TestORJSONResponse:
    """Test suite for ORJSONResponse class."""

    def test_initialization(self) -> None:
        """Test ORJSONResponse initializes correctly with proper media type."""
        # Act
        response = ORJSONResponse(content={"test": "data"})

        # Assert
        assert response.media_type == "application/json"
        assert isinstance(response, JSONResponse)

    @pytest.mark.parametrize(
        "dict_data",
        [
            {},
            {"key": "value"},
            {"number": 42, "float": 3.14, "bool": True},
            {"nested": {"inner": {"value": 123}}},
            {"list": [1, 2, 3], "dict": {"a": 1}},
            {"unicode": "Hello 🌍", "special": "tab\tnewline\n"},
        ],
    )
    def test_render_with_dict(
        self,
        dict_data: dict[str, Any],
        mocker: MockerFixture,
    ) -> None:
        """Test rendering of standard dictionary data."""
        # Arrange
        mock_orjson = mocker.patch("src.api.utils.responses.orjson")
        mock_orjson.dumps.return_value = b'{"mocked": "result"}'
        mock_orjson.OPT_SORT_KEYS = 1

        # Create response without triggering render in constructor
        response = ORJSONResponse.__new__(ORJSONResponse)
        response.media_type = "application/json"

        # Act
        result = response.render(dict_data)

        # Assert
        assert isinstance(result, bytes)
        mock_orjson.dumps.assert_called_once_with(dict_data, option=1)

    def test_render_with_pydantic_model(
        self,
        sample_pydantic_models: list[BaseModel],
        mocker: MockerFixture,
    ) -> None:
        """Test rendering of Pydantic BaseModel instances."""
        # Arrange
        mock_orjson = mocker.patch("src.api.utils.responses.orjson")
        mock_orjson.dumps.return_value = b'{"mocked": "model"}'
        mock_orjson.OPT_SORT_KEYS = 1

        # Create response without triggering render in constructor
        response = ORJSONResponse.__new__(ORJSONResponse)
        response.media_type = "application/json"

        for model in sample_pydantic_models:
            # Reset mock before each iteration
            mock_orjson.dumps.reset_mock()

            # Get the expected dumped data
            expected_dump = model.model_dump()

            # Act
            result = response.render(model)

            # Assert
            assert isinstance(result, bytes)
            # Verify orjson.dumps was called with the dumped data
            mock_orjson.dumps.assert_called_once_with(
                expected_dump, option=mock_orjson.OPT_SORT_KEYS
            )

    def test_render_with_various_content_types(
        self,
        sample_content_types: list[Any],
        mocker: MockerFixture,
    ) -> None:
        """Test rendering with different content types."""
        # Arrange
        mock_orjson = mocker.patch("src.api.utils.responses.orjson")
        mock_orjson.dumps.return_value = b'{"mocked": "content"}'
        mock_orjson.OPT_SORT_KEYS = 1

        # Create response without triggering render in constructor
        response = ORJSONResponse.__new__(ORJSONResponse)
        response.media_type = "application/json"

        for content in sample_content_types:
            # Reset mock for each test
            mock_orjson.dumps.reset_mock()

            # Act
            result = response.render(content)

            # Assert
            assert isinstance(result, bytes)
            mock_orjson.dumps.assert_called_once_with(content, option=1)

    def test_orjson_options(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Test that OPT_SORT_KEYS option is used."""
        # Arrange
        mock_orjson = mocker.patch("src.api.utils.responses.orjson")
        mock_orjson.dumps.return_value = b'{"sorted": "keys"}'
        mock_orjson.OPT_SORT_KEYS = 4  # Different value to verify it's used

        # Create response without triggering render in constructor
        response = ORJSONResponse.__new__(ORJSONResponse)
        response.media_type = "application/json"
        test_content = {"b": 2, "a": 1}

        # Act
        response.render(test_content)

        # Assert
        mock_orjson.dumps.assert_called_once_with(
            test_content, option=mock_orjson.OPT_SORT_KEYS
        )

    @pytest.mark.parametrize(
        ("status_code", "headers"),
        [
            (200, None),
            (201, {"X-Custom-Header": "value"}),
            (404, {"Content-Type": "application/json"}),
            (500, {"X-Error": "Internal Server Error"}),
        ],
    )
    def test_jsonresponse_constructor_parameters(
        self,
        status_code: int,
        headers: dict[str, str] | None,
    ) -> None:
        """Test that ORJSONResponse accepts JSONResponse constructor parameters."""
        # Act
        response = ORJSONResponse(
            content={"test": "data"},
            status_code=status_code,
            headers=headers,
        )

        # Assert
        assert response.status_code == status_code
        if headers:
            for key, value in headers.items():
                assert response.headers.get(key) == value

    def test_integration_with_jsonresponse(self) -> None:
        """Test that ORJSONResponse properly extends JSONResponse."""
        # Act & Assert
        assert issubclass(ORJSONResponse, JSONResponse)
        assert hasattr(ORJSONResponse, "media_type")
        assert hasattr(ORJSONResponse, "render")

        # Verify media_type override
        assert ORJSONResponse.media_type == "application/json"

    @pytest.mark.parametrize(
        ("exception_type", "exception_message"),
        [
            (TypeError, "Object of type 'set' is not JSON serializable"),
            (ValueError, "Invalid JSON data"),
            (OverflowError, "Number too large"),
        ],
    )
    def test_orjson_serialization_error_handling(
        self,
        exception_type: type[Exception],
        exception_message: str,
        mocker: MockerFixture,
    ) -> None:
        """Test behavior when orjson.dumps raises an exception."""
        # Arrange
        mock_orjson = mocker.patch("src.api.utils.responses.orjson")
        mock_orjson.dumps.side_effect = exception_type(exception_message)
        mock_orjson.OPT_SORT_KEYS = 1

        # Create response without triggering render in constructor
        response = ORJSONResponse.__new__(ORJSONResponse)
        response.media_type = "application/json"

        # Act & Assert
        with pytest.raises(exception_type) as exc_info:
            response.render({"test": "data"})

        assert str(exc_info.value) == exception_message

    def test_media_type_class_attribute(self) -> None:
        """Test that media_type is properly set as class attribute."""
        # Assert class attribute
        assert hasattr(ORJSONResponse, "media_type")
        assert ORJSONResponse.media_type == "application/json"

        # Verify it's a class attribute, not instance attribute
        response1 = ORJSONResponse(content={})
        response2 = ORJSONResponse(content={})

        # Both instances should share the same media_type
        assert response1.media_type == response2.media_type == "application/json"

        # Verify it overrides JSONResponse.media_type
        assert ORJSONResponse.media_type == JSONResponse.media_type

    def test_render_edge_cases(
        self,
        edge_case_data: list[Any],
        mocker: MockerFixture,
    ) -> None:
        """Test render method with edge cases and boundary conditions."""
        # Arrange
        mock_orjson = mocker.patch("src.api.utils.responses.orjson")
        mock_orjson.OPT_SORT_KEYS = 1

        for edge_case_value in edge_case_data:
            # Set return value for this edge case
            mock_orjson.dumps.return_value = b'{"edge": "case"}'
            mock_orjson.dumps.reset_mock()

            # Create response without triggering render in constructor
            response = ORJSONResponse.__new__(ORJSONResponse)
            response.media_type = "application/json"

            # Act
            result = response.render(edge_case_value)

            # Assert
            assert isinstance(result, bytes)
            mock_orjson.dumps.assert_called_once_with(edge_case_value, option=1)

    def test_render_pydantic_model_dump_data_flow(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Test the complete data flow when rendering Pydantic models."""
        # Arrange
        mock_orjson = mocker.patch("src.api.utils.responses.orjson")
        mock_orjson.dumps.return_value = b'{"final": "result"}'
        mock_orjson.OPT_SORT_KEYS = 1

        # Create a mock Pydantic model
        mock_model = mocker.Mock(spec=BaseModel)
        mock_model.model_dump.return_value = {"dumped": "data", "id": 123}

        # Create response without triggering render in constructor
        response = ORJSONResponse.__new__(ORJSONResponse)
        response.media_type = "application/json"

        # Act
        result = response.render(mock_model)

        # Assert
        # Verify model_dump was called
        mock_model.model_dump.assert_called_once()

        # Verify orjson.dumps received the dumped data
        mock_orjson.dumps.assert_called_once_with(
            {"dumped": "data", "id": 123}, option=1
        )

        # Verify the result is bytes
        assert result == b'{"final": "result"}'

    def test_render_non_pydantic_object_passes_through(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Test that non-Pydantic objects are passed directly to orjson."""
        # Arrange
        mock_orjson = mocker.patch("src.api.utils.responses.orjson")
        mock_orjson.dumps.return_value = b'{"custom": "object"}'
        mock_orjson.OPT_SORT_KEYS = 1

        # Create a custom object (not a Pydantic model)
        class CustomObject:
            def __init__(self) -> None:
                self.value = "test"

        custom_obj = CustomObject()

        # Create response without triggering render in constructor
        response = ORJSONResponse.__new__(ORJSONResponse)
        response.media_type = "application/json"

        # Act
        result = response.render(custom_obj)

        # Assert
        # Verify the object was passed directly to orjson
        mock_orjson.dumps.assert_called_once_with(custom_obj, option=1)
        assert result == b'{"custom": "object"}'

    def test_multiple_renders_independence(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Test that multiple render calls are independent."""
        # Arrange
        mock_orjson = mocker.patch("src.api.utils.responses.orjson")
        mock_orjson.OPT_SORT_KEYS = 1

        # Set up different return values for each call
        mock_orjson.dumps.side_effect = [
            b'{"first": "call"}',
            b'{"second": "call"}',
            b'{"third": "call"}',
        ]

        # Create response without triggering render in constructor
        response = ORJSONResponse.__new__(ORJSONResponse)
        response.media_type = "application/json"

        # Act
        result1 = response.render({"data": 1})
        result2 = response.render({"data": 2})
        result3 = response.render({"data": 3})

        # Assert
        assert result1 == b'{"first": "call"}'
        assert result2 == b'{"second": "call"}'
        assert result3 == b'{"third": "call"}'

        # Verify all calls were made
        assert mock_orjson.dumps.call_count == 3
