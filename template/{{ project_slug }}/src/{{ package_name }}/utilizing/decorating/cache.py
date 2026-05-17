"""
Useful decorators for various purposes.
"""

from __future__ import annotations

import functools
from collections.abc import Callable, Mapping, Set
from typing import Any, TypeVar, cast

from ..types import is_hashable

F = TypeVar("F", bound=Callable[..., Any])


def cache_method(func: F) -> F:
    """
    Per-instance memoization for instance methods.

    For those calls with and without keywords, the cache key differs.

    Implementation Note:
        Hashable arguments are used directly. Common container types are
        normalized recursively so equal unhashable inputs still share cache
        entries. For opaque unhashable objects we fall back to their repr().
    """
    cache_attr = f"__cache_{func.__name__}"

    @functools.wraps(func)
    def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
        # get/create this method's cache for THIS instance
        cache = cast(dict[Any, Any], self.__dict__.setdefault(cache_attr, {}))

        key: Any = None
        # build a key: (args, sorted kwargs) — common, fast path
        if kwargs:
            key = (args, tuple(sorted(kwargs.items())))
        else:
            key = (args, None)

        # Check if hashable
        if not is_hashable(key):
            key = _freeze_for_cache((args, kwargs))

        # Lookup in cache
        if key in cache:
            return cache[key]

        # Not found: compute and store
        result = func(self, *args, **kwargs)
        cache[key] = result
        return result

    # expose a way to clear just this method's cache on an instance
    def cache_clear(inst: Any) -> None:
        inst.__dict__.get(cache_attr, {}).clear()

    # Set the cache_clear method on the wrapper
    wrapper.cache_clear = cache_clear  # type: ignore[attr-defined]

    return cast(F, wrapper)


def _freeze_for_cache(value: Any) -> Any:
    """Convert common mutable inputs to hashable cache-key fragments."""
    if is_hashable(value):
        return value
    if isinstance(value, Mapping):
        return tuple(
            sorted(
                ((_freeze_for_cache(k), _freeze_for_cache(v)) for k, v in value.items()),
                key=repr,
            )
        )
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_for_cache(item) for item in value)
    if isinstance(value, Set) and not isinstance(value, (str, bytes, bytearray, frozenset)):
        return tuple(sorted((_freeze_for_cache(item) for item in value), key=repr))
    if hasattr(value, "__dict__"):
        return (type(value), _freeze_for_cache(vars(value)))
    return repr(value)
