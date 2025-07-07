# Unit Test Specification for src/core/config.py

This document defines the unit tests for the configuration management module (`src/core/config.py`), which provides type-safe configuration with validation, environment variable support, and cloud provider auto-detection.

## Test Organization

Tests will be organized into the following test classes, each marked with `@pytest.mark.unit`:

1. `TestLogConfig` - Tests for the LogConfig model
2. `TestObservabilityConfig` - Tests for the ObservabilityConfig model
3. `TestDatabaseConfig` - Tests for the DatabaseConfig model
4. `TestSettings` - Tests for the main Settings class
5. `TestGetSettings` - Tests for the get_settings function and caching
6. `TestGetConfigDefaults` - Tests for the get_config_defaults helper

## Required Fixtures (to be added to conftest.py)

### 1. `clean_lru_cache` (autouse=True)

- **Purpose**: Clear the LRU cache before and after each test to ensure isolation
- **Implementation**: Call `get_settings.cache_clear()` directly in setup and teardown
- **Best Practices**: Ensures test isolation, prevents side effects

### 2. `clean_env` (autouse=True)

- **Purpose**: Backup and restore environment variables to prevent test interference
- **Implementation**: Extend existing `isolated_env` fixture or use monkeypatch to save/restore os.environ
- **Best Practices**: Ensures test isolation, clean up, order independence

### 3. `temp_env_file`

- **Purpose**: Create temporary .env files for testing file-based configuration
- **Implementation**: Use tmp_path fixture to create temporary files
- **Best Practices**: No side effects, proper cleanup

### 4. `mock_cloud_env`

- **Purpose**: Mock cloud environment detection (GCP/AWS)
- **Implementation**: Use pytest_mock to set environment variables
- **Best Practices**: Type safety, clear test intent

## Test Specifications

### TestLogConfig

#### Test: test_default_values

- **Purpose**: Verify LogConfig initializes with correct default values
- **Assertions**: Check all fields have expected defaults (log_level="INFO", etc.)
- **Best Practices**: Clear assertions, no mocking needed

#### Test: test_field_validation

- **Purpose**: Verify field constraints are enforced
- **Parametrization**: Test invalid values for slow_request_threshold_ms (<=0), slow_query_threshold_ms (<=0)
- **Assertions**: Verify ValidationError is raised with specific error messages
- **Best Practices**: Error message verification, parametrization

#### Test: test_log_level_enum_validation

- **Purpose**: Verify only valid log levels are accepted
- **Parametrization**: Test valid levels (DEBUG, INFO, etc.) and invalid levels
- **Assertions**: Valid levels work, invalid raise ValidationError
- **Best Practices**: Parametrization, clear assertions

#### Test: test_formatter_type_enum_validation

- **Purpose**: Verify only valid formatter types are accepted
- **Parametrization**: Test valid types (console, json, gcp, aws, None) and invalid
- **Assertions**: Valid types work, invalid raise ValidationError
- **Best Practices**: Parametrization, type safety

### TestObservabilityConfig

#### Test: test_default_values

- **Purpose**: Verify ObservabilityConfig defaults are correct
- **Assertions**: Check enable_tracing=True, exporter_type="console", etc.
- **Best Practices**: Clear assertions, implementation detail avoidance

#### Test: test_empty_str_to_none_validator

- **Purpose**: Verify empty strings are converted to None for nullable fields
- **Parametrization**: Test exporter_endpoint and gcp_project_id with "", None, and valid values
- **Assertions**: Empty strings become None, others unchanged
- **Best Practices**: Parametrization, behavior verification

#### Test: test_trace_sample_rate_validation

- **Purpose**: Verify trace_sample_rate constraints (0.0-1.0)
- **Parametrization**: Test boundary values (0.0, 1.0) and invalid (-0.1, 1.1)
- **Assertions**: Valid rates accepted, invalid raise ValidationError
- **Best Practices**: Boundary testing, error verification

#### Test: test_exporter_type_enum_validation

- **Purpose**: Verify only valid exporter types accepted
- **Parametrization**: Test all valid types and invalid ones
- **Assertions**: Valid types work, invalid raise ValidationError
- **Best Practices**: Comprehensive coverage, parametrization

### TestDatabaseConfig

#### Test: test_default_values

- **Purpose**: Verify DatabaseConfig defaults are correct
- **Assertions**: Check database_url, pool_size=10, etc.
- **Best Practices**: Clear assertions, no implementation details

#### Test: test_database_url_validation

