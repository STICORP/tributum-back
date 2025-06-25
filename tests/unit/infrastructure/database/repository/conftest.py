"""Shared fixtures and test models for repository tests."""

from typing import cast
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture
from sqlalchemy import String
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import BaseModel
from src.infrastructure.database.repository import BaseRepository


class ModelForRepositoryTesting(BaseModel):
    """Test model for repository testing."""

    __tablename__ = "model_repository_testing"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)


@pytest.fixture
def mock_session(mocker: MockerFixture) -> MagicMock:
    """Create a properly mocked async session."""
    mock = mocker.MagicMock(spec=AsyncSession)
    return cast("MagicMock", mock)


@pytest.fixture
def test_repository(
    mock_session: MagicMock,
) -> BaseRepository[ModelForRepositoryTesting]:
    """Create a test repository instance."""
    return BaseRepository(cast("AsyncSession", mock_session), ModelForRepositoryTesting)
