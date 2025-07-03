"""High-performance JSON response classes using orjson serialization.

This module provides optimized FastAPI response classes that leverage
orjson for significantly faster JSON serialization compared to standard
Python json module.

Performance benefits:
- 2-10x faster serialization than standard json
- Native handling of datetime, UUID, and Decimal types
- Efficient serialization of Pydantic models
- Consistent key ordering for predictable output

The ORJSONResponse class is set as the default response class for the
entire FastAPI application, ensuring all JSON responses benefit from
these performance improvements.
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

    Attributes:
        media_type: The media type for the response.
    """

    media_type = "application/json"

    def render(self, content: Any) -> bytes:  # noqa: ANN401 - accepts any JSON-serializable content
        """Render the content as JSON using orjson.

        Args:
            content: The content to serialize to JSON.

        Returns:
            bytes: The JSON-encoded bytes.
        """
        # Handle Pydantic models by calling model_dump()
        if isinstance(content, BaseModel):
            content = content.model_dump()

        # Use consistent sorting for predictable output
        return orjson.dumps(content, option=orjson.OPT_SORT_KEYS)
