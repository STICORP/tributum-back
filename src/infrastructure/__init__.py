"""Infrastructure layer for external system integrations and data persistence.

This package implements the infrastructure layer of the application, providing
concrete implementations for data persistence, external service integrations,
and other technical concerns that the domain layer depends on.

Key responsibilities:
- **Database access**: Async PostgreSQL with SQLAlchemy 2.0+
- **Repository pattern**: Generic CRUD operations for all entities
- **Connection management**: Pooling, health checks, and lifecycle
- **External services**: Integration points for third-party APIs
- **Caching**: Performance optimization layers (future)
- **Message queuing**: Event-driven communication (future)

The infrastructure layer follows the Dependency Inversion Principle,
implementing interfaces defined by the domain layer to maintain proper
architectural boundaries.
"""
