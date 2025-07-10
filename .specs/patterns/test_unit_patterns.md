# Tributum Unit Test Patterns

This document describes the unit testing patterns used in the Tributum project. Follow these patterns when writing new unit tests.

## Test Structure

### Module Organization

Mirror the source code structure exactly:

```
src/core/config.py → tests/unit/core/test_config.py
src/api/middleware/error_handler.py → tests/unit/api/middleware/test_error_handler.py
```

### Test Module Docstring

Start each test module with a docstring:

```python
"""Unit tests for src/core/config.py module.

This module contains comprehensive unit tests for the configuration management
system, including type-safe configuration with validation, environment variable
support, and cloud provider auto-detection.
"""
```

### Test Class Structure

Group related tests in classes:

```python
@pytest.mark.unit
class TestLogConfig:
    """Tests for the LogConfig model."""

    def test_default_values(self) -> None:
        """Verify LogConfig initializes with correct default values."""
        ...
```

## Fixture Patterns

### Shared Fixtures in conftest.py

Create comprehensive fixtures for common test needs:

```python
@pytest.fixture
def mock_settings(monkeypatch: pytest.MonkeyPatch) -> Settings:
    """Provide mock Settings object with required attributes."""
    monkeypatch.setenv("APP_NAME", "TestApp")
    monkeypatch.setenv("APP_VERSION", "1.0.0")
    return Settings()

@pytest.fixture(autouse=True)
def clean_lru_cache() -> Generator[None]:
    """Clear the LRU cache before and after each test."""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
```

### Factory Fixtures

Use factory fixtures for creating test objects:

```python
@pytest.fixture
def repository_factory() -> Callable[[AsyncSession, type[BaseModel]], BaseRepository]:
    """Factory for creating repository instances."""
    def _factory(session: AsyncSession, model: type[BaseModel]) -> BaseRepository:
        return BaseRepository(session, model)
    return _factory
```

### Thread Synchronization Fixtures

For concurrency testing:

```python
@pytest.fixture
def thread_sync() -> dict[str, Any]:
    """Provide thread synchronization utilities."""
    return {
        "barrier": threading.Barrier,
        "event": threading.Event,
        "lock": threading.Lock,
        "create_results": lambda: [],
    }
```

## Mocking Patterns

### Using pytest-mock

Always use MockerFixture for mocking:

```python
def test_something(self, mocker: MockerFixture) -> None:
    """Test with mocked dependencies."""
    mock_logger = mocker.patch("src.module.logger")
    mock_function = mocker.Mock(return_value="test")
```

### Type Hints for Mocks

Use MockType for mock type hints:

```python
def test_with_mock(self, mock_session: MockType) -> None:
    """Test with typed mock."""
    result = cast("MockType", mock_session.execute.return_value)
```

### Spy Pattern

Use spy to track calls while preserving behavior:

```python
def test_caching_behavior(self, mocker: MockerFixture) -> None:
    """Verify settings instance is cached."""
    settings_spy = mocker.spy(Settings, "__new__")
    settings1 = get_settings()
    assert settings_spy.call_count == 1
```

## Test Method Patterns

### Naming Convention

Use descriptive names following the pattern:

```python
def test_<method>_<scenario>_<expected_result>(self) -> None:
    """Test description."""
    ...

# Examples:
def test_get_by_id_found(self) -> None:
def test_update_non_existent_entity(self) -> None:
def test_validation_error_handler_extracts_field_errors(self) -> None:
```

### Arrange-Act-Assert Pattern

Structure tests clearly:

```python
async def test_create_success(self, repository: BaseRepository) -> None:
    """Verify successful entity creation."""
    # Arrange (Setup)
    test_obj = Mock()
    test_obj.id = None

    # Act (Execute)
    result = await repository.create(test_obj)

    # Assert (Verify)
    assert result is test_obj
    assert result.id == 42
```

### Parametrized Tests

Use parametrize for testing multiple scenarios:

```python
@pytest.mark.parametrize(
    ("field", "value", "expected_error"),
    [
        ("slow_request_threshold_ms", 0, "greater than 0"),
        ("slow_request_threshold_ms", -1, "greater than 0"),
        ("slow_query_threshold_ms", 0, "greater than 0"),
    ],
)
def test_field_validation(
    self, field: str, value: int, expected_error: str
) -> None:
    """Verify field constraints are enforced."""
    with pytest.raises(ValidationError) as exc_info:
        LogConfig.model_validate({field: value})
```

