from {{ package_name }}.utilizing.decorating.cache import cache_method


class Payload:
    def __init__(self, value: int) -> None:
        self.value = value

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Payload) and self.value == other.value


class A:
    def __init__(self, base=0):
        self.base = base
        self.calls = {"met1": 0, "met2": 0, "met3": 0, "met_list": 0, "met_payload": 0}

    @cache_method
    def met1(self) -> float:
        self.calls["met1"] += 1
        return self.base + 1.0

    @cache_method
    def met2(self, x: float) -> float:
        """Second method to test."""
        self.calls["met2"] += 1
        return self.base + x

    @cache_method
    def met3(self, x: float, y: int) -> float:
        self.calls["met3"] += 1
        return self.base + x + y

    # to test unhashable arguments (list)
    @cache_method
    def met_list(self, items: list) -> float:
        self.calls["met_list"] += 1
        return self.base + sum(items)

    @cache_method
    def met_payload(self, payload: Payload) -> float:
        self.calls["met_payload"] += 1
        return self.base + payload.value


def test_method_without_one_arg_is_cached_and_clearable():
    a = A(base=10)
    # first call computes
    r1 = a.met1()
    assert r1 == 11.0
    assert a.calls["met1"] == 1

    # second call should be cached (no extra calls)
    r2 = a.met1()
    assert r2 == 11.0
    assert a.calls["met1"] == 1  # still one compute

    # change internal state; cached value should still be returned
    a.base = 100
    r3 = a.met1()
    assert r3 == 11.0  # still cached old result
    assert a.calls["met1"] == 1

    # clear cache for this method on THIS instance
    A.met1.cache_clear(a)
    r4 = a.met1()
    assert r4 == 101.0  # recomputed with new base
    assert a.calls["met1"] == 2


def test_method_without_args_is_cached_and_clearable():
    a = A(base=10)
    # first call computes
    r1 = a.met2(1.0)
    assert r1 == 11.0
    assert a.calls["met2"] == 1

    # second call should be cached (no extra calls)
    r2 = a.met2(1.0)
    assert r2 == 11.0
    assert a.calls["met2"] == 1  # still one compute

    # change internal state; cached value should still be returned
    a.base = 100
    r3 = a.met2(1.0)
    assert r3 == 11.0  # still cached old result
    assert a.calls["met2"] == 1

    # clear cache for this method on THIS instance
    A.met2.cache_clear(a)
    r4 = a.met2(1.0)
    assert r4 == 101.0  # recomputed with new base
    assert a.calls["met2"] == 2


def test_caching_by_kwargs():
    a = A(base=5)

    # first compute
    r1 = a.met3(x=2.0, y=3)
    assert r1 == 5 + 2.0 + 3
    assert a.calls["met3"] == 1

    # kwargs in different order should still hit the same cache key
    r2 = a.met3(y=3, x=2.0)
    assert r2 == r1
    assert a.calls["met3"] == 1  # no extra compute

    # kwargs in different order should still hit the same cache key
    r3 = a.met3(x=2.0, y=3)
    assert r3 == r1
    assert a.calls["met3"] == 1  # no extra compute

    # different args => new compute and new cache entry
    r4 = a.met3(x=2.0, y=4)
    assert r4 == 5 + 2.0 + 4
    assert a.calls["met3"] == 2

    # different args => new compute and new cache entry
    r5 = a.met3(x=3.0, y=3)
    assert r5 == 5 + 3.0 + 3
    assert a.calls["met3"] == 3


def test_caching_by_args_and_kwargs_order():
    a = A(base=5)

    # first compute
    r1 = a.met3(2.0, 3)
    assert r1 == 5 + 2.0 + 3
    assert a.calls["met3"] == 1

    # kwargs instead of args do not hit the same cache key
    r2 = a.met3(x=2.0, y=3)
    assert r2 == r1
    assert a.calls["met3"] == 2  # no extra compute


def test_per_instance_isolation():
    a1 = A(base=1)
    a2 = A(base=100)

    # compute on a1
    r1 = a1.met2(9.0)
    assert r1 == 1 + 9.0
    assert a1.calls["met2"] == 1

    # calling same method+args on a2 should NOT use a1's cache
    r2 = a2.met2(9.0)
    assert r2 == 100 + 9.0
    assert a2.calls["met2"] == 1
    # a1 hasn't been called again
    assert a1.calls["met2"] == 1


def test_unhashable_arguments_are_cached_via_fallback_key():
    a = A(base=10)

    # first call with a list (unhashable) -> compute
    r1 = a.met_list([1, 2, 3])
    assert r1 == 10 + 6
    assert a.calls["met_list"] == 1

    # second call with an equal list should hit the fallback-key cache
    # (the decorator uses repr of args/kwargs; two equal lists produce same repr)
    r2 = a.met_list([1, 2, 3])
    assert r2 == r1
    assert a.calls["met_list"] == 1  # no recompute

    # different list -> different key -> recompute
    r3 = a.met_list([1, 2, 3, 4])
    assert r3 == 10 + 10
    assert a.calls["met_list"] == 2


def test_equal_unhashable_objects_share_cache_entries() -> None:
    a = A(base=10)

    r1 = a.met_payload(Payload(5))
    r2 = a.met_payload(Payload(5))

    assert r1 == r2 == 15
    assert a.calls["met_payload"] == 1


def test_clear_only_affects_one_method():
    a = A(base=7)

    # warm both caches
    a.met1()
    v2 = a.met2(3.0)
    assert a.calls["met1"] == 1
    assert a.calls["met2"] == 1

    # clear cache for met1 only
    A.met1.cache_clear(a)

    # met1 recomputes
    v1b = a.met1()
    assert v1b == 8.0
    assert a.calls["met1"] == 2

    # met2 remains cached
    v2b = a.met2(3.0)
    assert v2b == v2
    assert a.calls["met2"] == 1


def test_wraps_preserves_metadata():
    # Access the function object (undecorated view) via the class attribute
    assert A.met2.__name__ == "met2"
    assert "Second method to test." in A.met2.__doc__
