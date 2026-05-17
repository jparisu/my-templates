"""Exception helpers shared across the project."""


class ThisShouldNotHappen(Exception):
    """Raised for defensive branches that should be unreachable."""
