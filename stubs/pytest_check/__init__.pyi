"""Type stubs for pytest_check."""

from collections.abc import Callable
from contextlib import AbstractContextManager
from typing import TypeVar

__all__ = ["any_failures", "check", "check_func", "raises"]

_T = TypeVar("_T")

class CheckContextManager(AbstractContextManager[None]):
    """Context manager for soft assertions."""

    def __enter__(self) -> None: ...
    def __exit__(self, *args: object) -> None: ...

check: CheckContextManager

def check_func[T](func: Callable[..., T]) -> Callable[..., T]: ...
def any_failures() -> bool: ...
def raises(
    expected_exception: type[BaseException], *args: object, **kwargs: object
) -> object: ...