- **Purpose**: Verify only postgresql+asyncpg URLs are accepted
- **Parametrization**: Test valid asyncpg URLs and invalid (postgresql://, mysql://, etc.)
- **Assertions**: Valid URLs accepted, others raise ValueError with specific message
- **Best Practices**: Error message verification, parametrization

#### Test: test_pool_configuration_validation

- **Purpose**: Verify pool configuration constraints
- **Parametrization**: Test valid and invalid values for pool_size (1-100), max_overflow (0-50), pool_timeout (>0, <=300)
- **Assertions**: Valid values accepted, invalid raise ValidationError
- **Best Practices**: Boundary testing, comprehensive coverage

#### Test: test_get_test_database_url

- **Purpose**: Verify test database URL generation
- **Parametrization**: Test various URL formats (with /tributum_db, /tributum, custom names, with query params, URLs without database name)
- **Assertions**: Correct test database name substitution, edge cases handled properly
- **Best Practices**: Behavior verification, edge case handling, comprehensive coverage

### TestSettings

#### Test: test_default_initialization

- **Purpose**: Verify Settings initializes with all defaults
- **Fixture**: Use clean_env to ensure no environment interference
- **Assertions**: All fields have expected default values
- **Best Practices**: Isolation, comprehensive assertions

#### Test: test_env_file_loading

- **Purpose**: Verify .env file is loaded correctly
- **Fixture**: Use temp_env_file to create temporary .env
- **Mock**: Mock file system to point to temp file
- **Assertions**: Values from .env are loaded
- **Best Practices**: No side effects, file system mocking with pytest_mock

#### Test: test_environment_variable_override

- **Purpose**: Verify env vars override defaults and .env file
- **Fixture**: Use clean_env to set specific env vars
- **Parametrization**: Test various env var combinations
- **Assertions**: Env vars take precedence
- **Best Practices**: Isolation, clear precedence testing

#### Test: test_nested_delimiter_support

- **Purpose**: Verify __ delimiter works for nested configs
- **Fixture**: Set env vars like LOG_CONFIG__LOG_LEVEL
- **Assertions**: Nested values are set correctly
- **Best Practices**: Feature behavior verification

#### Test: test_empty_str_to_none_validator

- **Purpose**: Verify empty strings become None for URL fields
- **Parametrization**: Test docs_url, redoc_url, openapi_url with empty strings
- **Assertions**: Empty strings converted to None
- **Best Practices**: Validator behavior verification

#### Test: test_model_post_init_development

- **Purpose**: Verify post-init logic for development environment
- **Assertions**: Formatter stays None or becomes "console", exporter stays "console"
- **Best Practices**: Environment-specific behavior testing

#### Test: test_model_post_init_production

- **Purpose**: Verify post-init logic for production environment
- **Parametrization**: Test with and without cloud env vars
- **Assertions**: Correct formatter/exporter selection, sample rate adjustment
- **Best Practices**: Complex logic verification, cloud detection

#### Test: test_detect_formatter_logic

- **Purpose**: Verify formatter auto-detection
- **Fixture**: Mock cloud environment variables
- **Parametrization**: Test K_SERVICE (GCP), AWS_EXECUTION_ENV (AWS), none (default)
- **Assertions**: Correct formatter selected
- **Best Practices**: Private method testing through public API

#### Test: test_detect_exporter_logic

- **Purpose**: Verify exporter auto-detection
- **Fixture**: Mock cloud environment variables
- **Parametrization**: Test various cloud environments
- **Assertions**: Correct exporter selected
- **Best Practices**: Cloud detection verification

#### Test: test_model_config_attributes

- **Purpose**: Verify Settings model_config is properly configured
- **Assertions**: Verify env_file=".env", case_sensitive=False, env_nested_delimiter="__", etc.
- **Best Practices**: Configuration validation

#### Test: test_cloud_env_conflict

- **Purpose**: Verify behavior when both GCP and AWS env vars are set
- **Fixture**: Set both K_SERVICE and AWS_EXECUTION_ENV
- **Assertions**: GCP takes precedence (first check in code)
- **Best Practices**: Edge case handling, precedence testing

#### Test: test_malformed_env_file

- **Purpose**: Verify graceful handling of malformed .env files
- **Fixture**: Create .env with invalid syntax
- **Assertions**: Error is handled appropriately or defaults are used
- **Best Practices**: Error handling verification

#### Test: test_case_sensitivity

- **Purpose**: Verify environment variables are case-insensitive
- **Parametrization**: Test APP_NAME, app_name, App_Name
- **Assertions**: All variations work correctly
- **Best Practices**: Configuration flexibility verification

### TestGetSettings

#### Test: test_returns_settings_instance

- **Purpose**: Verify get_settings returns Settings instance
- **Assertions**: Return type is Settings
- **Best Practices**: Type verification

#### Test: test_caching_behavior

- **Purpose**: Verify settings instance is cached
- **Mock**: Track Settings instantiation calls
- **Assertions**: Multiple calls return same instance
- **Best Practices**: Performance optimization verification

#### Test: test_cache_clearing

- **Purpose**: Verify cache can be cleared
- **Mock**: Track cache clearing
- **Assertions**: New instance after cache clear
- **Best Practices**: Cache management verification

#### Test: test_thread_safety

- **Purpose**: Verify get_settings is thread-safe
- **Fixture**: Use thread_sync from core conftest
- **Implementation**: Multiple threads calling get_settings concurrently, use threading.Event for synchronization
- **Assertions**: All threads get same instance, no race conditions, no errors
- **Best Practices**: Thread safety, proper cleanup with timeout, race condition testing

### TestGetConfigDefaults

#### Test: test_production_defaults

- **Purpose**: Verify correct defaults for production
- **Assertions**: Returns GCP formatter and exporter
- **Best Practices**: Helper function verification

#### Test: test_development_defaults

- **Purpose**: Verify correct defaults for development
- **Assertions**: Returns console formatter and exporter
- **Best Practices**: Environment-specific defaults

#### Test: test_unknown_environment

- **Purpose**: Verify behavior with unknown environment
- **Parametrization**: Test "staging", "test", "custom"
- **Assertions**: Returns development defaults
- **Best Practices**: Edge case handling

## Best Practices Implementation for Each Test

### 1. Async Tests

- All tests will be synchronous as the config module is not async
- No need for async/await or pytest-asyncio markers

### 2. Thread Tests

- Thread safety test for get_settings will use thread_sync fixture
- Proper thread cleanup using thread.join() with timeout
- Results collected in thread-safe list

### 3. Isolation

- autouse fixtures clean_lru_cache and clean_env ensure isolation
- Each test starts with fresh state
- No shared state between tests

### 4. Clean Up

- Fixtures handle all cleanup automatically
- Generator pattern with yield for setup/teardown
- No manual cleanup needed in tests

### 5. Test Order Independence

- No test depends on another test's execution
- Each test sets up its own state
- Random execution order safe

### 6. Implementation Details

- Tests verify public API behavior only
- Private methods (_detect_formatter) tested through public API
- No testing of Pydantic internals

### 7. Timeout

- Inherits 10-second timeout from pytest.ini
- Thread tests have explicit join timeout

### 8. External Dependencies

- No real file I/O - use tmp_path and mocking
- No network calls
- No real environment variables - use monkeypatch

### 9. Mocking

- Exclusively use pytest_mock fixture
- Mock at appropriate boundaries (os.environ, file system)
- Type-safe mocks matching real signatures

### 10. No Side Effects

- No files created in project directory
- No modifications to global state
- All changes reverted by fixtures

### 11. Clear Assertions

- Specific value assertions (assert config.log_level == "INFO")
- Descriptive assertion messages for debugging
- No ambiguous assertions

### 12. Error Messages

- Verify exact error messages from validators
- Use pytest.raises with match parameter
- Test error message content, not just exception type

### 13. Parametrization

- Heavy use of @pytest.mark.parametrize
- Test matrices for combinations
- Clear parameter names

### 14. Fixtures

- All fixtures in conftest.py
- Reusable across multiple test files
- Well-documented purpose

### 15. Test Organization

- Tests grouped by class (TestLogConfig, etc.)
- Related tests together
- Clear test naming

### 16. Test Markers

- Every test class decorated with @pytest.mark.unit
- No integration tests in this file

### 17. No unittest.mock

- Never import unittest.mock
- Always use mocker fixture from pytest_mock
- Consistent mocking approach

### 18. Type Safety

- All mocks respect type signatures - import actual types from src.core.config
- Settings objects have correct types - use real Settings, LogConfig, ObservabilityConfig, DatabaseConfig instances
- Validation of return types - use isinstance() checks where appropriate
- Mock return values match expected types exactly

### 19. Coverage

- Every line of code tested
- All branches covered
- All error conditions tested
- 100% coverage target
