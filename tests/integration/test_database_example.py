"""Example database integration test showing parallel database isolation.

This demonstrates how to use the database fixtures for parallel test execution.
Each test worker gets its own database, allowing true parallel execution.
"""

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine


@pytest.mark.integration
class TestDatabaseExample:
    """Example tests showing database isolation in parallel execution."""

    @pytest.mark.asyncio
    async def test_database_isolation(
        self, db_engine: AsyncEngine, worker_database_name: str
    ) -> None:
        """Test that each worker has its own isolated database."""
        async with db_engine.connect() as conn:
            # Get current database name
            result = await conn.execute(text("SELECT current_database()"))
            current_db = result.scalar()

            # Verify we're connected to the worker-specific database
            assert current_db == worker_database_name

            # Create a test table
            await conn.execute(
                text(
                    "CREATE TABLE IF NOT EXISTS test_isolation "
                    "(id INT PRIMARY KEY, data TEXT)"
                )
            )
            await conn.commit()

            # Insert data unique to this worker
            await conn.execute(
                text("INSERT INTO test_isolation (id, data) VALUES (:id, :data)"),
                {"id": 1, "data": f"Worker: {worker_database_name}"},
            )
            await conn.commit()

            # Verify the data
            result = await conn.execute(
                text("SELECT data FROM test_isolation WHERE id = 1")
            )
            data = result.scalar()
            assert data == f"Worker: {worker_database_name}"

    @pytest.mark.asyncio
    async def test_parallel_execution_safety(
        self, db_engine: AsyncEngine, worker_id: str
    ) -> None:
        """Test that parallel execution doesn't cause conflicts."""
        async with db_engine.connect() as conn:
            # Each worker creates its own table with a unique name
            table_name = f"test_worker_{worker_id}".replace("-", "_")

            await conn.execute(
                text(
                    f"CREATE TABLE IF NOT EXISTS {table_name} "
                    "(id SERIAL PRIMARY KEY, value INT)"
                )
            )
            await conn.commit()

            # Insert many rows to simulate heavy database usage
            for i in range(100):
                await conn.execute(
                    text(f"INSERT INTO {table_name} (value) VALUES (:value)"),
                    {"value": i},
                )
            await conn.commit()

            # Verify the count
            result = await conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
            count = result.scalar()
            assert count == 100

    @pytest.mark.asyncio
    async def test_database_url_fixture(self, database_url: str) -> None:
        """Test that the database_url fixture provides the correct URL."""
        # Verify the URL contains the expected components
        assert "postgresql+asyncpg://" in database_url
        assert "tributum_test" in database_url

        # For parallel workers, verify the worker ID is in the database name
        if "gw" in database_url:
            assert database_url.endswith("_gw") or "_gw" in database_url
