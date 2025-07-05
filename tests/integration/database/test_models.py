"""Test models for database integration tests."""

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import BaseModel


class SessionTestModel(BaseModel):
    """Test model for session management tests."""

    __tablename__ = "session_test_model"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    data: Mapped[str | None] = mapped_column(String(500), nullable=True)
