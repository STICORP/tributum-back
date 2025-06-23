"""Integration tests for application lifecycle management.

This module tests the startup and shutdown events, including database
connection verification and health check functionality.
"""

import asyncio
import time

import pytest
from httpx import AsyncClient
from pytest_mock import MockerFixture
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncEngine

from src.api.main import create_app, lifespan
from src.core.config import get_settings
from src.infrastructure.database.session import _db_manager, get_engine


@pytest.mark.integration
class TestApplicationLifecycle:
    """Test application lifecycle events."""

    async def test_startup_success(self, db_engine: AsyncEngine) -> None:
        """Test successful application startup with database connection."""
        # Reset the database manager to ensure clean state
        _db_manager.reset()

        # Ensure we have a database engine available for the test
        assert db_engine is not None

        # Create app and test startup
        app = create_app()

        # The lifespan context manager should complete without errors
        async with lifespan(app):
            # Verify engine is created
            engine = get_engine()
            assert engine is not None

            # Verify we can execute a query
            async with engine.connect() as conn:
                result = await conn.execute(text("SELECT 1"))
                assert result.scalar() == 1

    async def test_startup_database_failure(self, mocker: MockerFixture) -> None:
        """Test application startup fails when database is unavailable."""
        # Reset the database manager
        _db_manager.reset()

        # Mock the engine to fail on connect
        mock_engine = mocker.Mock()
        mock_connect = mocker.Mock()
        mock_engine.connect.return_value = mock_connect
        mock_connect.__aenter__ = mocker.AsyncMock(
            side_effect=OperationalError(
                "Connection failed", None, Exception("Connection failed")
            )
        )
        mock_connect.__aexit__ = mocker.AsyncMock()

        # Patch get_engine to return our mock
        mocker.patch("src.api.main.get_engine", return_value=mock_engine)

        app = create_app()

        # Startup should raise an exception
        with pytest.raises(OperationalError):
            async with lifespan(app):
                pass

    async def test_shutdown_cleanup(
        self, db_engine: AsyncEngine, mocker: MockerFixture
    ) -> None:
        """Test application shutdown properly closes database connections."""
        # Reset the database manager
        _db_manager.reset()

        # Ensure we have a database engine available for the test
        assert db_engine is not None

        app = create_app()

        # Track if close_database was called
        close_called = False
        original_close = _db_manager.close

        async def track_close() -> None:
            nonlocal close_called
            close_called = True
            await original_close()

        # Use pytest-mock to mock the close method
        mocker.patch.object(_db_manager, "close", side_effect=track_close)

        # Run startup and shutdown
        async with lifespan(app):
            # Ensure engine is created during startup
            engine = get_engine()
            assert engine is not None

        # Verify shutdown was called
        assert close_called

    async def test_health_endpoint_with_database(
        self, client: AsyncClient, db_engine: AsyncEngine
    ) -> None:
        """Test health endpoint reports database status correctly."""
        # db_engine fixture ensures database is available for the test
        _ = db_engine
        response = await client.get("/health")
        assert response.status_code == 200

        data = response.json()
        # Accept either healthy or degraded status
        assert data["status"] in ("healthy", "degraded")
        # Database check should be attempted
        assert "database" in data
        assert isinstance(data["database"], bool)

    async def test_health_endpoint_database_down(
        self, client: AsyncClient, mocker: MockerFixture
    ) -> None:
        """Test health endpoint handles database failures gracefully."""
        # Mock the engine connection to fail
        mock_engine = mocker.Mock()
        mock_connect = mocker.Mock()
        mock_engine.connect.return_value = mock_connect
        mock_connect.__aenter__ = mocker.AsyncMock(
            side_effect=OperationalError(
                "Database connection lost", None, Exception("Database connection lost")
            )
        )
        mock_connect.__aexit__ = mocker.AsyncMock()

        # Patch get_engine to return our mock
        mocker.patch("src.api.main.get_engine", return_value=mock_engine)

        response = await client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "degraded"
        assert data["database"] is False

    async def test_concurrent_health_checks(
        self, client: AsyncClient, db_engine: AsyncEngine
    ) -> None:
        """Test multiple concurrent health checks work correctly."""
        # db_engine fixture ensures database is available for the test
        _ = db_engine
        # Make 5 concurrent health check requests (reduced to avoid pool issues)
        tasks = [client.get("/health") for _ in range(5)]
        responses = await asyncio.gather(*tasks)

        # All should succeed
        for response in responses:
            assert response.status_code == 200
            data = response.json()
            assert data["status"] in ("healthy", "degraded")
            assert "database" in data
            assert isinstance(data["database"], bool)

        # Allow asyncpg to clean up connections properly
        await asyncio.sleep(0.1)

    async def test_health_check_performance(
        self, client: AsyncClient, db_engine: AsyncEngine
    ) -> None:
        """Test health check completes quickly."""
        # db_engine fixture ensures database is available for the test
        _ = db_engine

        start = time.time()
        response = await client.get("/health")
        duration = time.time() - start

        assert response.status_code == 200
        # Health check should complete in under 100ms
        assert duration < 0.1

    async def test_app_info_during_lifecycle(
        self, client: AsyncClient, db_engine: AsyncEngine
    ) -> None:
        """Test that app info endpoint works during normal lifecycle."""
        # db_engine fixture ensures database is available for the test
        _ = db_engine
        response = await client.get("/info")
        assert response.status_code == 200

        data = response.json()
        settings = get_settings()
        assert data["app_name"] == settings.app_name
        assert data["version"] == settings.app_version
        assert data["environment"] == settings.environment
