import pytest

from {{ package_name }}.utilizing.exceptions import ThisShouldNotHappen
from {{ package_name }}.utilizing.names import Naming_convention, naming_convention


def test_naming_convention_normalizes_text() -> None:
    assert naming_convention("Hello, World!") == "helloworld"
    assert Naming_convention("A-B C") == "abc"


def test_this_should_not_happen_is_exception() -> None:
    with pytest.raises(ThisShouldNotHappen):
        raise ThisShouldNotHappen("unexpected state")
