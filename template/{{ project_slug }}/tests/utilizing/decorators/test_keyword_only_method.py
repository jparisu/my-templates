import inspect

import pytest

from {{ package_name }}.utilizing.decorating.keyword_only import keyword_only


class A:
    def __init__(self, base=0):
        self.base = base
        self.calls = {"add": 0, "with_defaults": 0}

    @keyword_only
    def add(self, x: float, y: int) -> float:
        """adds with base"""
        self.calls["add"] += 1
        return self.base + x + y

    @keyword_only
    def with_defaults(self, x: int = 1, y: int = 2) -> int:
        """has defaults"""
        self.calls["with_defaults"] += 1
        return self.base + x + y


def test_rejects_positional_arguments():
    a = A(base=10)
    with pytest.raises(TypeError) as exc:
        a.add(2.0, 3)
    assert "only keyword arguments" in str(exc.value)
    # No computation should happen
    assert a.calls["add"] == 0


def test_accepts_kwargs_and_computes():
    a = A(base=5)
    out = a.add(x=2.0, y=3)
    assert out == 10.0
    assert a.calls["add"] == 1


def test_kwargs_order_irrelevant():
    a = A(base=1)
    r1 = a.add(x=2.0, y=3)
    r2 = a.add(y=3, x=2.0)
    assert r1 == r2 == 6.0
    # Both are valid calls; decorator doesn’t cache, so both compute.
    assert a.calls["add"] == 2


def test_missing_required_argument_raises():
    a = A()
    with pytest.raises(TypeError):
        a.add(x=2.0)  # missing y
    with pytest.raises(TypeError):
        a.add(y=3)  # missing x
    assert a.calls["add"] == 0


def test_defaults_allow_omitting_kwargs():
    a = A(base=0)
    # No kwargs → should use defaults (x=1, y=2)
    out = a.with_defaults()
    assert out == 3
    assert a.calls["with_defaults"] == 1

    # Override one default
    out2 = a.with_defaults(y=10)
    assert out2 == 11
    assert a.calls["with_defaults"] == 2


def test_rejects_unexpected_kwarg():
    a = A()
    with pytest.raises(TypeError):
        a.add(x=1, y=2, z=3)
    assert a.calls["add"] == 0


def test_signature_exposes_keyword_only_after_self():
    sig = inspect.signature(A.add)
    params = list(sig.parameters.values())
    # First param is the method 'self'
    assert params[0].name == "self"
    # All remaining must be KEYWORD_ONLY
    assert all(p.kind is inspect.Parameter.KEYWORD_ONLY for p in params[1:])
    # Names preserved
    assert [p.name for p in params] == ["self", "x", "y"]


def test_wraps_preserves_metadata():
    # Name and docstring are preserved by functools.wraps
    assert A.add.__name__ == "add"
    assert "adds with base" in (A.add.__doc__ or "")
