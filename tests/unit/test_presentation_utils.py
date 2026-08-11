"""Presentation formatting helpers (no Flet page required)."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from lib.presentation.utils import format_date, format_money, tr


def test_format_money() -> None:
    assert format_money("1234.5", "UZS") == "1 234.50 UZS"
    assert format_money(10, "RUB", signed=True).startswith("+")
    assert "−" in format_money(-5, "RUB", signed=True)


def test_format_date() -> None:
    dt = datetime(2024, 5, 1, 14, 30, tzinfo=timezone.utc)
    assert format_date(dt) == "01.05.2024"
    assert format_date(dt, with_time=True) == "01.05.2024 14:30"
    assert format_date(None) == "—"


def test_tr_format_kwargs() -> None:
    text = tr("subscription.next_billing", "en", date="01.01.2025")
    assert "01.01.2025" in text
    assert tr("nav.home", "uz") == "Bosh sahifa"
