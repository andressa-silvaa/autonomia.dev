import pytest
from solution import order_total


def _items(*pairs):
    return [{"quantity": q, "unit_price_cents": p} for q, p in pairs]


def test_no_discount_no_tax():
    assert order_total(_items((2, 1000), (1, 550)), 0, 0) == 2550


def test_discount_only():
    assert order_total(_items((1, 10000)), 10, 0) == 9000


def test_tax_only():
    assert order_total(_items((1, 10000)), 0, 10) == 11000


def test_discount_applied_before_tax():
    assert order_total(_items((1, 10000)), 50, 10) == 5500


def test_rounds_half_up_to_the_cent():
    assert order_total(_items((1, 1)), 50, 0) == 1


def test_empty_order():
    assert order_total([], 10, 10) == 0


def test_classic_float_trap():
    total = order_total(_items((3, 10)), 0, 0)
    assert total == 30
    assert isinstance(total, int)


@pytest.mark.parametrize(
    ("items", "discount", "tax"),
    [
        (_items((1, 100)), -1, 0),
        (_items((1, 100)), 101, 0),
        (_items((1, 100)), 0, -5),
        (_items((-1, 100)), 0, 0),
        (_items((1, -100)), 0, 0),
    ],
)
def test_invalid_input(items, discount, tax):
    with pytest.raises(ValueError):
        order_total(items, discount, tax)
