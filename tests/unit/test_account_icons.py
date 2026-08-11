"""Account icon key helpers."""

from __future__ import annotations

from lib.presentation.account_icons import (
    account_icon_groups,
    all_account_icon_keys,
    currency_glyph_label,
    currency_icon_key,
    is_valid_account_icon,
    parse_currency_icon_key,
)


def test_currency_icon_key_roundtrip() -> None:
    key = currency_icon_key("usd")
    assert key == "ccy_USD"
    assert parse_currency_icon_key(key) == "USD"
    assert parse_currency_icon_key("wallet") is None


def test_glyph_label() -> None:
    assert currency_glyph_label("USD", "$") == "$"
    assert currency_glyph_label("BTC", "Bitcoin") == "BTC"


def test_groups_and_validation() -> None:
    groups = account_icon_groups()
    assert groups
    keys = all_account_icon_keys()
    assert "wallet" in keys
    assert is_valid_account_icon("wallet")
    assert not is_valid_account_icon("not_a_real_icon_xyz")
