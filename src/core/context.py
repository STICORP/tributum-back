"""Request context management utilities for correlation IDs and request tracking."""

import uuid
from typing import Final

# Standard header name for correlation ID across services
CORRELATION_ID_HEADER: Final[str] = "X-Correlation-ID"


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
