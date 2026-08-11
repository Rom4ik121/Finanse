"""Currency alias normalization."""

from __future__ import annotations

from lib.domain.entities.currency_codes import normalize_currency_code


def test_normalize_iso_passthrough() -> None:
    assert normalize_currency_code("usd") == "USD"
    assert normalize_currency_code(" RUB ") == "RUB"


def test_normalize_aliases() -> None:
    assert normalize_currency_code("SOM") == "UZS"
    assert normalize_currency_code("СУМ") == "UZS"
    assert normalize_currency_code("₽") == "RUB"
    assert normalize_currency_code("$") == "USD"
    assert normalize_currency_code("€") == "EUR"
    assert normalize_currency_code("₸") == "KZT"


def test_normalize_empty_uses_default() -> None:
    assert normalize_currency_code(None) == "RUB"
    assert normalize_currency_code("") == "RUB"
    assert normalize_currency_code("  ", default="UZS") == "UZS"
