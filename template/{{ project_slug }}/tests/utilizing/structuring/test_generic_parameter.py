from dataclasses import dataclass

from {{ package_name }}.utilizing.colors import Color
from {{ package_name }}.utilizing.structuring.GenericEnumRegistry import GenericEnumRegistry
from {{ package_name }}.utilizing.structuring.GenericParameter import GenericParameter


class Backend(GenericEnumRegistry):
    MPL = ("matplotlib", "mpl")
    PLOTLY = ("plotly", "ply")

    def to_plotly(self) -> str:
        return "plotly" if self is Backend.PLOTLY else "matplotlib"


class Palette(GenericEnumRegistry):
    RED = "red"
    GREEN = "green"


@dataclass
class PlotParams(GenericParameter):
    backend: Backend = Backend.MPL
    title: str = "default"
    alpha: float | None = None

    @classmethod
    def aliases(cls) -> dict[str, str]:
        return {"lbl": "title"}


def test_from_dict_resolves_alias_and_enum() -> None:
    params = PlotParams.from_dict({"backend": "plotly", "lbl": "Title"})
    assert params.backend is Backend.PLOTLY
    assert params.title == "Title"


def test_from_dict_normalizes_alias_keys() -> None:
    params = PlotParams.from_dict({"L-B-L": "Title"})
    assert params.title == "Title"


def test_update_from_dict_converts_optional_values() -> None:
    params = PlotParams()
    params.update_from_dict({"alpha": None})
    assert params.alpha is None


def test_to_dict_with_target_format_uses_enum_serializer() -> None:
    params = PlotParams(backend=Backend.PLOTLY)
    out = params.to_dict(target_format="plotly")
    assert out["backend"] == "plotly"


def test_set_default_value_only_when_none() -> None:
    params = PlotParams(alpha=None)
    params.set_default_value("alpha", 0.5)
    params.set_default_value("title", "ignored")

    assert params.alpha == 0.5
    assert params.title == "default"


def test_update_from_dict_warns_for_unknown_keys(caplog) -> None:
    params = PlotParams()
    params.update_from_dict({"unknown": 1})

    assert "not recognized" in caplog.text


@dataclass
class EnumParams(GenericParameter):
    color: Palette | None = None


def test_from_dict_converts_pep604_optional_enum_field() -> None:
    params = EnumParams.from_dict({"color": "green"})
    assert params.color is Palette.GREEN
    assert isinstance(params.color, Palette)


def test_copy_preserves_enum_member_type() -> None:
    params = EnumParams(color=Palette.GREEN)
    copied = params.copy()
    assert copied.color is Palette.GREEN
    assert isinstance(copied.color, Palette)


@dataclass
class RequiredParams(GenericParameter):
    name: str
    backend: Backend = Backend.MPL


def test_from_dict_supports_required_dataclass_fields() -> None:
    params = RequiredParams.from_dict({"name": "plot"})
    assert params.name == "plot"
    assert params.backend is Backend.MPL


def test_from_dict_raises_for_missing_required_fields() -> None:
    try:
        RequiredParams.from_dict({})
    except TypeError as exc:
        assert "Missing required field 'name'" in str(exc)
    else:  # pragma: no cover - defensive branch
        raise AssertionError("Expected TypeError for missing required field.")


class Token:
    def __init__(self, value: str) -> None:
        self.value = value

    @classmethod
    def from_string(cls, value: str) -> "Token":
        return cls(value.upper())


class ValueFirstToken:
    def __init__(self, value: str) -> None:
        self.value = value

    @classmethod
    def from_value(cls, value: object) -> "ValueFirstToken":
        return cls(f"value:{value}")

    @classmethod
    def from_string(cls, value: str) -> "ValueFirstToken":
        return cls(f"string:{value}")


class RenderableToken:
    def __init__(self, value: str) -> None:
        self.value = value

    def to_plotly(self) -> str:
        return f"plotly:{self.value}"


@dataclass
class CustomParams(GenericParameter):
    token: Token | None = None
    color: Color | None = None


@dataclass
class ConversionPriorityParams(GenericParameter):
    token: ValueFirstToken | None = None


@dataclass
class RenderParams(GenericParameter):
    token: RenderableToken | None = None


def test_from_dict_converts_fields_with_from_string() -> None:
    params = CustomParams.from_dict({"token": "abc"})
    assert params.token is not None
    assert params.token.value == "ABC"


def test_from_dict_converts_color_from_rgb_tuple() -> None:
    params = CustomParams.from_dict({"color": (255, 0, 128)})
    assert params.color == "#ff0080"
    assert isinstance(params.color, Color)


def test_from_dict_prefers_from_value_when_available() -> None:
    params = ConversionPriorityParams.from_dict({"token": "abc"})
    assert params.token is not None
    assert params.token.value == "value:abc"


def test_to_dict_uses_custom_serializer_methods() -> None:
    params = RenderParams(token=RenderableToken("abc"))
    assert params.to_dict(target_format="plotly")["token"] == "plotly:abc"
