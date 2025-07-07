# Unit Test Specification: src/core/context.py

## Overview

This document defines comprehensive unit tests for `src/core/context.py`, which provides thread-safe and async-safe context management using Python's contextvars for distributed tracing and correlation ID propagation.

## Module Understanding

The `src/core/context.py` module contains:

1. **RequestContext class** - Static methods for managing correlation ID context:
   - `set_correlation_id(correlation_id: str)` - Sets correlation ID in current context
   - `get_correlation_id() -> str | None` - Retrieves correlation ID from current context
   - `clear()` - Clears all context variables (sets correlation ID to None)

2. **Helper functions**:
   - `generate_correlation_id() -> str` - Generates UUID4 string for correlation tracking
   - `generate_request_id() -> str` - Generates prefixed UUID4 string ("req-<uuid>") for request tracking

3. **Core mechanism**: Uses `contextvars.ContextVar` for thread-safe and async-safe storage of correlation ID

## Test Structure

All tests will be organized in a single test class `TestCoreContext` marked with `@pytest.mark.unit` decorator. Each test method will be async unless there's a specific reason to be synchronous.

## Required Fixtures

### Existing Fixtures to Use

- `thread_sync` - For testing thread safety and synchronization
- `clean_env` (autouse) - Ensures environment isolation between tests
- `clean_lru_cache` (autouse) - Ensures cache isolation between tests

### New Fixtures Needed

- `clean_context` (autouse) - Ensures context is cleared before and after each test to prevent interference

## Test Definitions

### 1. RequestContext.set_correlation_id() Tests

#### Test: test_set_correlation_id_stores_value

- **Purpose**: Verify that setting a correlation ID stores it correctly in context
- **Method**: Set a correlation ID and verify it can be retrieved
- **Fixtures**: `clean_context`
- **Best Practices Enforcement**:
  - Async test for consistency
  - Clean assertion verifying exact value stored
  - Uses pytest_mock if needed for verification
  - Type safety ensured with proper string handling
  - Test isolation via clean_context fixture
  - Clear, specific assertion message

#### Test: test_set_correlation_id_overwrites_existing

- **Purpose**: Verify that setting a new correlation ID overwrites the previous one
- **Method**: Set initial ID, set new ID, verify only new ID is retrievable
- **Fixtures**: `clean_context`
- **Best Practices Enforcement**:
  - Async test
  - Tests behavior, not implementation details
  - Clear assertions for both old and new values
  - No side effects

#### Test: test_set_correlation_id_with_empty_string

- **Purpose**: Verify that empty string correlation ID is handled correctly
- **Method**: Set empty string as correlation ID and verify it's stored
- **Fixtures**: `clean_context`
- **Best Practices Enforcement**:
  - Edge case testing
  - Async test
  - Clear assertion for empty string handling

### 2. RequestContext.get_correlation_id() Tests

#### Test: test_get_correlation_id_returns_set_value

- **Purpose**: Verify retrieval of previously set correlation ID
- **Method**: Set correlation ID, then get and verify it matches
- **Fixtures**: `clean_context`
- **Best Practices Enforcement**:
  - Async test
  - Clear assertion with specific value comparison
  - Test isolation

#### Test: test_get_correlation_id_returns_none_when_not_set

- **Purpose**: Verify that getting correlation ID returns None when no ID is set
- **Method**: Call get_correlation_id() without setting anything first
- **Fixtures**: `clean_context`
- **Best Practices Enforcement**:
  - Tests default behavior
  - Async test
  - Specific None assertion

#### Test: test_get_correlation_id_returns_none_after_clear

- **Purpose**: Verify that getting correlation ID returns None after context is cleared
- **Method**: Set correlation ID, clear context, verify get returns None
- **Fixtures**: `clean_context`
- **Best Practices Enforcement**:
  - Tests clear functionality integration
  - Async test
  - Sequential behavior verification

### 3. RequestContext.clear() Tests

#### Test: test_clear_removes_correlation_id

- **Purpose**: Verify that clear() removes the correlation ID from context
- **Method**: Set correlation ID, call clear(), verify get() returns None
- **Fixtures**: `clean_context`
- **Best Practices Enforcement**:
  - Tests state change behavior
  - Async test
  - Clear before/after state verification

#### Test: test_clear_idempotent_when_nothing_set

- **Purpose**: Verify that clear() can be called safely when no correlation ID is set
- **Method**: Call clear() without setting anything, verify no errors
- **Fixtures**: `clean_context`
- **Best Practices Enforcement**:
  - Edge case testing
  - Async test
  - No exception assertion

#### Test: test_clear_multiple_calls_safe

- **Purpose**: Verify that multiple clear() calls are safe
- **Method**: Set correlation ID, call clear() multiple times, verify state
- **Fixtures**: `clean_context`
- **Best Practices Enforcement**:
  - Edge case testing
  - Async test
  - Multiple operation safety

