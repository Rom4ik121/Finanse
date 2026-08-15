"""Ticker search matching for currency pickers."""

from __future__ import annotations

from lib.presentation.widgets.currency_ticker_picker import currency_row_matches


def test_matches_ticker_prefix() -> None:
    row = {"code": "USD", "name": "US Dollar", "symbol": "$"}
    assert currency_row_matches(row, "us")
    assert currency_row_matches(row, "USD")
    assert currency_row_matches(row, "$")
    assert not currency_row_matches(row, "BTC")


def test_matches_name_and_crypto() -> None:
    row = {"code": "SOL", "name": "Solana", "symbol": "SOL"}
    assert currency_row_matches(row, "sol")
    assert currency_row_matches(row, "sola")
