"""Currency page helpers."""

from __future__ import annotations

from decimal import Decimal

from lib.domain.entities.currency import Currency
from lib.presentation.pages.currencies import _format_rate, _matches_query


def test_format_rate_trims_zeros() -> None:
    assert _format_rate(Decimal("12500.00")) == "12500"
    assert _format_rate(Decimal("0.00080")) == "0.0008"
    assert _format_rate(Decimal("1.25")) == "1.25"


def test_matches_query_by_ticker_name_symbol() -> None:
    usd = Currency(code="USD", name="US Dollar", symbol="$", is_crypto=False)
    assert _matches_query(usd, "")
    assert _matches_query(usd, "usd")
    assert _matches_query(usd, "doll")
    assert _matches_query(usd, "$")
    assert not _matches_query(usd, "btc")