### 4. Thread Safety Tests

#### Test: test_context_isolation_between_threads

- **Purpose**: Verify that each thread maintains its own correlation ID context
- **Method**: Start multiple threads, set different correlation IDs in each, use barrier for synchronization, collect results via create_results(), verify isolation
- **Fixtures**: `thread_sync`, `clean_context`
- **Best Practices Enforcement**:
  - Thread safety verification using thread_sync fixture
  - Async test with proper thread synchronization
  - Timeout set appropriately for thread operations
  - Clean up threads after test
  - Clear assertions for each thread's context using collected results
  - Uses barrier for proper synchronization and create_results() for thread-safe result collection

#### Test: test_context_does_not_leak_between_threads

- **Purpose**: Verify that setting correlation ID in one thread doesn't affect other threads
- **Method**: Set correlation ID in one thread, verify other threads see None using barrier synchronization and create_results() for result collection
- **Fixtures**: `thread_sync`, `clean_context`
- **Best Practices Enforcement**:
  - Thread isolation testing
  - Async test with thread coordination
  - Proper thread cleanup
  - Multiple assertion validation using thread-safe result collection

### 5. Async Safety Tests

#### Test: test_context_inheritance_in_async_tasks

- **Purpose**: Verify that correlation ID is inherited by child async tasks
- **Method**: Set correlation ID, create async task, verify child sees same ID
- **Fixtures**: `clean_context`
- **Best Practices Enforcement**:
  - Async context inheritance testing
  - Async test naturally
  - Proper async task cleanup
  - Context propagation verification

#### Test: test_context_isolation_between_async_tasks

- **Purpose**: Verify that async tasks can have independent contexts
- **Method**: Create multiple async tasks with different correlation IDs, verify isolation
- **Fixtures**: `clean_context`
- **Best Practices Enforcement**:
  - Async isolation testing
  - Async test with proper task management
  - Timeout for async operations
  - Multiple task coordination

#### Test: test_context_modification_in_child_task_does_not_affect_parent

- **Purpose**: Verify that child task modifying context doesn't affect parent
- **Method**: Set correlation ID, create child task that modifies it, verify parent unchanged
- **Fixtures**: `clean_context`
- **Best Practices Enforcement**:
  - Async context isolation
  - Parent-child relationship testing
  - Clear assertions for both parent and child states

### 6. generate_correlation_id() Tests

#### Test: test_generate_correlation_id_returns_string

- **Purpose**: Verify function returns a string
- **Method**: Call function and verify return type
- **Fixtures**: None needed
- **Best Practices Enforcement**:
  - Simple type verification
  - Async test for consistency
  - Clear type assertion

#### Test: test_generate_correlation_id_returns_valid_uuid4

- **Purpose**: Verify function returns valid UUID4 format
- **Method**: Call function and validate UUID4 format using uuid.UUID()
- **Fixtures**: None needed
- **Best Practices Enforcement**:
  - Format validation testing
  - Async test
  - Specific UUID4 format verification
  - Exception handling for invalid format

#### Test: test_generate_correlation_id_returns_unique_values

- **Purpose**: Verify function generates unique values on multiple calls
- **Method**: Generate multiple correlation IDs and verify they're different
- **Fixtures**: None needed
- **Parametrization**: Use @pytest.mark.parametrize with count values [2, 5, 10] to test different numbers of generated IDs
- **Best Practices Enforcement**:
  - Uniqueness verification
  - Async test
  - Multiple value comparison
  - Parametrized for different counts to ensure robustness

#### Test: test_generate_correlation_id_length_is_36_characters

- **Purpose**: Verify UUID4 string is exactly 36 characters (standard UUID format)
- **Method**: Generate correlation ID and verify length
- **Fixtures**: None needed
- **Best Practices Enforcement**:
  - Specific format requirement testing
  - Async test
  - Exact length assertion

### 7. generate_request_id() Tests

#### Test: test_generate_request_id_returns_string

- **Purpose**: Verify function returns a string
- **Method**: Call function and verify return type
- **Fixtures**: None needed
- **Best Practices Enforcement**:
  - Type verification
  - Async test
  - Clear type assertion

#### Test: test_generate_request_id_has_req_prefix

- **Purpose**: Verify function returns string starting with "req-"
- **Method**: Call function and verify prefix
- **Fixtures**: None needed
- **Best Practices Enforcement**:
  - Prefix format verification
  - Async test
  - Specific string prefix assertion

#### Test: test_generate_request_id_returns_valid_uuid4_after_prefix

- **Purpose**: Verify the part after "req-" is valid UUID4
- **Method**: Call function, extract UUID part, validate UUID4 format
- **Fixtures**: None needed
- **Best Practices Enforcement**:
  - Format validation testing
  - Async test
  - UUID validation after string manipulation

