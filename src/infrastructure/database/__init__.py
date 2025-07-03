"""Database infrastructure with async PostgreSQL and repository pattern.

This package provides a complete database access layer using SQLAlchemy 2.0+
with async support, implementing the repository pattern for clean separation
of concerns.

Core components:
- **base**: Declarative base and common model fields
- **session**: Async engine and session management
- **repository**: Generic repository with CRUD operations
- **dependencies**: FastAPI dependency injection helpers

The implementation emphasizes:
- **Type safety**: Full typing with generics for repositories
- **Performance**: Connection pooling and query optimization
- **Observability**: Query logging and slow query detection
- **Reliability**: Health checks and proper cleanup

All database operations are async-first, leveraging PostgreSQL's
async capabilities through the asyncpg driver.
"""

from src.infrastructure.database.base import Base, BaseModel
from src.infrastructure.database.dependencies import DatabaseSession, get_db
from src.infrastructure.database.repository import BaseRepository
from src.infrastructure.database.session import (
    close_database,
    create_database_engine,
    get_async_session,
    get_engine,
    get_session_factory,
)

__all__ = [
    "Base",
    "BaseModel",
    "BaseRepository",
    "DatabaseSession",
    "close_database",
    "create_database_engine",
    "get_async_session",
    "get_db",
    "get_engine",
    "get_session_factory",
]
