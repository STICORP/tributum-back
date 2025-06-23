# FastAPI Best Practices Validation Guide

This document provides a comprehensive checklist and instructions for validating FastAPI implementations against industry best practices. Use this guide to ensure your FastAPI project follows recommended patterns and conventions.

## 1. Project Structure Validation

### ✅ Check: Domain-Driven Design Structure
- **Requirement**: All domain directories must be inside `src/` folder
- **Validation**: Verify that the project root contains a `src/` directory with all application code

### ✅ Check: Package Organization
Each package/module should contain these files when applicable:
- `router.py` - API endpoints
- `schemas.py` - Pydantic models for request/response
- `models.py` - SQLAlchemy ORM models
- `service.py` - Business logic implementation
- `dependencies.py` - Dependency injection functions
- `constants.py` - Module-specific constants
- `config.py` - Configuration settings
- `utils.py` - Helper functions
- `exceptions.py` - Custom exceptions

**Example Structure**:
```
src/
├── auth/
│   ├── router.py
│   ├── schemas.py
│   ├── models.py
│   ├── service.py
│   ├── dependencies.py
│   └── exceptions.py
├── posts/
│   ├── router.py
│   ├── schemas.py
│   ├── models.py
│   └── service.py
└── main.py
```

## 2. Async/Await Pattern Validation

### ✅ Check: Proper Async Route Usage
- **Rule**: Routes performing I/O operations MUST be async
- **Anti-pattern**: Using synchronous routes for database queries, API calls, or file I/O
- **Correct Pattern**:
```python
# ✅ CORRECT
@router.get("/users/{user_id}")
async def get_user(user_id: int, db: AsyncSession = Depends(get_db)):
    user = await db.get(User, user_id)
    return user

# ❌ INCORRECT
@router.get("/users/{user_id}")
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    return user
```

### ✅ Check: No Blocking Operations in Async Routes
- **Rule**: Never use blocking I/O in async functions
- **Common Violations**:
  - Using `time.sleep()` instead of `asyncio.sleep()`
  - Using synchronous file operations
  - Using synchronous HTTP libraries (requests) instead of httpx/aiohttp

### ✅ Check: CPU-Intensive Task Handling
- **Rule**: CPU-intensive operations should not block the event loop
- **Solution**: Use `ProcessPoolExecutor` or background tasks
```python
# ✅ CORRECT
from concurrent.futures import ProcessPoolExecutor
import asyncio

executor = ProcessPoolExecutor()

@router.post("/process-heavy")
async def process_heavy_task(data: HeavyData):
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(executor, cpu_intensive_task, data)
    return {"result": result}
```

## 3. Pydantic Model Validation

### ✅ Check: Comprehensive Field Validation
- **Rule**: Use Pydantic's validation features extensively
- **Required Validations**:
  - Field constraints (min/max values, regex patterns)
  - Custom validators for complex logic
  - Proper type annotations

```python
# ✅ CORRECT
from pydantic import BaseModel, Field, validator
from datetime import datetime

class UserCreate(BaseModel):
    email: str = Field(..., regex=r'^[\w\.-]+@[\w\.-]+\.\w+$')
    age: int = Field(..., ge=18, le=120)
    username: str = Field(..., min_length=3, max_length=50)

    @validator('username')
    def username_alphanumeric(cls, v):
        assert v.isalnum(), 'must be alphanumeric'
        return v
```

### ✅ Check: Custom Base Model Implementation
- **Rule**: Create a custom base model for shared configurations
```python
# ✅ CORRECT
from pydantic import BaseModel, ConfigDict

class CustomBaseModel(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        validate_assignment=True,
        arbitrary_types_allowed=True,
        str_strip_whitespace=True,
        json_encoders={
            datetime: lambda v: v.isoformat()
        }
    )

# Use in all schemas
class UserSchema(CustomBaseModel):
    id: int
    email: str
    created_at: datetime
```

