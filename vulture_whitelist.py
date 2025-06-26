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

    # Async context manager __aexit__ parameters
    def exc_val(self) -> None:
        """Exception value parameter in __aexit__ methods."""

    def exc_tb(self) -> None:
        """Exception traceback parameter in __aexit__ methods."""

    # SQLAlchemy event listener parameters
    def cursor(self) -> None:
        """Database cursor parameter in SQLAlchemy event listeners."""

    def conn(self) -> None:
        """Database connection parameter in SQLAlchemy event listeners."""

    def statement(self) -> None:
        """SQL statement parameter in SQLAlchemy event listeners."""

    def parameters(self) -> None:
        """Query parameters in SQLAlchemy event listeners."""

    def executemany(self) -> None:
        """Executemany flag in SQLAlchemy event listeners."""

    # SQLAlchemy event listener functions
    def _before_cursor_execute(self) -> None:
        """SQLAlchemy before_cursor_execute event handler."""

    def _after_cursor_execute(self) -> None:
        """SQLAlchemy after_cursor_execute event handler."""