## Async Testing

### Async Test Methods

Test async code with async def:

```python
async def test_get_by_id_found(
    self, repository: BaseRepository[User]
) -> None:
    """Test async repository method."""
    result = await repository.get_by_id(1)
    assert result is not None
```

### Timeout Decorator

Prevent hanging tests:

```python
@pytest.mark.timeout(5)
async def test_concurrent_operations(self) -> None:
    """Test with timeout to prevent hanging."""
    ...
```

### Thread Testing with Event Loops

Handle async code in threads properly:

```python
def run_in_thread() -> None:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    result = loop.run_until_complete(async_function())
```

## Assertion Patterns

### Comprehensive Assertions

Verify all aspects of behavior:

```python
# Verify return value
assert result is test_instance
assert result.id == 42

# Verify method calls
mock_session.add.assert_called_once_with(test_obj)
mock_session.flush.assert_called_once()

# Verify logging
mock_logger.info.assert_called_with(
    "Created {} instance with ID: {}", "TestModel", 42
)
```

### Exception Testing

Test error conditions:

```python
with pytest.raises(ValidationError) as exc_info:
    DatabaseConfig(database_url="mysql://invalid")

error_msg = str(exc_info.value)
assert "Database URL must use postgresql+asyncpg:// driver" in error_msg
```

### Mock Call Verification

Use appropriate assertion methods:

```python
# Exact call verification
mock.assert_called_once_with(arg1, arg2)

# Any call with specific arguments
mock.assert_any_call("error.code", error.error_code)

# Call count verification
assert mock.call_count == 3

# Not called verification
mock.assert_not_called()
```

## Edge Case Testing

### Test Boundary Values

```python
@pytest.mark.parametrize(
    ("count", "is_valid"),
    [
        (0, True),     # Minimum
        (50, True),    # Middle
        (100, True),   # Maximum
        (101, False),  # Over limit
        (-1, False),   # Negative
    ],
)
def test_pool_size_validation(self, count: int, is_valid: bool) -> None:
    """Test boundary conditions."""
    ...
```

### Test None and Empty Values

```python
def test_empty_str_to_none_validator(self) -> None:
    """Verify empty strings convert to None."""
    config = ObservabilityConfig(exporter_endpoint="")
    assert config.exporter_endpoint is None

def test_count_with_none_result(self) -> None:
    """Test when scalar returns None."""
    mock_result.scalar.return_value = None
    result = await repository.count()
    assert result == 0
```

## Concurrency Testing

### Thread Safety Tests

```python
def test_concurrent_read_operations(
    self, thread_sync: dict[str, Any]
) -> None:
    """Verify concurrent operations don't interfere."""
    num_threads = 5
    barrier = thread_sync["barrier"](num_threads)
    results = thread_sync["create_results"]()

    def run_operation() -> None:
        barrier.wait()
        # Perform operation
        results.append(result)

    threads = [
        threading.Thread(target=run_operation)
        for _ in range(num_threads)
    ]

    for t in threads:
        t.start()

    for t in threads:
        t.join(timeout=5.0)

    assert len(results) == num_threads
```

## Environment Isolation

### Clean Environment

Use fixtures to ensure test isolation:

```python
@pytest.fixture(autouse=True)
def clean_env(monkeypatch: pytest.MonkeyPatch) -> Generator[pytest.MonkeyPatch]:
    """Backup and restore environment variables."""
    original_env = os.environ.copy()
    yield monkeypatch
    os.environ.clear()
    os.environ.update(original_env)
```

### Monkeypatch for Environment

```python
def test_environment_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test with modified environment."""
    monkeypatch.setenv("APP_NAME", "TestApp")
    monkeypatch.setenv("DEBUG", "false")

    settings = Settings()
    assert settings.app_name == "TestApp"
    assert settings.debug is False
```

## Best Practices

1. **Always use type hints** for all test methods and fixtures
2. **Test one thing per test** - keep tests focused
3. **Use descriptive test names** that explain the scenario
4. **Mock external dependencies** to isolate unit tests
5. **Test edge cases** including None, empty, and boundary values
6. **Use parametrize** for testing multiple similar scenarios
7. **Clean up after tests** using fixtures or finally blocks
8. **Verify all aspects** including return values, side effects, and logging
9. **Use timeouts** for async tests to prevent hanging
10. **Document complex test setups** with comments
