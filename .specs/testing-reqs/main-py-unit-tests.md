# Unit Test Specification for main.py

## Overview

This document specifies the unit tests required for `main.py`, the entry point for the Tributum FastAPI application. The file orchestrates application startup, including configuration loading, logging setup, and Uvicorn server initialization.

## Understanding of main.py

The `main.py` file performs the following operations:

1. Imports required dependencies (os, uvicorn, logger, app, get_settings, setup_logging)
2. Defines a `main()` function that:
   - Retrieves application settings via `get_settings()`
   - Sets up logging via `setup_logging(settings)`
   - Determines the port to use (from PORT env var or settings.api_port)
   - Configures uvicorn logging to use InterceptHandler
   - Starts uvicorn in either development mode (with reload) or production mode
3. Executes `main()` when run as a script

## Available Fixtures

Based on the analysis of existing fixtures:

### From tests/conftest.py

- **pytest markers**: `unit` and `integration` markers configured

### From tests/unit/core/conftest.py

- **clean_context**: Auto-fixture that ensures RequestContext is clean before/after tests
- **deterministic_uuid**: Makes UUID generation predictable for tests
- **thread_sync**: Provides thread synchronization helpers
- **memory_monitor**: Monitors memory usage for leak detection
- **event_loop**: Provides asyncio event loop (though not needed for main.py)

### New Fixtures Needed

A new conftest.py file will be created at `tests/unit/` to provide fixtures specific to main.py testing.

## Test Specifications

### Test Class: TestMainFunction

All tests will be organized in a class marked with `@pytest.mark.unit` decorator.

#### Test 1: test_main_loads_settings_and_sets_up_logging

**Purpose**: Verify that main() correctly loads settings and initializes logging.

**Test Behavior**:

- Mock `get_settings` to return a mock settings object
- Mock `setup_logging` to track calls
- Mock `uvicorn.run` to prevent actual server startup
- Call `main()`
- Assert `get_settings` was called once
- Assert `setup_logging` was called once with the mock settings

**Best Practices Implementation**:

- **Async**: Not needed - main() is synchronous
- **Thread Safety**: No threads involved
- **Isolation**: All external dependencies mocked
- **Clean Up**: Mocks automatically cleaned by pytest_mock
- **Order Independence**: No shared state
- **Behavior Verification**: Tests the coordination behavior, not implementation
- **Timeout**: Default 10s timeout sufficient
- **External Dependencies**: All mocked (settings, logging, uvicorn)
- **Mocking**: Uses pytest_mock fixture exclusively
- **No Side Effects**: No actual server started or logs created
- **Clear Assertions**: Specific call counts and arguments verified
- **Type Safety**: Mock settings will match Settings type signature

#### Test 2: test_main_uses_cloud_run_port_when_available

**Purpose**: Verify PORT environment variable takes precedence over settings.

**Test Behavior**:

- Set PORT environment variable to "8080"
- Mock settings with api_port=3000
- Mock uvicorn.run
- Call main()
- Assert uvicorn.run called with port=8080

**Best Practices Implementation**:

- **Async**: Not needed
- **Thread Safety**: No threads involved
- **Isolation**: Uses monkeypatch for env var isolation
- **Clean Up**: monkeypatch automatically restores environment
- **Order Independence**: Environment restored after test
- **Behavior Verification**: Tests port selection logic
- **Timeout**: Default timeout sufficient
- **External Dependencies**: All mocked
- **Mocking**: pytest_mock for uvicorn, monkeypatch for env
- **No Side Effects**: No actual server started
- **Clear Assertions**: Verifies exact port value used
- **Type Safety**: Port values as integers

#### Test 3: test_main_uses_settings_port_when_no_env_port

**Purpose**: Verify settings.api_port is used when PORT env var is not set.

**Test Behavior**:

- Ensure PORT env var is not set
- Mock settings with api_port=3000
- Mock uvicorn.run
- Call main()
- Assert uvicorn.run called with port=3000

**Best Practices Implementation**:

- Similar to Test 2 but without setting PORT env var
- **Isolation**: Ensures PORT is not set using monkeypatch.delenv if exists

#### Test 4: test_main_configures_uvicorn_logging_correctly

**Purpose**: Verify uvicorn logging configuration structure.

**Test Behavior**:

- Mock uvicorn.run
- Call main()
- Capture the log_config argument passed to uvicorn.run
- Assert log_config has correct structure:
  - version: 1
  - disable_existing_loggers: False
  - handlers with InterceptHandler
  - loggers for uvicorn, uvicorn.error, uvicorn.access

**Best Practices Implementation**:

- **Async**: Not needed
- **Thread Safety**: No threads
- **Isolation**: All mocked
- **Clean Up**: Automatic
- **Order Independence**: No shared state
- **Behavior Verification**: Tests configuration structure
- **Clear Assertions**: Deep dictionary comparison
- **Type Safety**: Dict structure matches uvicorn expectations

#### Test 5: test_main_debug_mode_enables_reload

**Purpose**: Verify debug mode behavior with reload enabled.

**Test Behavior**:

- Mock settings with debug=True
- Mock uvicorn.run
- Mock logger.info
- Call main()
- Assert uvicorn.run called with:
  - app as string "src.api.main:app"
  - reload=True
  - Correct host/port
- Assert logger.info called with development mode message

**Best Practices Implementation**:

- **Async**: Not needed
- **Thread Safety**: No threads
- **Isolation**: All external calls mocked
- **Behavior Verification**: Tests debug mode behavior branch
- **Clear Assertions**: Verifies exact arguments and log message
- **Parametrization**: Will be combined with Test 6 using parametrize

