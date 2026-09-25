import re

import pytest
from solution import invoice_schema

SCHEMA = invoice_schema()


def test_is_a_closed_object():
    assert SCHEMA["type"] == "object"
    assert SCHEMA["additionalProperties"] is False


def test_required_fields():
    assert set(SCHEMA["required"]) == {"number", "issued_on", "total", "currency"}


def test_field_types():
    properties = SCHEMA["properties"]
    assert set(properties) == {"number", "issued_on", "total", "currency", "notes"}
    assert properties["number"]["type"] == "string"
    assert properties["issued_on"]["type"] == "string"
    assert properties["total"]["type"] == "number"
    assert properties["currency"]["type"] == "string"
    assert properties["notes"]["type"] == "string"


def test_total_cannot_be_negative():
    assert SCHEMA["properties"]["total"]["minimum"] == 0


def test_currency_is_restricted():
    assert sorted(SCHEMA["properties"]["currency"]["enum"]) == ["BRL", "EUR", "USD"]


@pytest.mark.parametrize("value", ["2026-09-25", "1999-01-01"])
def test_date_pattern_accepts_valid_dates(value):
    assert re.fullmatch(SCHEMA["properties"]["issued_on"]["pattern"], value)


@pytest.mark.parametrize("value", ["25/09/2026", "2026-9-5", "ontem", "2026-09-25T10:00:00"])
def test_date_pattern_rejects_invalid_dates(value):
    assert not re.fullmatch(SCHEMA["properties"]["issued_on"]["pattern"], value)
