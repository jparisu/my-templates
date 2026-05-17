from __future__ import annotations

import logging
import threading
from typing import Generic, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class GenericSingleton(Generic[T]):
    """
    Wrap a class so only one instance is created per process.
    """

    def __init__(self, cls: type[T]) -> None:
        self._cls: type[T] = cls
        self._instance: T | None = None
        self._lock = threading.Lock()

        logger.debug(f"Singleton created for class {cls.__name__}")

    def __call__(self, *args: object, **kwargs: object) -> T:
        if self._instance is None:
            with self._lock:
                if self._instance is None:
                    self._instance = self._cls(*args, **kwargs)
        return self._instance

    def get_instance(self, *args: object, **kwargs: object) -> T:
        """Return the singleton instance, creating it on first access if needed."""
        return self.__call__(*args, **kwargs)
