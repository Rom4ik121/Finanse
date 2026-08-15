"""Helpers for in-app notification badges (no banner spam on home)."""

from __future__ import annotations

from typing import Any, Iterable, Optional, Sequence

from lib.infrastructure.services.notification_service import (
    NotificationKind,
    NotificationMessage,
)

GOAL_ALERT_KINDS = (
    NotificationKind.GOAL_OFF_TRACK,
    NotificationKind.GOAL_MILESTONE,
)
DEBT_ALERT_KINDS = (
    NotificationKind.DEBT_REMINDER,
    NotificationKind.DEBT_OVERDUE,
    NotificationKind.DEBT_IDLE,
)
SUBSCRIPTION_ALERT_KINDS = (
    NotificationKind.SUBSCRIPTION_REMINDER,
    NotificationKind.SUBSCRIPTION_SKIPPED,
    NotificationKind.SUBSCRIPTION_EXPIRED,
)
BUDGET_ALERT_KINDS = (
    NotificationKind.BUDGET_WARNING,
    NotificationKind.BUDGET_OVER,
)


def _kinds_enabled(settings: Any, kinds: Sequence[NotificationKind]) -> list[NotificationKind]:
    if settings is None or not getattr(settings, "notifications_enabled", True):
        return []
    enabled: list[NotificationKind] = []
    for kind in kinds:
        if kind in (
            NotificationKind.GOAL_OFF_TRACK,
            NotificationKind.GOAL_MILESTONE,
        ):
            if getattr(settings, "goal_milestones", True):
                enabled.append(kind)
        elif kind in (
            NotificationKind.DEBT_REMINDER,
            NotificationKind.DEBT_OVERDUE,
            NotificationKind.DEBT_IDLE,
        ):
            if getattr(settings, "debt_reminders", True):
                enabled.append(kind)
        elif kind in (
            NotificationKind.SUBSCRIPTION_REMINDER,
            NotificationKind.SUBSCRIPTION_SKIPPED,
            NotificationKind.SUBSCRIPTION_EXPIRED,
        ):
            if getattr(settings, "subscription_reminders", True):
                enabled.append(kind)
        elif kind in (
            NotificationKind.BUDGET_WARNING,
            NotificationKind.BUDGET_OVER,
        ):
            if getattr(settings, "budget_alerts", True):
                enabled.append(kind)
    return enabled


def pending_messages(
    container: Any,
    settings: Any,
    kinds: Sequence[NotificationKind],
) -> list[NotificationMessage]:
    """Unread pending notifications filtered by kind and user settings."""
    notifier = getattr(container, "notification_service", None)
    if notifier is None:
        return []
    allowed = set(_kinds_enabled(settings, kinds))
    if not allowed:
        return []
    return [m for m in notifier.list_pending() if m.kind in allowed]


def pending_count(
    container: Any,
    settings: Any,
    kinds: Sequence[NotificationKind],
) -> int:
    return len(pending_messages(container, settings, kinds))


def pending_related_ids(
    container: Any,
    settings: Any,
    kinds: Sequence[NotificationKind],
) -> set[str]:
    ids: set[str] = set()
    for message in pending_messages(container, settings, kinds):
        if message.related_id:
            ids.add(message.related_id)
    return ids


def mark_related_read(
    container: Any,
    related_id: str,
    kinds: Iterable[NotificationKind] | None = None,
) -> int:
    """Mark unread notifications for ``related_id`` as read. Returns count."""
    notifier = getattr(container, "notification_service", None)
    if notifier is None or not related_id:
        return 0
    kind_set = set(kinds) if kinds is not None else None
    marked = 0
    for message in list(notifier.list_all(unread_only=True)):
        if message.related_id != related_id:
            continue
        if kind_set is not None and message.kind not in kind_set:
            continue
        if notifier.mark_read(message.id):
            marked += 1
    return marked
