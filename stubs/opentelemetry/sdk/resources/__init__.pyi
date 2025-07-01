"""Type stubs for opentelemetry.sdk.resources."""

from collections.abc import Mapping
from typing import Any

class Resource:
    """Type stub for Resource."""

    @staticmethod
    def create(attributes: Mapping[str, Any] | None = None) -> Resource: ...
    @property
    def attributes(self) -> Mapping[str, Any]: ...
    def merge(self, other: Resource) -> Resource: ...
