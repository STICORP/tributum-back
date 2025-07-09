"""Unit tests for src/infrastructure/database/base.py module.

This module contains comprehensive unit tests for the database base module,
including the naming convention, Base declarative class, and BaseModel abstract
class with common fields.
"""

import pytest
from pytest_mock import MockType
from sqlalchemy import BigInteger, DateTime, MetaData
from sqlalchemy.orm import DeclarativeBase

from src.infrastructure.database.base import (
    NAMING_CONVENTION,
    Base,
    BaseModel,
)


@pytest.mark.unit
class TestNamingConvention:
    """Tests for the NAMING_CONVENTION dictionary structure and values."""

    def test_naming_convention_structure(self) -> None:
        """Verify that NAMING_CONVENTION contains all required keys."""
        required_keys = {"ix", "uq", "ck", "fk", "pk"}
        actual_keys = set(NAMING_CONVENTION.keys())

        assert actual_keys == required_keys, (
            f"NAMING_CONVENTION missing keys: {required_keys - actual_keys}"
        )

    @pytest.mark.parametrize(
        ("key", "expected_pattern"),
        [
            ("ix", "ix_%(column_0_label)s"),
            ("uq", "uq_%(table_name)s_%(column_0_name)s"),
            ("ck", "ck_%(table_name)s_%(constraint_name)s"),
            ("fk", "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s"),
            ("pk", "pk_%(table_name)s"),
        ],
    )
    def test_naming_convention_values(self, key: str, expected_pattern: str) -> None:
        """Verify that naming convention values follow expected patterns.

        Args:
            key: The naming convention key to test.
            expected_pattern: The expected pattern string.
        """
        assert NAMING_CONVENTION[key] == expected_pattern, (
            f"NAMING_CONVENTION['{key}'] has unexpected pattern"
        )


@pytest.mark.unit
class TestBaseDeclarativeBase:
    """Test the Base declarative base class configuration and metadata."""

    def test_base_class_inheritance(self) -> None:
        """Verify Base class inherits from DeclarativeBase correctly."""
        assert issubclass(Base, DeclarativeBase), (
            "Base should inherit from DeclarativeBase"
        )
        assert Base.__mro__[1] == DeclarativeBase, (
            "DeclarativeBase should be direct parent"
        )

    def test_base_metadata_configuration(self) -> None:
        """Verify that Base.metadata is properly configured with naming conventions."""
        assert hasattr(Base, "metadata"), "Base should have metadata attribute"
        assert Base.metadata.naming_convention == NAMING_CONVENTION, (
            "Base.metadata should use NAMING_CONVENTION"
        )

    def test_base_metadata_type(self) -> None:
        """Verify that Base.metadata is a MetaData instance."""
        assert isinstance(Base.metadata, MetaData), (
            "Base.metadata should be MetaData instance"
        )


