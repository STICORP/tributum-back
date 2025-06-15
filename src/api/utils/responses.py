"""Custom response classes for high-performance JSON serialization.

This module provides FastAPI response classes that use orjson for
improved JSON serialization performance.
"""

from typing import Any

import orjson
from fastapi import Response
from pydantic import BaseModel


class ORJSONResponse(Response):
    """FastAPI Response class using orjson for high-performance JSON serialization.

    This response class provides 2-10x faster JSON serialization compared to
    the standard JSONResponse, with proper handling of datetime objects,
    UUIDs, and Pydantic models.
    """

    media_type = "application/json"

    def __init__(self, content: Any = None, **kwargs: Any) -> None:
        """Initialize the response.

        Args:
            content: The content to render.
            **kwargs: Additional arguments passed to Response.
        """
        self.debug = kwargs.pop("debug", False)
        super().__init__(content, **kwargs)

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

        # In debug mode, use indentation for readability
        options = orjson.OPT_SORT_KEYS
        if self.debug:
            options |= orjson.OPT_INDENT_2

        return orjson.dumps(content, option=options)
