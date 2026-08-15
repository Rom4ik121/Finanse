"""Account icon key helpers."""

from __future__ import annotations

from lib.presentation.account_icons import (
    account_icon_groups,
    all_account_icon_keys,
    crypto_icon_keys,
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
    assert currency_glyph_label("BTC", "Bitcoin") == "₿"
    assert currency_glyph_label("USDT") == "₮"


def test_groups_and_validation() -> None:
    groups = account_icon_groups()
    assert groups
    keys = all_account_icon_keys()
    assert "wallet" in keys
    assert "currency_bitcoin" not in dict(groups)["icon_group.finance"]
    group_names = [name for name, _icons in groups]
    assert group_names == [
        "icon_group.finance",
        "icon_group.cards",
        "icon_group.fiat",
        "icon_group.crypto",
    ]
    assert is_valid_account_icon("wallet")
    assert not is_valid_account_icon("not_a_real_icon_xyz")


def test_all_catalog_cryptos_have_account_icons() -> None:
    groups = dict(account_icon_groups())
    crypto_keys = set(groups["icon_group.crypto"])
    expected = set(crypto_icon_keys())
    assert len(expected) >= 50
    assert expected <= crypto_keys
    for key in expected:
        assert is_valid_account_icon(key)
