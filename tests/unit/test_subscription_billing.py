"""Pure subscription billing date helpers."""

from __future__ import annotations

from datetime import datetime, timezone

from lib.domain.entities.subscription import Periodicity
from lib.domain.use_cases.subscriptions import _add_months, _advance_billing_date


def test_add_months_clamps_day() -> None:
    jan31 = datetime(2024, 1, 31, tzinfo=timezone.utc)
    feb = _add_months(jan31, 1)
    assert feb.month == 2
    assert feb.day == 29  # 2024 leap year


def test_advance_monthly_and_yearly() -> None:
    base = datetime(2024, 5, 15, 12, 0, tzinfo=timezone.utc)
    monthly = _advance_billing_date(base, Periodicity.MONTHLY)
    yearly = _advance_billing_date(base, Periodicity.YEARLY)
    assert monthly == datetime(2024, 6, 15, 12, 0, tzinfo=timezone.utc)
    assert yearly == datetime(2025, 5, 15, 12, 0, tzinfo=timezone.utc)
