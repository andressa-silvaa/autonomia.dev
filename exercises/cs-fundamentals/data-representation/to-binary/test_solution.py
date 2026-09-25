from pathlib import Path

import pytest
import solution
from solution import to_binary

FORBIDDEN = ("bin(", "format(", ":b}")


@pytest.mark.parametrize(
    ("number", "expected"),
    [
        (0, "0"),
        (1, "1"),
        (2, "10"),
        (5, "101"),
        (10, "1010"),
        (255, "11111111"),
        (1024, "10000000000"),
    ],
)
def test_converts_to_binary(number, expected):
    assert to_binary(number) == expected


def test_negative_numbers_are_rejected():
    with pytest.raises(ValueError):
        to_binary(-3)


def test_does_not_use_shortcuts():
    source = Path(solution.__file__).read_text(encoding="utf-8")
    used = [shortcut for shortcut in FORBIDDEN if shortcut in source]
    assert not used, f"Sem atalhos: a solução usa {used}"
