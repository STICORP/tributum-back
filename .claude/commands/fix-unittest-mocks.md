# /fix-unittest-mocks

## Your Task

- Replace unittest.mock with pytest-mock in $ARGUMENTS
- Think harder

## General Instructions for Replacing unittest.mock with pytest-mock

### FORBIDDEN PRACTICES (Will cause mypy failures)

1. **NEVER use `if TYPE_CHECKING`** - This is strictly forbidden
2. **NEVER use `Any` type** - mypy will complain. Always research and use the proper concrete type
3. **NEVER use `cast()`** - Proper typing eliminates the need for casting
4. **NEVER leave types unspecified** - Every variable, parameter, and return type must be properly typed

### 1. Import Changes

**Remove these imports:**
```python
from unittest.mock import MagicMock, Mock, AsyncMock, patch, call
from typing import TYPE_CHECKING, cast, Any  # FORBIDDEN - remove all of these
```

**Add/keep these imports:**
```python
from pytest_mock import MockerFixture
# Import the actual types being mocked - REQUIRED for proper typing
from sqlalchemy.ext.asyncio import AsyncSession  # Example: actual interface type
from some.module import ConcreteType  # Always import the real types, never use Any
```

### 2. Type Annotation Changes (CRITICAL for mypy compliance)

**FORBIDDEN - Using mock types or Any:**
```python
def test_something(mock_obj: MagicMock) -> None:  # WRONG - mypy will fail
def test_something(mock_obj: Any) -> None:  # FORBIDDEN - never use Any
def test_something(mock_obj) -> None:  # WRONG - missing type annotation
```

**REQUIRED - Use the actual interface type:**
```python
def test_something(mock_obj: AsyncSession) -> None:  # CORRECT - proper concrete type
def test_something(mock_obj: UserRepository) -> None:  # CORRECT - actual class type
```

### 3. Creating Mocks (with proper typing)

**FORBIDDEN - Untyped or cast usage:**
```python
mock = MagicMock(spec=SomeClass)  # WRONG - no type annotation
mock = cast("SomeClass", mock)  # FORBIDDEN - never use cast
mock: Any = mocker.MagicMock()  # FORBIDDEN - never use Any
```

**REQUIRED - Properly typed mock creation:**
```python
# Always include type annotation with concrete type
mock: SomeClass = mocker.MagicMock(spec=SomeClass)
# For async interfaces:
mock: AsyncSession = mocker.AsyncMock(spec=AsyncSession)
# For custom classes:
mock: UserService = mocker.MagicMock(spec=UserService)
```

### 4. Fixing Mock Assertions (CRITICAL for mypy)

The main mypy issue is that when you patch methods on a mock, mypy doesn't know about assertion methods like `assert_called_once()`.

**Instead of:**
```python
mocker.patch.object(mock_session, "execute", mocker.AsyncMock(return_value=result))
# ...
mock_session.execute.assert_called_once()  # mypy error: no attribute "assert_called_once"
```

**Use:**
```python
# Keep a reference to the patched method
mock_execute = mocker.patch.object(mock_session, "execute", mocker.AsyncMock(return_value=result))
# ...
mock_execute.assert_called_once()  # No mypy error!
```

### 5. Common Patterns

#### Pattern 1: Fixture that returns a mock
```python
@pytest.fixture
def mock_session(mocker: MockerFixture) -> AsyncSession:
    """Create a properly mocked async session."""
    mock: AsyncSession = mocker.AsyncMock(spec=AsyncSession)
    return mock
```

#### Pattern 2: Multiple patches with assertions
```python
# Always keep references when you need to assert
mock_add = mocker.patch.object(session, "add", mocker.MagicMock())
mock_flush = mocker.patch.object(session, "flush", mocker.AsyncMock())
mock_refresh = mocker.patch.object(session, "refresh", mocker.AsyncMock())

# Later assertions work without mypy errors
mock_add.assert_called_once()
mock_flush.assert_called_once()
mock_refresh.assert_called_once()
```

#### Pattern 3: Mocking with side effects
```python
def side_effect_func(obj: MyType) -> None:
    obj.id = 42

mock_method = mocker.patch.object(
    target,
    "method_name",
    mocker.AsyncMock(side_effect=side_effect_func)
)
```

### 6. Removing cast() calls

**Never do:**
```python
repo = BaseRepository(cast("AsyncSession", mock_session), Model)
```

**Instead:**
```python
repo = BaseRepository(mock_session, Model)  # mock_session is already typed as AsyncSession
```

### 7. Complete Example Transformation

**Before (unittest.mock with FORBIDDEN practices):**
```python
from typing import TYPE_CHECKING, cast, Any  # FORBIDDEN imports
from unittest.mock import MagicMock

if TYPE_CHECKING:  # FORBIDDEN - never use TYPE_CHECKING
    from sqlalchemy.ext.asyncio import AsyncSession

async def test_example(mock_session: MagicMock) -> None:  # WRONG type
    mock_result = MagicMock()  # Missing type annotation
    mock_session.execute = AsyncMock(return_value=mock_result)  # Direct assignment

    # FORBIDDEN - using cast
    service = MyService(cast("AsyncSession", mock_session))
    await service.do_something()

    # Will fail mypy - no assert_called_once on mock_session.execute
    mock_session.execute.assert_called_once()
```

**After (pytest-mock with PROPER typing):**
```python
# Only necessary imports - no TYPE_CHECKING, cast, or Any
from pytest_mock import MockerFixture
from sqlalchemy.ext.asyncio import AsyncSession
from myapp.services import MyService  # Import all concrete types

async def test_example(mock_session: AsyncSession, mocker: MockerFixture) -> None:
    # Properly typed mock result
    mock_result: dict[str, str] = mocker.MagicMock()  # Research actual return type

    # Keep reference for assertions
    mock_execute = mocker.patch.object(
        mock_session,
        "execute",
        mocker.AsyncMock(return_value=mock_result)
    )

    # No cast needed - mock_session is already typed as AsyncSession
    service = MyService(mock_session)
    await service.do_something()

    # Works with mypy - using the patch reference
    mock_execute.assert_called_once()
```

### 8. Debugging Tips

1. **"overloaded function has no attribute"** - You're asserting on the mock directly. Keep a reference to the patch:
   ```python
   # WRONG
   mock_session.execute.assert_called_once()

   # CORRECT
   mock_execute = mocker.patch.object(mock_session, "execute", ...)
   mock_execute.assert_called_once()
   ```

2. **"Incompatible type 'Any'"** - Never use Any. Research the actual type:
   ```python
   # WRONG
   result: Any = mocker.MagicMock()

   # CORRECT - find the real type
   result: list[User] = mocker.MagicMock()
   ```

3. **"Argument has incompatible type MagicMock"** - Use the interface type:
   ```python
   # WRONG
   def helper(session: MagicMock) -> None:

   # CORRECT
   def helper(session: AsyncSession) -> None:
   ```

4. **Run `make all-checks` after EVERY change** - Catch mypy errors immediately

### 9. Key Rules for mypy Success

1. **EVERY variable needs a type annotation** - No exceptions
2. **NEVER use forbidden imports** - TYPE_CHECKING, cast, Any
3. **ALWAYS keep patch references** - For assertion methods
4. **RESEARCH actual types** - Don't guess, look at the source code
5. **Import concrete types** - From the actual modules, not typing
