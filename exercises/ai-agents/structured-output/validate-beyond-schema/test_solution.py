import datetime

from solution import validate_invoice

TODAY = datetime.date(2026, 9, 25)


def _invoice(**overrides):
    invoice = {
        "number": "NF-1",
        "issued_on": "2026-09-20",
        "total": 100.0,
        "currency": "BRL",
        "items": [{"quantity": 2, "unit_price": 50.0}],
    }
    invoice.update(overrides)
    return invoice


def test_valid_invoice_has_no_problems():
    assert validate_invoice(_invoice(), TODAY) == []


def test_future_date():
    assert validate_invoice(_invoice(issued_on="2026-09-26"), TODAY) == ["data no futuro"]


def test_issued_today_is_valid():
    assert validate_invoice(_invoice(issued_on="2026-09-25"), TODAY) == []


def test_empty_items():
    problems = validate_invoice(_invoice(items=[], total=0.0), TODAY)
    assert problems == ["nota sem itens"]


def test_total_mismatch():
    assert validate_invoice(_invoice(total=999.0), TODAY) == ["total não bate com os itens"]


def test_rounding_tolerance():
    invoice = _invoice(total=100.005, items=[{"quantity": 3, "unit_price": 33.335}])
    assert validate_invoice(invoice, TODAY) == []


def test_invalid_quantity_reports_index():
    invoice = _invoice(
        total=50.0,
        items=[{"quantity": 1, "unit_price": 50.0}, {"quantity": 0, "unit_price": 10.0}],
    )
    assert "quantidade inválida no item 1" in validate_invoice(invoice, TODAY)


def test_problems_are_collected_in_order():
    invoice = _invoice(
        issued_on="2026-12-01", total=1.0, items=[{"quantity": -1, "unit_price": 5.0}]
    )
    assert validate_invoice(invoice, TODAY) == [
        "data no futuro",
        "total não bate com os itens",
        "quantidade inválida no item 0",
    ]
