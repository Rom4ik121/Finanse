"""Tests for dashboard analytics period presets."""

from __future__ import annotations

from datetime import datetime, timezone

from lib.domain.use_cases.transactions import StatsPeriod
from lib.presentation.analytics_period import (
    format_chart_period_label,
    resolve_analytics_period,
)


def test_resolve_analytics_period_defaults_to_30_days() -> None:
    now = datetime(2026, 8, 12, 12, 0, tzinfo=timezone.utc)
    cfg = resolve_analytics_period("unknown", now)

    assert cfg.key == "30d"
    assert cfg.group_by == StatsPeriod.DAY
    assert cfg.date_from == datetime(2026, 7, 13, 12, 0, tzinfo=timezone.utc)
    assert cfg.date_to == now


def test_resolve_analytics_period_all_time_uses_monthly_buckets() -> None:
    now = datetime(2026, 8, 12, tzinfo=timezone.utc)
    cfg = resolve_analytics_period("all", now)

    assert cfg.date_from is None
    assert cfg.group_by == StatsPeriod.MONTH
    assert cfg.max_chart_points == 36


def test_format_chart_period_label() -> None:
    assert format_chart_period_label("2026-08-12", StatsPeriod.DAY) == "08-12"
    assert format_chart_period_label("2026-W32", StatsPeriod.WEEK) == "W32"
    assert format_chart_period_label("2026-08", StatsPeriod.MONTH) == "08"