@pytest.mark.unit
class TestBaseModel:
    """Test the BaseModel abstract base class with common fields and methods."""

    def test_base_model_abstract_class(self) -> None:
        """Verify BaseModel is marked as abstract."""
        assert hasattr(BaseModel, "__abstract__"), (
            "BaseModel should have __abstract__ attribute"
        )
        assert BaseModel.__abstract__ is True, "BaseModel.__abstract__ should be True"

    def test_base_model_inheritance(self) -> None:
        """Verify BaseModel inherits from Base correctly."""
        assert issubclass(BaseModel, Base), "BaseModel should inherit from Base"
        assert BaseModel.__mro__[1] == Base, "Base should be direct parent of BaseModel"

    def test_base_model_id_field_configuration(self) -> None:
        """Verify the id field is properly configured."""
        # Check that id attribute exists
        assert hasattr(BaseModel, "id"), "BaseModel should have id attribute"

        # In SQLAlchemy 2.0+, we access the column via .column attribute
        id_column = BaseModel.id.column

        # Check column type
        assert isinstance(id_column.type, BigInteger), "id should be BigInteger type"

        # Check primary key
        assert id_column.primary_key is True, "id should be primary key"

        # Check autoincrement
        assert id_column.autoincrement is True, "id should have autoincrement"

        # Check doc
        assert id_column.doc == "Primary key with auto-incrementing BigInteger ID", (
            "id should have correct documentation"
        )

        # Check type annotation
        assert hasattr(BaseModel, "__annotations__"), (
            "BaseModel should have annotations"
        )
        assert "id" in BaseModel.__annotations__, "id should be in annotations"
        # The annotation should be Mapped[int]
        annotation_str = str(BaseModel.__annotations__["id"])
        assert "Mapped[" in annotation_str, (
            f"id should have Mapped type annotation, got: {annotation_str}"
        )

    def test_base_model_created_at_field_configuration(self) -> None:
        """Verify created_at field is properly configured."""
        # Check that created_at attribute exists
        assert hasattr(BaseModel, "created_at"), (
            "BaseModel should have created_at attribute"
        )

        # In SQLAlchemy 2.0+, we access the column via .column attribute
        created_at_column = BaseModel.created_at.column

        # Check column type
        assert isinstance(created_at_column.type, DateTime), (
            "created_at should be DateTime type"
        )
        assert created_at_column.type.timezone is True, (
            "created_at should be timezone-aware"
        )

        # Check nullable
        assert created_at_column.nullable is False, "created_at should not be nullable"

        # Check server_default
        assert created_at_column.server_default is not None, (
            "created_at should have server_default"
        )
        # SQLAlchemy func.now() creates a Function element
        assert hasattr(created_at_column.server_default, "arg"), (
            "server_default should be a function"
        )

        # Check doc
        assert created_at_column.doc == "Timestamp when the record was created (UTC)", (
            "created_at should have correct documentation"
        )

        # Check type annotation
        assert "created_at" in BaseModel.__annotations__, (
            "created_at should be in annotations"
        )
        annotation_str = str(BaseModel.__annotations__["created_at"])
        assert "Mapped[" in annotation_str, (
            f"created_at should have Mapped type annotation, got: {annotation_str}"
        )

    def test_base_model_updated_at_field_configuration(self) -> None:
        """Verify updated_at field is properly configured."""
        # Check that updated_at attribute exists
        assert hasattr(BaseModel, "updated_at"), (
            "BaseModel should have updated_at attribute"
        )

        # In SQLAlchemy 2.0+, we access the column via .column attribute
        updated_at_column = BaseModel.updated_at.column

        # Check column type
        assert isinstance(updated_at_column.type, DateTime), (
            "updated_at should be DateTime type"
        )
        assert updated_at_column.type.timezone is True, (
            "updated_at should be timezone-aware"
        )

        # Check nullable
        assert updated_at_column.nullable is False, "updated_at should not be nullable"

        # Check server_default
        assert updated_at_column.server_default is not None, (
            "updated_at should have server_default"
        )
        assert hasattr(updated_at_column.server_default, "arg"), (
            "server_default should be a function"
        )

        # Check onupdate
        assert updated_at_column.onupdate is not None, "updated_at should have onupdate"
        assert hasattr(updated_at_column.onupdate, "arg"), (
            "onupdate should be a function"
        )

        # Check doc
        assert (
            updated_at_column.doc == "Timestamp when the record was last updated (UTC)"
        ), "updated_at should have correct documentation"

        # Check type annotation
        assert "updated_at" in BaseModel.__annotations__, (
            "updated_at should be in annotations"
        )
        annotation_str = str(BaseModel.__annotations__["updated_at"])
        assert "Mapped[" in annotation_str, (
            f"updated_at should have Mapped type annotation, got: {annotation_str}"
        )

    def test_base_model_repr_method(
        self, concrete_base_model_class: type[BaseModel]
    ) -> None:
        """Test the __repr__ method implementation.

        Args:
            concrete_base_model_class: Fixture providing concrete model class.
        """
        # Create an instance of the concrete model
        instance = concrete_base_model_class()
        instance.id = 42

        # Test repr
        result = repr(instance)
        expected = "<TestModel(id=42)>"

        assert result == expected, f"Expected {expected}, got {result}"

    def test_base_model_repr_method_with_mock_instance(
        self, mock_base_model_instance: MockType
    ) -> None:
        """Test __repr__ method with mocked instance.

        Args:
            mock_base_model_instance: Fixture providing mock instance.
        """
        # Test repr on mock instance
        result = repr(mock_base_model_instance)
        expected = "<TestModel(id=123)>"

        assert result == expected, f"Expected {expected}, got {result}"

    def test_base_model_field_annotations(self) -> None:
        """Verify that field type annotations are properly set."""
        annotations = BaseModel.__annotations__

        # Check that all expected fields have annotations
        expected_fields = {"id", "created_at", "updated_at"}
        actual_fields = set(annotations.keys())

        assert expected_fields.issubset(actual_fields), (
            f"Missing annotations for: {expected_fields - actual_fields}"
        )

        # Verify the annotations are Mapped types
        for field in expected_fields:
            annotation = str(annotations[field])
            assert "Mapped[" in annotation, (
                f"{field} should have Mapped type annotation"
            )
