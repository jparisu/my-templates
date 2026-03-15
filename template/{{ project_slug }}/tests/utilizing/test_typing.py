from {{ package_name }}.utilizing.types import is_hashable


class A_Unhashable:
    def __init__(self, x=42):
        self.x = x

    # Note: setting __eq__ without __hash__ makes this class unhashable
    def __eq__(self, other):
        return isinstance(other, A_Unhashable) and self.x == other.x


class A_Hashable:
    def __init__(self, x=42):
        self.x = x

    def __eq__(self, other):
        return self.x == other.x

    def __hash__(self):
        return hash(self.x)


class A_BrokenHash:
    def __hash__(self):
        raise TypeError("broken hash")


def test_is_hashable_with_hashable_objects():
    assert is_hashable(42)  # int
    assert is_hashable(3.14)  # float
    assert is_hashable("hello")  # str
    assert is_hashable((1, 2, 3))  # tuple
    assert is_hashable(frozenset([1, 2, 3]))  # frozenset
    assert is_hashable(A_Hashable(10))  # custom hashable object
    assert is_hashable(((0, 1), "obj", frozenset([1, 2])))  # tuple of hashable objects


def test_is_hashable_with_unhashable_objects():
    assert not is_hashable([1, 2, 3])  # list
    assert not is_hashable({1: "a", 2: "b"})  # dict
    assert not is_hashable({1, 2, 3})  # set
    assert not is_hashable(bytearray(b"hello"))  # bytearray
    assert not is_hashable(((0, 1), [0, 1]))  # tuple with unhashable element
    assert not is_hashable(A_Unhashable(10))  # custom unhashable object
    assert not is_hashable(A_BrokenHash())  # object advertising hash but failing at runtime
