"""HTTP API layer with FastAPI for the Tributum platform.

This package implements the API layer of the application, providing RESTful
endpoints, request/response handling, and HTTP-specific functionality built
on top of the FastAPI framework.

Key components:
- **main**: Application factory and lifecycle management
- **middleware**: Cross-cutting concerns for all requests
  - Security headers for protection against common attacks
  - Request context with correlation ID tracking
  - Structured logging with performance metrics
  - Centralized error handling with consistent responses
- **schemas**: Pydantic models for validation and serialization
  - Standardized error response format
  - Request/response DTOs with detailed validation
- **utils**: API-specific utilities and helpers
  - High-performance JSON serialization with orjson

Design principles:
- **Async-first**: All endpoints and middleware use async/await
- **Type safety**: Full typing with Pydantic models
- **Observability**: Comprehensive logging and tracing
- **Security**: Defense-in-depth with multiple security layers
- **Performance**: Optimized serialization and connection handling

The API layer serves as the application's HTTP boundary, translating
between HTTP concepts and domain logic while maintaining proper
separation of concerns.
"""
