"""Example database integration test showing parallel database isolation.

This demonstrates how to use the database fixtures for parallel test execution.
Each test worker gets its own database, allowing true parallel execution.
"""

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.integration
class TestDatabaseExample:
    """Example tests showing database isolation in parallel execution."""

    async def test_database_isolation(
        self, db_session: AsyncSession, worker_database_name: str
    ) -> None:
        """Test that each worker has its own isolated database.

        This test demonstrates:
        - Worker-specific database isolation for parallel execution
        - Workers can create persistent tables without conflicts
        - Safe SQL patterns with parameterized queries
        """
        # Get current database name
        result = await db_session.execute(text("SELECT current_database()"))
        current_db = result.scalar()

        # Verify we're connected to the worker-specific database
        assert current_db == worker_database_name

        # Create a persistent test table to demonstrate worker isolation
        await db_session.execute(
            text(
                "CREATE TABLE IF NOT EXISTS test_isolation "
                "(id INT PRIMARY KEY, data TEXT)"
            )
        )
        await db_session.commit()  # Explicit commit to show persistence

        # Insert data unique to this worker
        await db_session.execute(
            text("INSERT INTO test_isolation (id, data) VALUES (:id, :data)"),
            {"id": 1, "data": f"Worker: {worker_database_name}"},
        )
        await db_session.commit()  # Commit to demonstrate real persistence

        # Verify the data exists
        result = await db_session.execute(
            text("SELECT data FROM test_isolation WHERE id = 1")
        )
        data = result.scalar()
        assert data == f"Worker: {worker_database_name}"

    async def test_parallel_execution_safety(
        self, db_session: AsyncSession, worker_database_name: str
    ) -> None:
        """Test that parallel execution doesn't cause conflicts.

        This test demonstrates:
        - Parallel workers can create their own persistent tables
        - Heavy database operations work safely in parallel
        - Worker-specific naming prevents conflicts
        """
        # Create a unique table name based on worker database
        # Use worker_database_name for compatibility (worker_id not always available)
        table_name = f"test_worker_{worker_database_name}".replace("-", "_")

        # Create a persistent table unique to this worker
        # This demonstrates workers don't conflict when creating tables
        await db_session.execute(
            text(
                f"CREATE TABLE IF NOT EXISTS {table_name} "
                "(id SERIAL PRIMARY KEY, value INT)"
            )
        )
        await db_session.commit()  # Commit to create real table

        # Insert many rows to simulate heavy database usage
        # Use parameterized queries for safety
        for i in range(100):
            await db_session.execute(
                text(f"INSERT INTO {table_name} (value) VALUES (:value)"), {"value": i}
            )
        await db_session.commit()  # Commit the inserts

        # Verify the count
        result = await db_session.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
        count = result.scalar()
        assert count == 100

    async def test_database_url_fixture(
        self, database_url: str, worker_database_name: str
    ) -> None:
        """Test that the database_url fixture provides the correct URL.

        This test demonstrates:
        - Fixture dependency injection
        - URL structure validation
        - Worker-specific database naming
        """
        # Verify the URL contains the expected components
        assert "postgresql+asyncpg://" in database_url
        assert "tributum_test" in database_url

        # Verify the worker-specific database name is in the URL
        assert worker_database_name in database_url

        # Verify URL ends with the correct database name
        assert database_url.endswith(f"/{worker_database_name}")
