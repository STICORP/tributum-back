"""Base model and declarative base for SQLAlchemy ORM.

This module provides the foundation for all database models in the Tributum
application, including a base model with common fields and naming conventions.
"""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, MetaData, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Naming convention for constraints to ensure consistency
# and avoid conflicts during migrations
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """SQLAlchemy declarative base with naming conventions.

    This base class configures naming conventions for all database
    constraints to ensure consistency across the application.
    """

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class BaseModel(Base):
    """Abstract base model with common fields for all database models.

    This model provides:
    - Sequential integer ID (BigInteger for scale)
    - Automatic created_at timestamp
    - Automatic updated_at timestamp (updates on modification)

    All models in the application should inherit from this base model
    to ensure consistent field naming and behavior.
    """

    __abstract__ = True

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
        doc="Primary key with auto-incrementing BigInteger ID",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        doc="Timestamp when the record was created (UTC)",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        doc="Timestamp when the record was last updated (UTC)",
    )

    def __repr__(self) -> str:
        """Return a string representation of the model instance.

        Returns:
            str: A string showing the model class name and ID
        """
        return f"<{self.__class__.__name__}(id={self.id})>"