#### Test 6: test_main_production_mode_disables_reload

**Purpose**: Verify production mode behavior without reload.

**Test Behavior**:

- Mock settings with debug=False
- Mock uvicorn.run
- Mock logger.info
- Import app object and mock it
- Call main()
- Assert uvicorn.run called with:
  - app object directly (not string)
  - reload=False
  - Correct host/port
- Assert logger.info called with production mode message

**Best Practices Implementation**:

- Similar to Test 5 but for production mode
- **Parametrization**: Tests 5 and 6 will use @pytest.mark.parametrize

#### Test 7: test_main_parametrized_debug_modes

**Purpose**: Replace Tests 5 and 6 with a single parametrized test for better test efficiency.

**Test Behavior**:

- Use @pytest.mark.parametrize("debug,expected_app,expected_reload,expected_log_msg", [
    (True, "src.api.main:app", True, "development mode with auto-reload"),
    (False, app_object, False, "production mode")
  ])
- Test both branches in a single parametrized test
- Verify correct behavior for each mode

**Best Practices Implementation**:

- **Parametrization**: Tests multiple inputs with single test
- **Clear Assertions**: Mode-specific assertions using parametrized expected values
- All other practices as in Tests 5 and 6

**Note**: This test replaces Tests 5 and 6 for efficiency

#### Test 8: test_main_module_execution

**Purpose**: Verify the if **name** == "**main**" block.

**Test Behavior**:

- Mock the main function
- Use runpy.run_module or exec to execute main.py
- Assert main() was called once

**Best Practices Implementation**:

- **Async**: Not needed
- **Thread Safety**: No threads
- **Isolation**: Mock main function to prevent execution
- **Clean Up**: Automatic
- **Order Independence**: Isolated execution
- **Behavior Verification**: Tests module execution guard
- **No Side Effects**: No actual execution
- **Clear Assertions**: Verify main() called exactly once

#### Test 9: test_port_environment_variable_type_conversion

**Purpose**: Verify PORT env var is correctly converted to integer.

**Test Behavior**:

- Set PORT="9999" as string
- Mock uvicorn.run
- Call main()
- Assert uvicorn.run receives port as integer 9999, not string

**Best Practices Implementation**:

- **Type Safety**: Ensures string->int conversion
- **Clear Assertions**: Type checking on port argument
- **Error Messages**: If conversion fails, helpful error

#### Test 10: test_invalid_port_environment_variable

**Purpose**: Verify behavior with invalid PORT value raises appropriate error.

**Test Behavior**:

- Set PORT="invalid" (non-numeric string)
- Call main()
- Assert ValueError is raised by int() conversion
- Verify error message contains "invalid literal for int()"

**Best Practices Implementation**:

- **Error Messages**: Verify the natural ValueError from int()
- **Clear Assertions**: Uses pytest.raises with match pattern for "invalid literal"
- **Behavior Verification**: Tests error propagation (no try/except in code)
- **No Side Effects**: Error raised before any server startup

#### Test 11: test_empty_port_environment_variable

**Purpose**: Verify behavior when PORT is empty string.

**Test Behavior**:

- Set PORT="" (empty string)
- Mock settings with api_port=3000
- Call main()
- Since os.environ.get("PORT", default) returns "" (not None), int("") will raise ValueError
- Assert ValueError is raised with message about empty string

**Best Practices Implementation**:

- **Edge Cases**: Tests empty string scenario
- **Error Messages**: Verify ValueError for empty string to int conversion
- **Clear Assertions**: Specific error pattern matching
- **Behavior Verification**: Tests actual behavior of os.environ.get with empty values

## Fixtures Required

### New conftest.py at tests/unit/conftest.py

1. **mock_settings**: Fixture providing mock Settings object with required attributes:
   - `api_host`: str = "0.0.0.0"
   - `api_port`: int = 3000
   - `debug`: bool = False
   - Type must match the actual Settings class for type safety

2. **mock_app**: Fixture providing mock FastAPI app instance
   - Must be a MagicMock that can be passed to uvicorn.run

3. **mock_uvicorn**: Fixture that mocks uvicorn.run to prevent server startup
   - Uses mocker.patch on "uvicorn.run"
   - Returns the mock for assertion purposes

4. **isolated_env**: Fixture using monkeypatch to isolate environment variables
   - Ensures PORT is not set unless explicitly required by test
   - Cleans up any test-set environment variables

## Test Organization

```
tests/unit/
├── conftest.py  # New fixture file
└── test_main.py  # Test file for main.py
```

All tests in `test_main.py` will be:

- Organized in a `TestMainFunction` class
- Marked with `@pytest.mark.unit`
- Use only pytest_mock fixture, never unittest.mock
- Achieve 100% code coverage for main.py

## Coverage Considerations

To achieve 100% coverage:

- Both debug=True and debug=False branches must be tested
- PORT environment variable present and absent cases
- The if **name** == "**main**" block must be tested
- All lines in the log_config dictionary must be executed
- Both logger.info calls must be verified

## Mock Strategy

All external dependencies will be mocked:

- `get_settings()` - Returns mock Settings object
- `setup_logging()` - Prevents actual logging setup
- `uvicorn.run()` - Prevents server startup
- `logger.info()` - Captures log messages
- `os.environ.get()` - Controlled via monkeypatch
- `app` import - Mocked when needed for production mode

## Type Safety Considerations

All mocks will respect type signatures:

- Mock settings will have all required attributes
- Port values will be integers
- Log config will match uvicorn's expected structure
- All function signatures will match the real implementations
