# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

### Changed
- Improved changelog commit messages to be more descriptive and follow project standards

### Deprecated

### Removed

### Fixed

### Security

## [0.1.0] - 2025-06-16

### Added
- Initial release
- Basic FastAPI application with /info endpoint
- Core utilities for configuration, exceptions, and logging
- Development environment setup

[Unreleased]: https://github.com/daniel-jorge/tributum-back/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/daniel-jorge/tributum-back/releases/tag/v0.1.0
