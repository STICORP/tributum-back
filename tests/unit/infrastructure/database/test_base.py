"""Unit tests for base model and declarative base."""

import asyncio
from datetime import UTC, datetime

import pytest
import pytest_check
from sqlalchemy import BigInteger, DateTime, Integer, String
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import NAMING_CONVENTION, Base, BaseModel


@pytest.mark.unit
class TestBase:
    """Test cases for the declarative base."""

    def test_base_has_metadata(self) -> None:
        """Test that Base has metadata configured."""
        assert hasattr(Base, "metadata")
        assert Base.metadata is not None

    def test_naming_conventions_applied(self) -> None:
        """Test that naming conventions are properly configured."""
        # Check that metadata has naming convention
        assert Base.metadata.naming_convention is not None

        # Verify all expected naming conventions are present
        with pytest_check.check:
            assert "ix" in Base.metadata.naming_convention
        with pytest_check.check:
            assert "uq" in Base.metadata.naming_convention
        with pytest_check.check:
            assert "ck" in Base.metadata.naming_convention
        with pytest_check.check:
            assert "fk" in Base.metadata.naming_convention
        with pytest_check.check:
            assert "pk" in Base.metadata.naming_convention

    def test_naming_convention_values(self) -> None:
        """Test that naming convention values match expected patterns."""
        conventions = Base.metadata.naming_convention

        # Check each convention directly
        with pytest_check.check:
            assert "ix" in conventions
            assert conventions.get("ix") == NAMING_CONVENTION["ix"]
        with pytest_check.check:
            assert "uq" in conventions
            assert conventions.get("uq") == NAMING_CONVENTION["uq"]
        with pytest_check.check:
            assert "ck" in conventions
            assert conventions.get("ck") == NAMING_CONVENTION["ck"]
        with pytest_check.check:
            assert "fk" in conventions
            assert conventions.get("fk") == NAMING_CONVENTION["fk"]
        with pytest_check.check:
            assert "pk" in conventions
            assert conventions.get("pk") == NAMING_CONVENTION["pk"]


@pytest.mark.unit
class TestBaseModel:
    """Test cases for the BaseModel abstract class."""

    def test_base_model_is_abstract(self) -> None:
        """Test that BaseModel is marked as abstract."""
        assert BaseModel.__abstract__ is True

    def test_base_model_has_required_columns(self) -> None:
        """Test that BaseModel defines all required columns."""
        # Check column existence
        assert hasattr(BaseModel, "id")
        assert hasattr(BaseModel, "created_at")
        assert hasattr(BaseModel, "updated_at")

    def test_id_column_configuration(self) -> None:
        """Test ID column is properly configured."""
        id_column = BaseModel.id

        # MappedColumn has the column directly
        assert hasattr(id_column, "column")
        column = id_column.column

        # Check column type
        assert isinstance(column.type, BigInteger)

        # Check primary key
        assert column.primary_key is True

        # Check autoincrement
        assert column.autoincrement is True

    def test_created_at_column_configuration(self) -> None:
        """Test created_at column is properly configured."""
        created_at_column = BaseModel.created_at

        # MappedColumn has the column directly
        assert hasattr(created_at_column, "column")
        column = created_at_column.column

        # Check column type
        assert isinstance(column.type, DateTime)
        assert column.type.timezone is True

        # Check server default (func.now())
        assert column.server_default is not None

        # Check nullable
        assert column.nullable is False

    def test_updated_at_column_configuration(self) -> None:
        """Test updated_at column is properly configured."""
        updated_at_column = BaseModel.updated_at

        # MappedColumn has the column directly
        assert hasattr(updated_at_column, "column")
        column = updated_at_column.column

        # Check column type
        assert isinstance(column.type, DateTime)
        assert column.type.timezone is True

        # Check server default
        assert column.server_default is not None

        # Check onupdate
        assert column.onupdate is not None

        # Check nullable
        assert column.nullable is False

    def test_repr_method(self) -> None:
        """Test the __repr__ method format."""

        # Create a test model that inherits from BaseModel
        class TestModel(BaseModel):
            __tablename__ = "test_model"
            __abstract__ = False

        # Create an instance with a mock ID
        instance = TestModel()
        instance.id = 123

        # Test repr format
        assert repr(instance) == "<TestModel(id=123)>"

    def test_repr_method_with_none_id(self) -> None:
        """Test the __repr__ method with None ID."""

        # Create a test model that inherits from BaseModel
        class TestModel(BaseModel):
            __tablename__ = "test_model_none"
            __abstract__ = False

        # Create an instance without setting ID
        instance = TestModel()

        # Test repr format with None ID
        assert repr(instance) == "<TestModel(id=None)>"


