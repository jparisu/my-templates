"""Type-related utility helpers."""


def is_hashable(obj: object) -> bool:
    """Return whether ``hash(obj)`` succeeds without raising ``TypeError``."""
    try:
        hash(obj)
    except TypeError:
        return False
    return True
