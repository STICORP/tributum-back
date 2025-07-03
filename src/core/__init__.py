"""Core infrastructure package for shared application functionality.

This package provides the foundational components used across all layers
of the Tributum application:

- **config**: Centralized configuration management with environment support
- **context**: Request context and correlation ID management
- **exceptions**: Structured exception hierarchy with error codes
- **error_context**: Sensitive data sanitization for safe logging
- **logging**: Structured logging with cloud provider integrations
- **observability**: Distributed tracing with OpenTelemetry
- **types**: Type aliases for better code clarity

These modules implement cross-cutting concerns that ensure consistency,
security, and observability throughout the application.
"""