@pytest.mark.unit
@pytest.mark.asyncio
class TestBaseModelIntegration:
    """Integration tests for BaseModel with a real database."""

    # These tests use PostgreSQL fixtures from test_database_fixtures.py
    # The db_engine and database_url fixtures are automatically available

    async def test_model_creation(self, db_engine: AsyncEngine) -> None:
        """Test creating a model instance with auto-generated fields."""

        # Create a concrete model for testing
        class TestEntity(BaseModel):
            __tablename__ = "test_entities"
            __abstract__ = False

            name: Mapped[str] = mapped_column(String(100))

        # Create the table
        async with db_engine.begin() as conn:
            await conn.run_sync(TestEntity.metadata.create_all)

        # Create a session and save an instance
        async with AsyncSession(db_engine) as session:
            entity = TestEntity(name="Test Entity")
            session.add(entity)
            await session.commit()

            # Refresh to get database-generated values
            await session.refresh(entity)

        # Verify auto-generated fields
        assert entity.id is not None
        assert isinstance(entity.id, int)
        assert entity.id > 0

        assert entity.created_at is not None
        assert isinstance(entity.created_at, datetime)

        assert entity.updated_at is not None
        assert isinstance(entity.updated_at, datetime)

        # created_at and updated_at should be the same initially
        assert entity.created_at == entity.updated_at

    async def test_sequential_id_generation(self, db_engine: AsyncEngine) -> None:
        """Test that IDs are generated sequentially."""

        # Create a concrete model for testing
        class TestSequential(BaseModel):
            __tablename__ = "test_sequential"
            __abstract__ = False

            value: Mapped[int] = mapped_column(Integer)

        # Create the table
        async with db_engine.begin() as conn:
            await conn.run_sync(TestSequential.metadata.create_all)

        # Create a session and save multiple instances
        async with AsyncSession(db_engine) as session:
            entities = [TestSequential(value=i) for i in range(3)]
            session.add_all(entities)
            await session.commit()

            # Refresh all entities
            for entity in entities:
                await session.refresh(entity)

        # Check sequential IDs
        ids = [entity.id for entity in entities]
        assert ids == sorted(ids)  # IDs should be in ascending order

        # Check that IDs increment by 1
        for i in range(1, len(ids)):
            assert ids[i] == ids[i - 1] + 1

    async def test_timestamp_defaults(self, db_engine: AsyncEngine) -> None:
        """Test that timestamps are set to current time by default."""

        # Create a concrete model for testing
        class TestTimestamps(BaseModel):
            __tablename__ = "test_timestamps"
            __abstract__ = False

            data: Mapped[str] = mapped_column(String(50))

        # Create the table
        async with db_engine.begin() as conn:
            await conn.run_sync(TestTimestamps.metadata.create_all)

        # Record time before creation
        before_create = datetime.now(UTC)

        # Create a session and save an instance
        async with AsyncSession(db_engine) as session:
            entity = TestTimestamps(data="test")
            session.add(entity)
            await session.commit()
            await session.refresh(entity)

            # Record time after creation
            after_create = datetime.now(UTC)

        # Verify timestamps are within expected range
        assert before_create <= entity.created_at <= after_create
        assert before_create <= entity.updated_at <= after_create

    async def test_updated_at_changes_on_update(self, db_engine: AsyncEngine) -> None:
        """Test that updated_at changes when record is updated."""

        # Create a concrete model for testing
        class TestUpdate(BaseModel):
            __tablename__ = "test_updates"
            __abstract__ = False

            data: Mapped[str] = mapped_column(String(50))

        # Create the table
        async with db_engine.begin() as conn:
            await conn.run_sync(TestUpdate.metadata.create_all)

        # Create and save an instance
        async with AsyncSession(db_engine) as session:
            entity = TestUpdate(data="initial")
            session.add(entity)
            await session.commit()
            await session.refresh(entity)

            initial_created_at = entity.created_at
            initial_updated_at = entity.updated_at

            # Wait a bit to ensure timestamp difference
            await asyncio.sleep(0.1)

            # Update the entity
            entity.data = "updated"
            await session.commit()
            await session.refresh(entity)

            # Verify created_at didn't change but updated_at did
            assert entity.created_at == initial_created_at
            assert entity.updated_at > initial_updated_at

    async def test_naming_convention_applied_to_constraints(
        self, db_engine: AsyncEngine
    ) -> None:
        """Test that naming conventions are applied to actual constraints."""

        # Create a model with various constraints
        class TestConstraints(BaseModel):
            __tablename__ = "test_constraints"
            __abstract__ = False

            unique_field: Mapped[str] = mapped_column(
                String(50), unique=True, nullable=False
            )

        # Create the table
        async with db_engine.begin() as conn:
            await conn.run_sync(TestConstraints.metadata.create_all)

        # Get the table metadata
        table_metadata = TestConstraints.metadata.tables["test_constraints"]

        # Check primary key constraint name
        pk_columns = [col for col in table_metadata.columns if col.primary_key]
        assert len(pk_columns) == 1

        # Find the primary key constraint
        pk_found = False
        for constraint in table_metadata.constraints:
            if hasattr(constraint, "name") and constraint.name == "pk_test_constraints":
                pk_found = True
                break
        assert pk_found, "Primary key constraint not found with expected name"

        # Check unique constraint exists
        unique_constraints_found = False
        for constraint in table_metadata.constraints:
            if hasattr(constraint, "columns") and hasattr(
                constraint, "_pending_colargs"
            ):
                col_names = {col.name for col in constraint.columns}
                if "unique_field" in col_names:
                    unique_constraints_found = True
                    break
        assert unique_constraints_found
