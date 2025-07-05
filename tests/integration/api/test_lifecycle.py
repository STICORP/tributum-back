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
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.integration
class TestApplicationLifecycle:
    """Test application lifecycle events."""

    async def test_database_connection_during_lifecycle(
        self, db_session: AsyncSession
    ) -> None:
        """Test that database connection works during application lifecycle."""
        # The db_session fixture ensures we have a working database connection
        # No need to manually test startup - the fixture handles it

        # Verify we can execute a query
        result = await db_session.execute(text("SELECT 1"))
        assert result.scalar() == 1

        # Create a temporary table to verify isolation
        await db_session.execute(
            text("CREATE TEMPORARY TABLE lifecycle_test (id INT PRIMARY KEY)")
        )
        await db_session.execute(text("INSERT INTO lifecycle_test (id) VALUES (1)"))
        await db_session.commit()

        # Verify the data exists
        result = await db_session.execute(text("SELECT COUNT(*) FROM lifecycle_test"))
        assert result.scalar() == 1

    async def test_health_endpoint_with_database(
        self, client_with_db: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test health endpoint reports database status correctly."""
        # client_with_db ensures both app and database are available
        response = await client_with_db.get("/health")
        assert response.status_code == 200

        data = response.json()
        # Should be healthy since we have a working database
        assert data["status"] == "healthy"
        assert data["database"] is True

        # Verify we can use the database in the same test
        result = await db_session.execute(text("SELECT 1"))
        assert result.scalar() == 1

    async def test_health_endpoint_database_mock_failure(
        self, client: AsyncClient, mocker: MockerFixture
    ) -> None:
        """Test health endpoint handles database failures gracefully."""
        # Mock database connection check to return failure
        mocker.patch(
            "src.api.main.check_database_connection",
            return_value=(False, "Database connection lost"),
        )

        response = await client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "degraded"
        assert data["database"] is False

    async def test_concurrent_health_checks(self, client_with_db: AsyncClient) -> None:
        """Test multiple concurrent health checks work correctly."""
        # Make 5 concurrent health check requests
        tasks = [client_with_db.get("/health") for _ in range(5)]
        responses = await asyncio.gather(*tasks)

        # All should succeed
        for response in responses:
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["database"] is True

    async def test_health_check_performance(self, client_with_db: AsyncClient) -> None:
        """Test health check completes quickly."""
        start = time.time()
        response = await client_with_db.get("/health")
        duration = time.time() - start

        assert response.status_code == 200
        # Health check should complete in under 100ms
        assert duration < 0.1

    async def test_app_info_during_lifecycle(self, client: AsyncClient) -> None:
        """Test that app info endpoint works during normal lifecycle."""
        response = await client.get("/info")
        assert response.status_code == 200

        data = response.json()
        # Verify the response contains expected fields
        assert "app_name" in data
        assert "version" in data
        assert "environment" in data
        assert "debug" in data

        # In test environment, these should match test settings
        assert data["app_name"] == "Tributum"
        assert data["environment"] == "development"  # Default test environment
        assert data["debug"] is True  # Default for test environment

    async def test_multiple_database_operations_during_lifecycle(
        self, client_with_db: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test that multiple database operations work correctly."""
        # First, check health
        response = await client_with_db.get("/health")
        assert response.status_code == 200
        assert response.json()["database"] is True

        # Create temporary tables for testing
        await db_session.execute(
            text(
                """CREATE TEMPORARY TABLE lifecycle_ops_test (
                    id SERIAL PRIMARY KEY,
                    operation TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )"""
            )
        )

        # Perform multiple operations
        operations = ["startup", "health_check", "data_insert", "data_query"]
        for op in operations:
            await db_session.execute(
                text("INSERT INTO lifecycle_ops_test (operation) VALUES (:op)"),
                {"op": op},
            )

        await db_session.commit()

        # Verify all operations were recorded
        result = await db_session.execute(
            text("SELECT COUNT(*) FROM lifecycle_ops_test")
        )
        assert result.scalar() == len(operations)

        # Make another API call to ensure app is still healthy
        response = await client_with_db.get("/info")
        assert response.status_code == 200

    async def test_database_pool_during_lifecycle(
        self, client_with_db: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test that database pool handles multiple connections properly."""
        # Create a temporary table
        await db_session.execute(
            text("CREATE TEMPORARY TABLE pool_test (id INT PRIMARY KEY)")
        )

        # Make multiple concurrent requests that would use the database
        tasks = [client_with_db.get("/health") for _ in range(3)]

        responses = await asyncio.gather(*tasks)

        # All requests should succeed
        for response in responses:
            assert response.status_code == 200
            assert response.json()["database"] is True

        # Our session should still work
        await db_session.execute(text("INSERT INTO pool_test (id) VALUES (1)"))
        await db_session.commit()

        result = await db_session.execute(text("SELECT COUNT(*) FROM pool_test"))
        assert result.scalar() == 1
