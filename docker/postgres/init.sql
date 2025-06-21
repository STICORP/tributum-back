-- init.sql: PostgreSQL initialization script for Tributum
-- This script runs when the PostgreSQL container starts for the first time

-- Grant CREATE DATABASE privilege to tributum user for parallel test execution
-- This allows the test fixtures to create isolated databases for each worker
ALTER USER tributum CREATEDB;

-- Create test database as a copy of the main database
-- This allows tests to run in isolation without affecting the main database
CREATE DATABASE tributum_test WITH TEMPLATE tributum_db;

-- Grant all privileges on the test database to the tributum user
GRANT ALL PRIVILEGES ON DATABASE tributum_test TO tributum;

-- Connect to the test database to ensure it's properly set up
\c tributum_test;

-- Ensure the tributum user has full permissions in the test database
-- This includes creating schemas, tables, and other database objects
GRANT ALL ON SCHEMA public TO tributum;
