"""Analytics chart period presets for the dashboard."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from lib.domain.use_cases.transactions import StatsPeriod

ANALYTICS_PERIOD_KEYS = ("7d", "30d", "90d", "180d", "365d", "all")
DEFAULT_ANALYTICS_PERIOD = "30d"


@dataclass(frozen=True)
class AnalyticsPeriodConfig:
    """Resolved date range and grouping for dashboard charts."""

    key: str
    date_from: datetime | None
    date_to: datetime
    group_by: StatsPeriod
    max_chart_points: int | None


def resolve_analytics_period(key: str, now: datetime) -> AnalyticsPeriodConfig:
    """Map a preset key to query bounds and chart granularity."""
    if key == "7d":
        return AnalyticsPeriodConfig(
            key=key,
            date_from=now - timedelta(days=7),
            date_to=now,
            group_by=StatsPeriod.DAY,
            max_chart_points=None,
        )
    if key == "90d":
        return AnalyticsPeriodConfig(
            key=key,
            date_from=now - timedelta(days=90),
            date_to=now,
            group_by=StatsPeriod.WEEK,
            max_chart_points=None,
        )
    if key == "180d":
        return AnalyticsPeriodConfig(
            key=key,
            date_from=now - timedelta(days=180),
            date_to=now,
            group_by=StatsPeriod.WEEK,
            max_chart_points=None,
        )
    if key == "365d":
        return AnalyticsPeriodConfig(
            key=key,
            date_from=now - timedelta(days=365),
            date_to=now,
            group_by=StatsPeriod.MONTH,
            max_chart_points=None,
        )
    if key == "all":
        return AnalyticsPeriodConfig(
            key=key,
            date_from=None,
            date_to=now,
            group_by=StatsPeriod.MONTH,
            max_chart_points=36,
        )
    # Default and explicit 30d.
    return AnalyticsPeriodConfig(
        key="30d",
        date_from=now - timedelta(days=30),
        date_to=now,
        group_by=StatsPeriod.DAY,
        max_chart_points=None,
    )


def format_chart_period_label(period: str, group_by: StatsPeriod) -> str:
    """Short x-axis label for chart buckets."""
    if group_by == StatsPeriod.DAY:
        return period[-5:] if len(period) >= 5 else period
    if group_by == StatsPeriod.WEEK:
        if "-W" in period:
            return f"W{period.split('-W', 1)[1]}"
        return period[-3:]
    return period[5:7] if len(period) >= 7 else period
