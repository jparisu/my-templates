"""Color value object with backend serializer helpers."""

from __future__ import annotations

import re
from collections.abc import Sequence
from numbers import Real
from typing import Any


class Color(str):
    """Color token supporting names, hex values, and RGB tuples.

    The class is intentionally ``str``-compatible so it can be passed to plotting
    backends directly while still exposing ``to_matplotlib`` / ``to_plotly`` helpers.
    """

    _HEX_RE = re.compile(r"^#([0-9a-fA-F]{3}|[0-9a-fA-F]{4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")

    def __new__(cls, value: str) -> Color:
        if not isinstance(value, str):
            raise TypeError(f"Color expects a string value, got {type(value).__name__}.")
        normalized = cls._normalize_string(value)
        return super().__new__(cls, normalized)

    @classmethod
    def from_value(cls, value: Any) -> Color:
        """Build a color from string-like or RGB sequence values."""
        if isinstance(value, cls):
            return value
        if isinstance(value, str):
            return cls.from_string(value)
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
            return cls.from_rgb(value)
        raise TypeError(
            "Color.from_value expects a color string (name/hex) or an RGB(A) "
            f"sequence; got {type(value).__name__}."
        )

    @classmethod
    def from_string(cls, value: str) -> Color:
        """Build a color from backend-native names, hex, or RGB(A) text."""
        text = str(value).strip()
        if not text:
            raise ValueError("Color string cannot be empty.")

        lowered = text.lower()
        if lowered.startswith("rgb(") and lowered.endswith(")"):
            body = lowered[4:-1]
            return cls.from_rgb(cls._parse_numeric_sequence(body))
        if lowered.startswith("rgba(") and lowered.endswith(")"):
            body = lowered[5:-1]
            return cls.from_rgb(cls._parse_numeric_sequence(body))
        if text.startswith("(") and text.endswith(")") and "," in text:
            body = text[1:-1]
            return cls.from_rgb(cls._parse_numeric_sequence(body))

        return cls(text)

    @classmethod
    def from_rgb(cls, values: Sequence[Any]) -> Color:
        """Build a color from RGB or RGBA components.

        Accepted ranges:
        - integers in ``[0, 255]``
        - floats in ``[0, 1]`` (normalized) or ``[0, 255]``.
        """
        components = list(values)
        if len(components) not in (3, 4):
            raise ValueError(f"RGB(A) sequence must have length 3 or 4, got {len(components)}.")

        rgb = [cls._component_to_byte(v) for v in components[:3]]
        hex_color = "#" + "".join(f"{channel:02x}" for channel in rgb)
        if len(components) == 4:
            alpha = cls._component_to_byte(components[3], alpha=True)
            hex_color += f"{alpha:02x}"
        return cls(hex_color)

    def to_plotly(self) -> str:
        """Return Plotly-compatible color token."""
        return str(self)

    def to_matplotlib(self) -> str:
        """Return Matplotlib-compatible color token."""
        return str(self)

    @classmethod
    def convert_to_color(cls, target: str, throw: bool = True) -> Color:
        """Backward-compatible color resolver with default fallback support."""
        try:
            return cls.from_string(target)
        except Exception:
            if throw:
                raise
            return cls.default()

    @classmethod
    def default(cls) -> Color:
        """Return default plotting color."""
        return cls("blue")

    @classmethod
    def _normalize_string(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("Color string cannot be empty.")

        if cls._HEX_RE.match(text):
            hex_text = text.lower()
            # Expand shorthand (#rgb / #rgba) to canonical long notation.
            if len(hex_text) in (4, 5):
                expanded = "".join(ch * 2 for ch in hex_text[1:])
                return "#" + expanded
            return hex_text

        return text.lower()

    @staticmethod
    def _parse_numeric_sequence(body: str) -> list[float]:
        parts = [p.strip() for p in body.split(",")]
        if any(part == "" for part in parts):
            raise ValueError(f"Invalid RGB(A) text sequence: {body!r}")
        try:
            return [float(part) for part in parts]
        except ValueError as exc:  # pragma: no cover - defensive conversion path
            raise ValueError(f"Invalid numeric value in RGB(A) text sequence: {body!r}") from exc

    @staticmethod
    def _component_to_byte(value: Any, *, alpha: bool = False) -> int:
        if isinstance(value, bool):
            numeric_int = int(value)
        elif isinstance(value, int):
            numeric_int = value
            if not 0 <= numeric_int <= 255:
                raise ValueError(f"RGB(A) integer components must be in [0, 255], got {value!r}.")
            return numeric_int
        elif isinstance(value, Real):
            numeric_float = float(value)
            if 0.0 <= numeric_float <= 1.0:
                return int(round(numeric_float * 255.0))
            if 0.0 <= numeric_float <= 255.0:
                return int(round(numeric_float))
            raise ValueError(
                f"RGB(A) float components must be in [0, 1] or [0, 255], got {value!r}."
            )
        else:
            raise TypeError(f"RGB(A) components must be numeric, got {type(value).__name__}.")

        if not alpha and not 0 <= numeric_int <= 255:
            raise ValueError(f"RGB components must be in [0, 255], got {value!r}.")
        if alpha and not 0 <= numeric_int <= 255:
            raise ValueError(f"Alpha component must be in [0, 255], got {value!r}.")
        return numeric_int


_NAMED_COLOR_TOKENS = (
    "blue",
    "red",
    "green",
    "orange",
    "purple",
    "cyan",
    "magenta",
    "yellow",
    "black",
    "gray",
    "pink",
    "brown",
    "navy",
    "dodgerblue",
    "deepskyblue",
    "turquoise",
    "lightgreen",
    "maroon",
    "gold",
    "tan",
    "olive",
    "chocolate",
    "lime",
    "darkgreen",
)

for _token in _NAMED_COLOR_TOKENS:
    setattr(Color, _token.upper(), Color(_token))
