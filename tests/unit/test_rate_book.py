"""Unit tests for in-memory FX RateBook."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from lib.domain.entities.currency import ExchangeRate
from lib.domain.services.rate_book import RateBook


def test_rate_book_direct_and_inverse() -> None:
    book = RateBook(
        [
            ExchangeRate(
                base="USD",
                quote="UZS",
                rate=Decimal("12500"),
                updated_at=datetime.now(timezone.utc),
            )
        ]
    )
    assert book.convert(Decimal("2"), "USD", "UZS") == Decimal("25000.00")
    assert book.convert(Decimal("25000"), "UZS", "USD") == Decimal("2.00")


def test_rate_book_cross_via_usd() -> None:
    now = datetime.now(timezone.utc)
    book = RateBook(
        [
            ExchangeRate(base="UZS", quote="USD", rate=Decimal("0.00008"), updated_at=now),
            ExchangeRate(base="UZS", quote="BTC", rate=Decimal("0.0000000008"), updated_at=now),
        ]
    )
    # BTC→UZS = 1/0.0000000008 = 1_250_000_000; × UZS→USD = 100_000
    converted = book.convert(Decimal("1"), "BTC", "USD")
    assert converted == Decimal("100000.00")


def test_rate_book_missing_returns_none() -> None:
    book = RateBook(())
    assert book.convert(Decimal("1"), "AAA", "BBB") is None
