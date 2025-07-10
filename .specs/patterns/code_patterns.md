# Tributum Code Patterns

This document describes the coding patterns used in the Tributum project. Follow these patterns when implementing new features.

## Module Structure

### Module Docstrings

Every module MUST start with a comprehensive docstring:

```python
"""Brief one-line description.

Detailed explanation of the module's purpose, features, and responsibilities.

Key components:
- **Component 1**: Description
- **Component 2**: Description

Additional context if needed.
"""
```

### Import Organization

Order imports as follows:

```python
# Standard library
from datetime import datetime
from typing import Any

# Third-party
from fastapi import FastAPI
from pydantic import BaseModel

# Local imports
from src.core.config import Settings
from src.core.exceptions import TributumError
```

## Type Safety

### Type Annotations

Use full type annotations for ALL functions and methods:

```python
async def get_user(user_id: int) -> User | None:
    """Get user by ID."""
    ...
```

### Type Aliases (Python 3.13+)

Define reusable types using the `type` keyword:

```python
type JsonValue = dict[str, "JsonValue"] | list["JsonValue"] | str | int | float | bool | None
type ErrorContext = dict[str, Any]
```

### Generic Types

Use TypeVar for generic repository/service patterns:

```python
from typing import TypeVar

T = TypeVar("T", bound=BaseModel)

class BaseRepository[T: BaseModel]:
    def __init__(self, session: AsyncSession, model_class: type[T]) -> None:
        ...
```

## Configuration Management

### Pydantic Settings

Use nested Pydantic models for configuration:

```python
class DatabaseConfig(BaseModel):
    database_url: str = Field(...)
    pool_size: int = Field(default=10, ge=1, le=100)

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_nested_delimiter="__",
    )
    database_config: DatabaseConfig = Field(default_factory=DatabaseConfig)

@lru_cache
def get_settings() -> Settings:
    return Settings()
```

Environment variables use `__` for nesting: `DATABASE_CONFIG__POOL_SIZE=20`

## Exception Handling

### Custom Exception Hierarchy

All exceptions inherit from TributumError:

```python
class TributumError(Exception):
    def __init__(
        self,
        error_code: str | ErrorCode,
        message: str,
        severity: Severity = Severity.MEDIUM,
        context: dict[str, Any] | None = None,
        cause: Exception | None = None,
    ) -> None:
        ...

class ValidationError(TributumError):
    def __init__(self, message: str, ...) -> None:
        super().__init__(ErrorCode.VALIDATION_ERROR, message, Severity.LOW, ...)
```

### Exception Handlers

Register handlers in order:

```python
def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(TributumError, tributum_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(Exception, generic_exception_handler)
```

## Database Patterns

### Base Model

All models inherit from BaseModel:

```python
class BaseModel(Base):
    __abstract__ = True

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
```

### Repository Pattern

Create domain-specific repositories inheriting from BaseRepository:

```python
class UserRepository(BaseRepository[User]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, User)

    async def find_by_email(self, email: str) -> User | None:
        """Custom query method."""
        return await self.find_one_by(email=email)
```

## API Patterns

### FastAPI Application Setup

Use lifespan context manager and proper middleware ordering:

```python
@asynccontextmanager
async def lifespan(app_instance: FastAPI) -> AsyncGenerator[None]:
    # Startup
    await check_database_connection()
    yield
    # Shutdown
    await close_database()

def create_app() -> FastAPI:
    app = FastAPI(lifespan=lifespan, default_response_class=ORJSONResponse)

    # Register in order:
    register_exception_handlers(app)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)

    return app
```

### Dependency Injection

Use FastAPI's Depends for dependencies:

```python
async def get_db_session() -> AsyncGenerator[AsyncSession]:
    async with async_session_maker() as session:
        yield session

@app.get("/users/{user_id}")
async def get_user(
    user_id: int,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> User:
    ...
```

## Documentation Standards

### Function Docstrings

Use Google-style docstrings:

```python
async def create_user(user_data: UserCreate, session: AsyncSession) -> User:
    """Create a new user.

    Args:
        user_data: User creation data containing email and password.
        session: Database session for the operation.

    Returns:
        User: The created user instance.

    Raises:
        ValidationError: If email already exists.
        BusinessRuleError: If user limit exceeded.
    """
    ...
```

### Class Docstrings

Document class purpose and usage:

```python
class UserService:
    """Handles user-related business logic.

    This service provides methods for user management including
    creation, authentication, and profile updates.

    Args:
        repository: User repository for database operations.
        cache: Optional cache service for performance.
    """
    ...
```

## Logging and Observability

### Structured Logging

Use loguru with structured context:

```python
logger.info(
    "User created successfully",
    user_id=user.id,
    email=user.email,
    correlation_id=correlation_id,
)

logger.error(
    "Database connection failed",
    error=str(exc),
    **sanitize_error_context(exc),
)
```

### OpenTelemetry Integration

Add spans for important operations:

```python
span = trace.get_current_span()
if span.is_recording():
    span.set_attribute("user.id", user_id)
    span.set_attribute("operation.type", "user_creation")
```

## Best Practices

1. **Always use async/await** for I/O operations
2. **Validate input** using Pydantic models
3. **Handle errors explicitly** with custom exceptions
4. **Log operations** with appropriate context
5. **Use dependency injection** for testability
6. **Type everything** for better IDE support and error catching
7. **Document complex logic** with clear docstrings
8. **Follow naming conventions** consistently
