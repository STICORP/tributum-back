# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- /do command for expert-level task execution with quality enforcement guidelines
- McCabe complexity checking (C90) with maximum complexity of 10
- Claude Code slash command for automated GitHub release creation
- Enhanced /readme command with dual-mode operation: comprehensive discovery for initial generation and efficient incremental updates
- /curate-makefile command for intelligent Makefile analysis and improvement
- /analyze-project command for comprehensive project configuration and quality analysis
- JSON logging for staging environment to match production configuration
- pytest-randomly integration for randomized test execution to detect inter-test dependencies
- pytest-check integration for soft assertions that show all test failures at once
- OpenTelemetry observability configuration for distributed tracing control
- OpenTelemetry tracing infrastructure with GCP Cloud Trace integration for distributed tracing

### Changed
- Streamlined CLAUDE.md from 480 to 317 lines while preserving all essential guidance for improved readability
- Enhanced CLAUDE.md with actionable development guidance including specific test commands, error patterns, and debugging tips
- Comprehensive CLAUDE.md rewrite with enhanced development guidance and architectural documentation
- Isolated development tool execution system to prevent dependency conflicts
- Unified command execution through Makefile for CI/CD, pre-commit, and local development
- Regenerated README with comprehensive project documentation following strict current-state-only principles
- Enhanced /readme command with stricter content validation to prevent future-looking documentation
- Enforced stricter type checking by removing ANN401 ignore rule and documenting all Any type usage
- Improved exception handling by removing BLE001 ignore rule and using specific exception types
- Added stricter linting rules (G, INP, T20) for improved code quality and security
- Refactored linting configuration to enable all Ruff rules by default with targeted exclusions
- Updated README with accurate 98% code coverage badge and latest tooling improvements
- Achieved 100% test coverage by adding comprehensive test suites for all edge cases
- Integrated pytest-env for centralized test environment configuration and reduced test boilerplate
- Updated README with comprehensive testing enhancements and configuration documentation

### Fixed
- Type safety issue in request logging test
- Import organization and type annotation linting issues
- RequestContext test isolation issue exposed by randomized test ordering

### Security
- Updated urllib3 to 2.5.0 to address security vulnerabilities

## [0.2.0] - 2025-06-17

### Added
- Initial project structure with FastAPI framework
- Configuration management using Pydantic Settings v2
- Exception infrastructure with severity levels and context support
- Structured logging with structlog and correlation ID support
- RequestContextMiddleware for request tracking
- High-performance JSON serialization with ORJSONResponse
- Comprehensive development tooling (ruff, mypy, pre-commit hooks)
- Security scanning with bandit, safety, pip-audit, and semgrep
- Test infrastructure with pytest and coverage reporting
- Domain-driven design structure (planned)
- Project metadata and semantic versioning setup
- Automated changelog updates in commit workflow
- Security headers middleware with configurable HSTS support
- Request logging middleware with comprehensive sanitization for observability
- Claude Code slash command for enforcing quality standards without bypasses
- Request/response body logging with automatic sensitive data sanitization
- Global exception handling with standardized error responses and full context logging
- HTTP request context capture for enhanced error reporting with security filtering
- Centralized constants module for magic values and configuration
- Request ID field for individual request tracking in error responses
- Debug information in error responses for development environments

### Changed
- Replaced interrogate with pydoclint for enhanced docstring quality validation
- Improved documentation quality across all modules with comprehensive docstrings
- Improved changelog commit messages to be more descriptive and follow project standards
- Enhanced Ruff linting configuration with stricter rules for code quality
- Refactored codebase to eliminate magic values and improve code quality

## [0.1.0] - 2025-06-16

### Added
- Initial release
- Basic FastAPI application with /info endpoint
- Core utilities for configuration, exceptions, and logging
- Development environment setup

[Unreleased]: https://github.com/daniel-jorge/tributum-back/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/daniel-jorge/tributum-back/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/daniel-jorge/tributum-back/releases/tag/v0.1.0
