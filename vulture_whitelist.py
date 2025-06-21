"""Vulture whitelist for false positives.

Add imports/names that vulture incorrectly identifies as unused.
"""


# Dummy class to reference names that vulture thinks are unused
class _VultureWhitelist:
    """Container for whitelisted names."""

    # FastAPI decorators and dependencies
    def get(self) -> None:
        """FastAPI GET route decorator."""

    def post(self) -> None:
        """FastAPI POST route decorator."""

    def put(self) -> None:
        """FastAPI PUT route decorator."""

    def delete(self) -> None:
        """FastAPI DELETE route decorator."""

    def patch(self) -> None:
        """FastAPI PATCH route decorator."""

    # Pytest fixtures (if not caught by ignore patterns)
    def conftest(self) -> None:
        """Pytest conftest module."""

    # SQLAlchemy model attributes (when added)
    def id(self) -> None:
        """SQLAlchemy id column."""

    def created_at(self) -> None:
        """SQLAlchemy created_at timestamp."""

    def updated_at(self) -> None:
        """SQLAlchemy updated_at timestamp."""

    # Pydantic field validator cls parameter
    def cls(self) -> None:
        """Pydantic field validator class parameter."""

    # Pydantic validators
    def empty_str_to_none(self) -> None:
        """Pydantic field validator method."""

    # Pytest fixtures that appear unused but are used via dependency injection
    def ensure_container_stopped(self) -> None:
        """Pytest fixture for Docker container cleanup."""

    def ensure_container_running(self) -> None:
        """Pytest fixture parameter for Docker container setup."""
