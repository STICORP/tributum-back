"""Request context management utilities for correlation IDs and request tracking."""

import uuid
from contextvars import ContextVar
from typing import Final

# Standard header name for correlation ID across services
CORRELATION_ID_HEADER: Final[str] = "X-Correlation-ID"

# Context variable for storing correlation ID across async boundaries
_correlation_id_var: ContextVar[str | None] = ContextVar("correlation_id", default=None)


class RequestContext:
    """Manages request context using contextvars for async-safe storage.

    This class provides thread-safe and async-safe storage for request-scoped
    data, particularly correlation IDs that need to be accessible throughout
    the request lifecycle.
    """

    @staticmethod
    def set_correlation_id(correlation_id: str) -> None:
        """Set the correlation ID for the current context.

        Args:
            correlation_id: The correlation ID to store in the context.
        """
        _correlation_id_var.set(correlation_id)

    @staticmethod
    def get_correlation_id() -> str | None:
        """Get the correlation ID from the current context.

        Returns:
            The correlation ID if set, None otherwise.
        """
        return _correlation_id_var.get()

    @staticmethod
    def clear() -> None:
        """Clear all context variables.

        This should typically be called at the end of a request to ensure
        clean state for the next request.
        """
        _correlation_id_var.set(None)


def generate_correlation_id() -> str:
    """Generate a unique correlation ID for request tracking.

    Returns a UUID4 string that can be used to correlate logs and events
    across different services and components.

    Returns:
        A string representation of a UUID4.

    Examples:
        >>> correlation_id = generate_correlation_id()
        >>> len(correlation_id)
        36
        >>> # Format: xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx
    """
    return str(uuid.uuid4())
