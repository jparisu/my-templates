"""
Useful decorators for various purposes.
"""

from __future__ import annotations

import functools
import inspect
from collections.abc import Callable
from typing import Any, TypeVar, cast

F = TypeVar("F", bound=Callable[..., Any])


def keyword_only(func: F) -> F:
    """
    Enforce that instance methods are called with keyword-only args.
    Also updates the visible signature to show keyword-only params.
    """
    sig = inspect.signature(func)
    params = list(sig.parameters.values())
    if not params:
        raise TypeError(f"{func.__name__} must be a method with 'self' first")

    # Create a public-facing signature where every param after self is KEYWORD_ONLY
    new_params = [params[0]] + [p.replace(kind=inspect.Parameter.KEYWORD_ONLY) for p in params[1:]]
    public_sig = sig.replace(parameters=new_params)

    @functools.wraps(func)
    def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
        if args:
            raise TypeError(f"{func.__name__}() accepts only keyword arguments")
        # Validate kwargs (presence, types, defaults) against the public signature
        public_sig.bind(self, **kwargs)
        return func(self, **kwargs)

    # Make tools/IDEs show the keyword-only signature
    wrapper.__signature__ = public_sig  # type: ignore[attr-defined]

    return cast(F, wrapper)