### ✅ Check: BaseSettings Decoupling
- **Rule**: Don't create a single BaseSettings for the entire application
- **Best Practice**: Create separate settings per module
```python
# ✅ CORRECT - auth/config.py
from pydantic_settings import BaseSettings

class AuthSettings(BaseSettings):
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    class Config:
        env_prefix = "AUTH_"

# ✅ CORRECT - database/config.py
class DatabaseSettings(BaseSettings):
    url: str
    pool_size: int = 10

    class Config:
        env_prefix = "DB_"
```

## 4. Dependency Injection Validation

### ✅ Check: Complex Logic in Dependencies
- **Rule**: Use dependencies for reusable validation and complex logic
- **Anti-pattern**: Repeating validation logic in routes
```python
# ✅ CORRECT
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = await db.get(User, user_id)
    if user is None:
        raise credentials_exception
    return user

# Use in routes
@router.get("/me")
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user
```

### ✅ Check: Dependency Chaining
- **Rule**: Chain dependencies to avoid code duplication
```python
# ✅ CORRECT
async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

async def get_current_admin_user(
    current_user: User = Depends(get_current_active_user)
) -> User:
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return current_user
```

### ✅ Check: Dependency Performance
- **Rule**: Dependencies are cached per request automatically
- **Best Practice**: Expensive operations should be in dependencies
```python
# ✅ CORRECT - Settings loaded once per request
def get_settings() -> Settings:
    return Settings()

@router.get("/config")
async def get_config(settings: Settings = Depends(get_settings)):
    return {"app_name": settings.app_name}
```

## 5. REST API Design Validation

### ✅ Check: RESTful Route Naming
- **Rules**:
  - Use plural nouns for resources
  - Use HTTP methods correctly
  - Follow standard URL patterns

```python
# ✅ CORRECT
@router.get("/users")  # Get all users
@router.get("/users/{user_id}")  # Get specific user
@router.post("/users")  # Create user
@router.put("/users/{user_id}")  # Update user
@router.delete("/users/{user_id}")  # Delete user
@router.get("/users/{user_id}/posts")  # Get user's posts

# ❌ INCORRECT
@router.get("/get-users")
@router.post("/create-user")
@router.get("/user/{id}/get-posts")
```

### ✅ Check: HTTP Status Codes
- **Rule**: Use appropriate status codes
```python
# ✅ CORRECT
@router.post("/users", status_code=201)  # Created
@router.delete("/users/{user_id}", status_code=204)  # No Content
@router.put("/users/{user_id}")  # 200 OK by default
```

## 6. Database and ORM Validation

### ✅ Check: Consistent Naming Convention
- **Rule**: Use a single naming convention across the database
```python
# ✅ CORRECT
from sqlalchemy import MetaData

POSTGRES_INDEXES_NAMING_CONVENTION = {
    "ix": "%(column_0_label)s_idx",
    "uq": "%(table_name)s_%(column_0_name)s_key",
    "ck": "%(table_name)s_%(constraint_name)s_check",
    "fk": "%(table_name)s_%(column_0_name)s_fkey",
    "pk": "%(table_name)s_pkey",
}

metadata = MetaData(naming_convention=POSTGRES_INDEXES_NAMING_CONVENTION)
```

### ✅ Check: SQL-First Approach for Complex Queries
- **Rule**: Use raw SQL for complex data processing
- **When to use**: Aggregations, complex joins, window functions
```python
# ✅ CORRECT for complex aggregations
from sqlalchemy import text

async def get_user_statistics(db: AsyncSession, user_id: int):
    query = text("""
        SELECT
            COUNT(DISTINCT p.id) as post_count,
            COUNT(DISTINCT c.id) as comment_count,
            COALESCE(AVG(p.rating), 0) as avg_post_rating
        FROM users u
        LEFT JOIN posts p ON u.id = p.user_id
        LEFT JOIN comments c ON u.id = c.user_id
        WHERE u.id = :user_id
        GROUP BY u.id
    """)

    result = await db.execute(query, {"user_id": user_id})
    return result.mappings().first()
```

## 7. Testing Validation

### ✅ Check: Async Test Client Usage
- **Rule**: Use `httpx.AsyncClient` for testing async endpoints
```python
# ✅ CORRECT
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_create_user(client: AsyncClient):
    response = await client.post(
        "/users",
        json={"email": "test@example.com", "password": "testpass"}
    )
    assert response.status_code == 201
    assert response.json()["email"] == "test@example.com"
```

