"""Tributum - High-Performance Financial Intelligence Platform.

Tributum is a modern tax system built with Python 3.13+ and FastAPI, designed for
scalability, reliability, and maintainability.

Architecture Overview:
- **API Layer**: FastAPI with async request handling and middleware
- **Core Layer**: Shared utilities, configuration, and cross-cutting concerns
- **Domain Layer**: Business logic and entities (DDD-ready)
- **Infrastructure Layer**: Data persistence and external integrations

Key Features:
- **Performance**: Async-first design with connection pooling
- **Observability**: Structured logging and distributed tracing
- **Security**: Comprehensive error sanitization and security headers
- **Reliability**: Health checks, circuit breakers, and proper cleanup
- **Developer Experience**: Full type safety and 100% test coverage

The system follows clean architecture principles with clear separation
of concerns, making it easy to test, extend, and maintain.
"""
