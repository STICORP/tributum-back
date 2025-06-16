"""Custom response classes for high-performance JSON serialization.

This module provides FastAPI response classes that use orjson for
improved JSON serialization performance.
"""

from typing import Any

import orjson
from fastapi.responses import JSONResponse
from pydantic import BaseModel


class ORJSONResponse(JSONResponse):
    """FastAPI Response class using orjson for high-performance JSON serialization.

    This response class provides 2-10x faster JSON serialization compared to
    the standard JSONResponse, with proper handling of datetime objects,
    UUIDs, and Pydantic models.
    """

    media_type = "application/json"

    def render(self, content: Any) -> bytes:
        """Render the content as JSON using orjson.

        Args:
            content: The content to serialize to JSON.

        Returns:
            The JSON-encoded bytes.
        """
        # Handle Pydantic models by calling model_dump()
        if isinstance(content, BaseModel):
            content = content.model_dump()

        # Use consistent sorting for predictable output
        return orjson.dumps(content, option=orjson.OPT_SORT_KEYS)