## 8. Error Handling Validation

### ✅ Check: ValueError to ValidationError Conversion
- **Rule**: Convert ValueErrors to Pydantic ValidationErrors for proper API responses
```python
# ✅ CORRECT
from pydantic import ValidationError

@router.post("/process")
async def process_data(data: ProcessRequest):
    try:
        result = process_complex_logic(data)
    except ValueError as e:
        raise ValidationError.from_exception_data(
            "ValueError",
            [{"type": "value_error", "loc": ("body",), "msg": str(e)}]
        )
    return result
```

## 9. Performance Validation

### ✅ Check: Thread Pool for Sync Operations
- **Rule**: Use thread pool for synchronous third-party SDKs
```python
# ✅ CORRECT
import asyncio
from concurrent.futures import ThreadPoolExecutor

thread_pool = ThreadPoolExecutor()

@router.post("/send-email")
async def send_email(email_data: EmailSchema):
    loop = asyncio.get_running_loop()
    # boto3 is synchronous
    await loop.run_in_executor(
        thread_pool,
        send_email_via_boto3,
        email_data
    )
    return {"status": "sent"}
```

### ✅ Check: Response Model Usage
- **Rule**: Always use response_model for automatic serialization and validation
```python
# ✅ CORRECT
@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: int, db: AsyncSession = Depends(get_db)):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user  # Automatically serialized to UserResponse
```

## 10. Documentation Validation

### ✅ Check: API Documentation Customization
- **Rule**: Provide comprehensive API documentation
```python
# ✅ CORRECT
@router.post(
    "/users",
    response_model=UserResponse,
    status_code=201,
    summary="Create a new user",
    description="Create a new user with the provided email and password",
    response_description="The created user",
    responses={
        409: {"description": "User with this email already exists"},
        422: {"description": "Validation error"}
    }
)
async def create_user(user: UserCreate, db: AsyncSession = Depends(get_db)):
    """
    Create a new user with the following information:

    - **email**: A valid email address
    - **password**: A strong password (min 8 characters)
    - **full_name**: Optional full name of the user
    """
    # Implementation
```

## 11. Code Quality Validation

### ✅ Check: Linting Configuration
- **Rule**: Use Ruff for Python linting
- **Required Configuration**:
```toml
# pyproject.toml
[tool.ruff]
target-version = "py311"
line-length = 88
select = [
    "E",  # pycodestyle errors
    "W",  # pycodestyle warnings
    "F",  # pyflakes
    "I",  # isort
    "B",  # flake8-bugbear
    "C4", # flake8-comprehensions
    "UP", # pyupgrade
]
ignore = []

[tool.ruff.per-file-ignores]
"__init__.py" = ["F401"]
```

## Validation Checklist Summary

Use this checklist to validate FastAPI implementations:

1. **Structure**: ✅ `src/` folder exists with proper package organization
2. **Async**: ✅ I/O operations use async/await, no blocking calls
3. **Pydantic**: ✅ Comprehensive validation, custom base model, decoupled settings
4. **Dependencies**: ✅ Complex logic extracted, proper chaining, async preferred
5. **REST**: ✅ RESTful naming, appropriate status codes
6. **Database**: ✅ Consistent naming, SQL-first for complex queries
7. **Testing**: ✅ Async test client used
8. **Errors**: ✅ ValueErrors converted to ValidationErrors
9. **Performance**: ✅ Thread pools for sync SDKs, response models used
10. **Documentation**: ✅ Comprehensive API docs with examples
11. **Quality**: ✅ Ruff configured and passing

## How to Use This Guide

1. **For Code Reviews**: Go through each section and verify compliance
2. **For Development**: Reference the correct patterns when implementing features
3. **For Refactoring**: Identify anti-patterns and replace with best practices
4. **For LLM Validation**: Use the checklist to systematically verify implementation quality

Remember: These practices are guidelines. Always consider your specific use case and adjust accordingly while maintaining the core principles of clean, maintainable, and performant code.
