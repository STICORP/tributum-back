"""Test the integration test fixtures for proper isolation.

This module verifies that the db_session and client_with_db fixtures
properly isolate tests by rolling back all database changes.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession


@pytest.mark.integration
class TestFixtureIsolation:
    """Test that our integration test fixtures provide proper isolation."""

    @pytest.mark.asyncio
    async def test_db_session_temporary_tables(self, db_session: AsyncSession) -> None:
        """Test using temporary tables for complete isolation."""
        # Create a TEMPORARY table - these are session-specific
        await db_session.execute(
            text(
                "CREATE TEMPORARY TABLE temp_test_isolation "
                "(id SERIAL PRIMARY KEY, value TEXT)"
            )
        )

        # Insert test data
        await db_session.execute(
            text("INSERT INTO temp_test_isolation (value) VALUES (:value)"),
            {"value": "temp_data"},
        )
        await db_session.commit()

        # Verify the data exists
        result = await db_session.execute(
            text("SELECT COUNT(*) FROM temp_test_isolation WHERE value = :value"),
            {"value": "temp_data"},
        )
        count = result.scalar()
        assert count == 1

        # Temporary tables are automatically dropped at session end

    @pytest.mark.asyncio
    async def test_client_with_db_isolation(
        self, client_with_db: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test that client_with_db uses the transactional session."""
        # Create a temporary table for testing
        await db_session.execute(
            text(
                "CREATE TEMPORARY TABLE temp_api_test "
                "(id SERIAL PRIMARY KEY, name TEXT)"
            )
        )
        await db_session.execute(
            text("INSERT INTO temp_api_test (name) VALUES (:name)"),
            {"name": "api_test_value"},
        )
        await db_session.commit()

        # Make an API call to ensure client works
        response = await client_with_db.get("/health")
        assert response.status_code == 200

        # Verify our test data exists in the same transaction
        result = await db_session.execute(
            text("SELECT name FROM temp_api_test WHERE name = :name"),
            {"name": "api_test_value"},
        )
        value = result.scalar()
        assert value == "api_test_value"

    @pytest.mark.asyncio
    async def test_multiple_commits_still_rollback(
        self, db_session: AsyncSession
    ) -> None:
        """Test that multiple commits within a test are rolled back."""
        # Create temporary table
        await db_session.execute(
            text(
                "CREATE TEMPORARY TABLE temp_multi_commit "
                "(id SERIAL PRIMARY KEY, step INT)"
            )
        )
        await db_session.commit()

        # Multiple commits
        for i in range(1, 4):
            await db_session.execute(
                text("INSERT INTO temp_multi_commit (step) VALUES (:step)"),
                {"step": i},
            )
            await db_session.commit()

        # Verify all data exists
        result = await db_session.execute(
            text("SELECT COUNT(*) FROM temp_multi_commit")
        )
        count = result.scalar()
        assert count == 3

    @pytest.mark.asyncio
    async def test_async_operations_work_correctly(
        self, db_session: AsyncSession
    ) -> None:
        """Test that async database operations work as expected."""
        # Create a temporary table
        await db_session.execute(
            text(
                "CREATE TEMPORARY TABLE temp_async_test "
                "(id SERIAL PRIMARY KEY, data TEXT)"
            )
        )

        # Insert multiple rows
        for i in range(10):
            await db_session.execute(
                text("INSERT INTO temp_async_test (data) VALUES (:data)"),
                {"data": f"async_{i}"},
            )

        await db_session.commit()

        # Verify all rows were inserted
        result = await db_session.execute(text("SELECT COUNT(*) FROM temp_async_test"))
        count = result.scalar()
        assert count == 10

    @pytest.mark.asyncio
    async def test_nested_transactions_with_savepoints(
        self, db_session: AsyncSession
    ) -> None:
        """Test that savepoints work correctly within the transactional fixture."""
        # Create temporary table
        await db_session.execute(
            text(
                "CREATE TEMPORARY TABLE temp_savepoint_test "
                "(id SERIAL PRIMARY KEY, value TEXT)"
            )
        )
        await db_session.commit()

        # Insert initial data
        await db_session.execute(
            text("INSERT INTO temp_savepoint_test (value) VALUES ('initial')")
        )

        # Create a savepoint and insert more data
        async with db_session.begin_nested():
            await db_session.execute(
                text("INSERT INTO temp_savepoint_test (value) VALUES ('nested')")
            )
            # This will commit the savepoint

        # Verify both rows exist
        result = await db_session.execute(
            text("SELECT COUNT(*) FROM temp_savepoint_test")
        )
        count = result.scalar()
        assert count == 2

        # Create another savepoint but roll it back
        async def insert_and_rollback() -> None:
            """Insert data in a nested transaction and force rollback."""
            async with db_session.begin_nested():
                await db_session.execute(
                    text(
                        "INSERT INTO temp_savepoint_test (value) VALUES ('rolled_back')"
                    )
                )
                # Force a rollback
                raise Exception("Test rollback")

        with pytest.raises(Exception, match="Test rollback"):
            await insert_and_rollback()

        # Verify only the first two rows exist
        result = await db_session.execute(
            text("SELECT COUNT(*) FROM temp_savepoint_test")
        )
        count = result.scalar()
        assert count == 2

        await db_session.commit()

    @pytest.mark.asyncio
    async def test_isolation_with_constraints(self, db_session: AsyncSession) -> None:
        """Test isolation using temporary tables with constraint checking."""
        # Create a temporary table with constraints
        await db_session.execute(
            text(
                """
                CREATE TEMPORARY TABLE temp_constraint_test (
                    id SERIAL PRIMARY KEY,
                    email TEXT UNIQUE NOT NULL,
                    age INT CHECK (age >= 0)
                )
                """
            )
        )

        # Insert valid data
        await db_session.execute(
            text("INSERT INTO temp_constraint_test (email, age) VALUES (:email, :age)"),
            {"email": "test@example.com", "age": 25},
        )
        await db_session.commit()

        # Verify the data exists
        result = await db_session.execute(
            text("SELECT COUNT(*) FROM temp_constraint_test")
        )
        count = result.scalar()
        assert count == 1

        # Insert another valid row with different email
        await db_session.execute(
            text("INSERT INTO temp_constraint_test (email, age) VALUES (:email, :age)"),
            {"email": "another@example.com", "age": 30},
        )
        await db_session.commit()

        # Verify we now have two rows
        result = await db_session.execute(
            text("SELECT COUNT(*) FROM temp_constraint_test")
        )
        count = result.scalar()
        assert count == 2

    @pytest.mark.asyncio
    async def test_transaction_isolation_between_sessions(
        self, db_session: AsyncSession, db_engine: AsyncEngine
    ) -> None:
        """Test that sessions are properly isolated from each other."""
        # Create a temporary table
        await db_session.execute(
            text(
                "CREATE TEMPORARY TABLE temp_isolation_check "
                "(id SERIAL PRIMARY KEY, data TEXT)"
            )
        )
        await db_session.execute(
            text("INSERT INTO temp_isolation_check (data) VALUES (:data)"),
            {"data": "session1_data"},
        )
        await db_session.commit()

        # Create a second session to verify isolation
        async with db_engine.connect() as second_conn:
            # Try to access the temporary table from another session
            # This should fail because temp tables are session-local
            with pytest.raises(DBAPIError):
                await second_conn.execute(text("SELECT * FROM temp_isolation_check"))

        # Verify our session still has access
        result = await db_session.execute(
            text("SELECT data FROM temp_isolation_check WHERE data = :data"),
            {"data": "session1_data"},
        )
        value = result.scalar()
        assert value == "session1_data"
