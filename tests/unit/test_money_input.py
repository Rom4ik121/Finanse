"""Grouped amount input parsing and formatting."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

import pytest

from lib.presentation.money_input import (
    amount_separators,
    format_amount_input,
    format_amount_value,
    parse_amount,
)


def test_separators_by_language() -> None:
    assert amount_separators("en") == (",", ".")
    assert amount_separators("ru") == (".", ",")
    assert amount_separators("uz") == (".", ",")


def test_format_groups_while_typing_ru() -> None:
    assert format_amount_input("1", "ru") == "1"
    assert format_amount_input("12", "ru") == "12"
    assert format_amount_input("123", "ru") == "123"
    assert format_amount_input("1234", "ru") == "1.234"
    assert format_amount_input("1234567", "ru") == "1.234.567"
    assert format_amount_input("1000000", "ru") == "1.000.000"
    assert format_amount_input("1,000000", "ru") == "1.000.000"
    assert format_amount_input("1.000000", "ru") == "1.000.000"
    assert format_amount_input("1000000", "en") == "1,000,000"
    assert format_amount_input("1,000000", "en") == "1,000,000"
    assert format_amount_input("1234,", "ru") == "1.234,"
    assert format_amount_input("1234,5", "ru") == "1.234,5"
    assert format_amount_input("1234,50", "ru") == "1.234,50"


def test_format_groups_while_typing_en() -> None:
    assert format_amount_input("1234", "en") == "1,234"
    assert format_amount_input("1234.", "en") == "1,234."
    assert format_amount_input("1234.5", "en") == "1,234.5"
    assert format_amount_input("25000.00", "en") == "25,000.00"


def test_parse_grouped_amounts() -> None:
    assert parse_amount("1.234,50") == Decimal("1234.50")
    assert parse_amount("1,234.50") == Decimal("1234.50")
    assert parse_amount("25.000") == Decimal("25000")
    assert parse_amount("25,000") == Decimal("25000")
    assert parse_amount("1 234,5") == Decimal("1234.5")
    with pytest.raises(InvalidOperation):
        parse_amount("")
    with pytest.raises(InvalidOperation):
        parse_amount("   ")


def test_format_amount_value_from_decimal() -> None:
    assert format_amount_value(Decimal("25000"), "ru") == "25.000"
    assert format_amount_value(Decimal("25000.5"), "ru") == "25.000,50"
    assert format_amount_value(Decimal("25000"), "en") == "25,000"
    assert format_amount_value("", "ru") == ""
