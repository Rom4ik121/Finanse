"""In-app notification queue and reminder scheduling."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Optional
from uuid import uuid4

from lib.domain.entities.debt import Debt, DebtStatus
from lib.domain.entities.subscription import Subscription

logger = logging.getLogger("finanse.infrastructure.services.notification")


class NotificationKind(str, Enum):
    """Categories of in-app notifications."""

    INFO = "info"
    WARNING = "warning"
    DEBT_REMINDER = "debt_reminder"
    SUBSCRIPTION_REMINDER = "subscription_reminder"
    GOAL_MILESTONE = "goal_milestone"


@dataclass(slots=True)
class NotificationMessage:
    """A single in-app notification."""

    id: str
    title: str
    body: str
    kind: NotificationKind = NotificationKind.INFO
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    due_at: Optional[datetime] = None
    related_id: Optional[str] = None
    read: bool = False


class NotificationService:
    """In-memory notification queue with debt / subscription reminder helpers."""

    def __init__(self, *, default_lead_days: int = 3) -> None:
        self._messages: list[NotificationMessage] = []
        self._default_lead_days = default_lead_days

    def push(
        self,
        title: str,
        body: str,
        *,
        kind: NotificationKind = NotificationKind.INFO,
        due_at: Optional[datetime] = None,
        related_id: Optional[str] = None,
    ) -> NotificationMessage:
        """Enqueue a notification and return it."""
        message = NotificationMessage(
            id=str(uuid4()),
            title=title,
            body=body,
            kind=kind,
            due_at=due_at,
            related_id=related_id,
        )
        self._messages.append(message)
        logger.debug("Notification queued: %s (%s)", title, kind.value)
        return message

    def list_all(self, *, unread_only: bool = False) -> list[NotificationMessage]:
        """Return notifications (optionally unread only), newest first."""
        items = [m for m in self._messages if (not unread_only or not m.read)]
        return sorted(items, key=lambda m: m.created_at, reverse=True)

    def list_pending(self, *, now: Optional[datetime] = None) -> list[NotificationMessage]:
        """Return unread notifications that are due (or have no due time)."""
        moment = now or datetime.now(timezone.utc)
        pending: list[NotificationMessage] = []
        for message in self._messages:
            if message.read:
                continue
            if message.due_at is None or message.due_at <= moment:
                pending.append(message)
        return sorted(pending, key=lambda m: m.created_at, reverse=True)

    def mark_read(self, notification_id: str) -> bool:
        """Mark a notification as read. Returns whether it was found."""
        for message in self._messages:
            if message.id == notification_id:
                message.read = True
                return True
        return False

    def clear_read(self) -> int:
        """Remove read notifications. Returns count removed."""
        before = len(self._messages)
        self._messages = [m for m in self._messages if not m.read]
        return before - len(self._messages)

    def clear_all(self) -> None:
        """Drop the entire queue."""
        self._messages.clear()

    def schedule_debt_reminders(
        self,
        debts: list[Debt],
        *,
        lead_days: Optional[int] = None,
        now: Optional[datetime] = None,
    ) -> list[NotificationMessage]:
        """Create pending reminders for active debts due within ``lead_days``."""
        moment = now or datetime.now(timezone.utc)
        lead = timedelta(days=lead_days if lead_days is not None else self._default_lead_days)
        created: list[NotificationMessage] = []

        for debt in debts:
            if debt.status != DebtStatus.ACTIVE or debt.due_date is None:
                continue
            due = debt.due_date
            if due.tzinfo is None:
                due = due.replace(tzinfo=timezone.utc)
            if due < moment or due > moment + lead:
                continue
            if self._has_related(debt.id, NotificationKind.DEBT_REMINDER):
                continue
            message = self.push(
                title="Debt due soon",
                body=(
                    f"{debt.counterparty}: {debt.remaining_amount} {debt.currency} "
                    f"due {due.date().isoformat()}"
                ),
                kind=NotificationKind.DEBT_REMINDER,
                due_at=due,
                related_id=debt.id,
            )
            created.append(message)

        logger.info("Scheduled %s debt reminders", len(created))
        return created

    def schedule_subscription_reminders(
        self,
        subscriptions: list[Subscription],
        *,
        lead_days: Optional[int] = None,
        now: Optional[datetime] = None,
    ) -> list[NotificationMessage]:
        """Create pending reminders for active subscriptions billing soon."""
        moment = now or datetime.now(timezone.utc)
        lead = timedelta(days=lead_days if lead_days is not None else self._default_lead_days)
        created: list[NotificationMessage] = []

        for sub in subscriptions:
            if not sub.is_active:
                continue
            due = sub.next_billing_date
            if due.tzinfo is None:
                due = due.replace(tzinfo=timezone.utc)
            if due < moment or due > moment + lead:
                continue
            if self._has_related(sub.id, NotificationKind.SUBSCRIPTION_REMINDER):
                continue
            message = self.push(
                title="Subscription billing soon",
                body=(
                    f"{sub.name}: {sub.amount} {sub.currency} "
                    f"on {due.date().isoformat()}"
                ),
                kind=NotificationKind.SUBSCRIPTION_REMINDER,
                due_at=due,
                related_id=sub.id,
            )
            created.append(message)

        logger.info("Scheduled %s subscription reminders", len(created))
        return created

    def _has_related(self, related_id: str, kind: NotificationKind) -> bool:
        return any(
            m.related_id == related_id and m.kind == kind and not m.read
            for m in self._messages
        )
