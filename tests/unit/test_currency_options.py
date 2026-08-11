"""Currency catalog helpers."""

from __future__ import annotations

from lib.presentation.currency_options import (
    _currency_display_name,
    load_currency_catalog,
)


def test_load_currency_catalog_has_rub() -> None:
    rows = load_currency_catalog(include_crypto=False)
    codes = {r["code"] for r in rows}
    assert "RUB" in codes
    assert "BTC" not in codes


def test_load_currency_catalog_include_crypto() -> None:
    rows = load_currency_catalog(include_crypto=True)
    codes = {r["code"] for r in rows}
    assert "BTC" in codes or "ETH" in codes


def test_display_name_by_lang() -> None:
    row = {
        "code": "USD",
        "name_ru": "Доллар США",
        "name_en": "US Dollar",
        "name_uz": "AQSH dollari",
    }
    assert _currency_display_name(row, "ru") == "Доллар США"
    assert _currency_display_name(row, "en") == "US Dollar"
    assert _currency_display_name(row, "uz") == "AQSH dollari"
