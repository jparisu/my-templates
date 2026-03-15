"""Utility subpackage for reusable helpers and structural abstractions."""

from .colors import Color
from .exceptions import ThisShouldNotHappen
from .names import Naming_convention, naming_convention
from .types import is_hashable

__all__ = [
    "Color",
    "ThisShouldNotHappen",
    "Naming_convention",
    "is_hashable",
    "naming_convention",
]