#### Test: test_generate_request_id_returns_unique_values

- **Purpose**: Verify function generates unique values on multiple calls
- **Method**: Generate multiple request IDs and verify they're different
- **Fixtures**: None needed
- **Parametrization**: Use @pytest.mark.parametrize with count values [2, 5, 10] to test different numbers of generated IDs
- **Best Practices Enforcement**:
  - Uniqueness verification
  - Async test
  - Multiple value comparison
  - Parametrized for different counts to ensure robustness

#### Test: test_generate_request_id_length_is_40_characters

- **Purpose**: Verify request ID is exactly 40 characters ("req-" + 36 char UUID)
- **Method**: Generate request ID and verify total length
- **Fixtures**: None needed
- **Best Practices Enforcement**:
  - Specific format requirement testing
  - Async test
  - Exact length assertion

### 8. Integration and Edge Case Tests

#### Test: test_full_workflow_set_get_clear

- **Purpose**: Verify complete workflow of setting, getting, and clearing correlation ID
- **Method**: Execute full sequence and verify each step
- **Fixtures**: `clean_context`
- **Best Practices Enforcement**:
  - Workflow integration testing
  - Async test
  - Sequential state verification
  - Multiple assertion points

#### Test: test_context_survives_multiple_operations

- **Purpose**: Verify context remains stable through multiple get operations
- **Method**: Set correlation ID, call get() multiple times, verify consistency
- **Fixtures**: `clean_context`
- **Best Practices Enforcement**:
  - Stability testing
  - Async test
  - Multiple operation verification

## Test Implementation Requirements

### Best Practices Implementation

1. **Async Tests**: All tests will be async for consistency with project patterns
2. **Thread Tests**: Will use `thread_sync` fixture for proper thread coordination and cleanup
3. **Isolation**: Each test completely isolated using `clean_context` fixture
4. **Clean Up**: Context cleared automatically between tests
5. **Test Order Independence**: Tests use fixtures to ensure clean state
6. **Implementation vs Behavior**: Tests verify behavior (what happens) not implementation (how it happens)
7. **Timeout**: Async and thread tests will have appropriate timeouts to prevent hanging
8. **External Dependencies**: Pure unit tests with no database, network, or file I/O
9. **Mocking**: pytest_mock fixture will be used exclusively, no unittest.mock imports
10. **No Side Effects**: Tests will not create files, start servers, or have persistent effects
11. **Clear Assertions**: Each test will have specific, clear assertions with meaningful error messages
12. **Error Messages**: When applicable, verify error messages and log outputs
13. **Parametrization**: Use pytest.mark.parametrize for similar tests with different inputs
14. **Fixtures**: Reuse existing fixtures and create minimal new fixtures in conftest.py
15. **Test Organization**: All tests in single TestCoreContext class marked with @pytest.mark.unit
16. **Test Markers**: All tests must have @pytest.mark.unit decorator
17. **Type Safety**: Mock objects and test data will match expected types exactly
18. **Coverage**: Tests designed to achieve 100% code coverage

### Fixture Requirements

#### New Fixture: clean_context (autouse)

- **Purpose**: Clear context before and after each test
- **Implementation**: Call RequestContext.clear() in setup and teardown
- **Location**: tests/unit/conftest.py
- **Scope**: Function level
- **Type Safety**: No return value needed, void fixture

#### Usage of Existing Fixtures

- **thread_sync**: Used for thread safety tests with barrier coordination and results collection
  - Provides: `barrier(n)` for n-thread synchronization, `create_results()` for thread-safe result collection, `event()` and `lock()` for coordination
- **clean_env**: Automatic isolation of environment variables
- **clean_lru_cache**: Automatic cache clearing (may interact with context if settings are involved)

### Coverage Goals

These tests are designed to achieve 100% line coverage for src/core/context.py:

- All RequestContext methods: set_correlation_id, get_correlation_id, clear
- Both helper functions: generate_correlation_id, generate_request_id
- All conditional branches and edge cases
- Thread safety and async safety scenarios
- Error conditions and edge cases

## Quality Validation

Each test specification above addresses the following quality requirements:

1. **pytest_mock Usage**: Specified where mocking is needed and confirmed pytest_mock fixture usage
2. **Fixture Planning**: Identified existing fixtures to reuse and one new fixture to create
3. **Best Practice Enforcement**: Each test explicitly describes how it implements each best practice
4. **No Code in Specification**: All descriptions are in plain language without code implementation
5. **Specific Test Behavior**: Each test clearly describes what behavior is being verified
6. **Thread and Async Safety**: Comprehensive coverage of concurrent execution scenarios
7. **Edge Cases**: Coverage of boundary conditions and error scenarios
8. **Type Safety**: Consideration of type matching and validation
9. **Test Isolation**: Clear plan for preventing test interference
10. **Complete Coverage**: Tests designed to cover all code paths and functionality
