import pytest

from {{ package_name }}.utilizing.colors import Color


def test_color_from_named_string() -> None:
    color = Color.from_string("Blue")
    assert color == "blue"
    assert color.to_matplotlib() == "blue"
    assert color.to_plotly() == "blue"


def test_color_from_hex_string_expands_short_form() -> None:
    color = Color.from_string("#0f8")
    assert color == "#00ff88"


def test_color_from_rgb_tuple_ints() -> None:
    color = Color.from_rgb((255, 128, 0))
    assert color == "#ff8000"


def test_color_from_rgb_tuple_floats() -> None:
    color = Color.from_rgb((1.0, 0.5, 0.0))
    assert color == "#ff8000"


def test_color_from_value_sequence() -> None:
    color = Color.from_value([0, 64, 255])
    assert color == "#0040ff"


def test_color_from_rgba_sequence() -> None:
    color = Color.from_rgb((255, 128, 0, 0.5))
    assert color == "#ff800080"


def test_color_from_rgb_text_forms() -> None:
    assert Color.from_string("rgb(255, 0, 128)") == "#ff0080"
    assert Color.from_string("(1.0, 0.5, 0.0)") == "#ff8000"


def test_color_convert_to_color_uses_default_when_requested() -> None:
    assert Color.convert_to_color("", throw=False) == Color.BLUE


def test_color_invalid_inputs_raise() -> None:
    with pytest.raises(ValueError):
        Color.from_string("")
    with pytest.raises(ValueError):
        Color.from_rgb((255, 0))
    with pytest.raises(ValueError):
        Color.from_rgb((256, 0, 0))
    with pytest.raises(ValueError):
        Color.from_string("rgb(255,,0)")


def test_named_color_constants_are_available() -> None:
    assert isinstance(Color.BLUE, Color)
    assert Color.BLUE == "blue"
