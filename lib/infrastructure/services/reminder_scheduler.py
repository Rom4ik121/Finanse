"""Schedule debt/subscription/goal reminders based on user settings."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from lib.domain.entities.debt import DebtStatus
from lib.domain.entities.goal import GoalStatus
from lib.infrastructure.services.localization import t
from lib.infrastructure.services.notification_service import (
    NotificationKind,
    NotificationMessage,
)

if TYPE_CHECKING:
    from lib.domain.entities.settings import AppSettings

logger = logging.getLogger("finanse.infrastructure.services.reminder_scheduler")


async def schedule_reminders(
    container: Any,
    settings: "AppSettings",
    *,
    language: str = "ru",
) -> list[NotificationMessage]:
    """Create in-app reminders when notifications are enabled.

    Returns newly queued reminder messages.
    """
    notifier = getattr(container, "notification_service", None)
    if notifier is None:
        return []

    if not settings.notifications_enabled:
        notifier.clear_all()
        return []

    drop: list[NotificationKind] = []
    if not settings.debt_reminders:
        drop.extend(
            [
                NotificationKind.DEBT_REMINDER,
                NotificationKind.DEBT_OVERDUE,
                NotificationKind.DEBT_IDLE,
            ]
        )
    if not settings.subscription_reminders:
        drop.extend(
            [
                NotificationKind.SUBSCRIPTION_REMINDER,
                NotificationKind.SUBSCRIPTION_SKIPPED,
                NotificationKind.SUBSCRIPTION_EXPIRED,
            ]
        )
    if not settings.goal_milestones:
        drop.append(NotificationKind.GOAL_MILESTONE)
        drop.append(NotificationKind.GOAL_OFF_TRACK)
    if drop:
        notifier.clear_kinds(*drop)

    created: list[NotificationMessage] = []
    try:
        if settings.debt_reminders and container.list_debts is not None:
            created.extend(
                await _schedule_debt_alerts(container, notifier, language=language)
            )
        if settings.subscription_reminders and container.list_subscriptions is not None:
            subs = await container.list_subscriptions.execute(active_only=True)
            account_names: dict[str, str] = {}
            account_balances: dict[str, object] = {}
            list_accounts = getattr(container, "list_accounts", None)
            if list_accounts is not None and getattr(list_accounts, "execute", None):
                try:
                    accounts = await list_accounts.execute(active_only=False)
                    account_names = {a.id: a.name for a in accounts}
                    account_balances = {a.id: a.balance for a in accounts}
                except Exception:  # noqa: BLE001
                    logger.debug("Could not load accounts for subscription reminders")
            lead_days = int(getattr(settings, "reminder_days", 3) or 3)
            created.extend(
                notifier.schedule_subscription_reminders(
                    subs,
                    language=language,
                    lead_days=lead_days,
                    account_names=account_names,
                    account_balances=account_balances,
                )
            )
        if settings.goal_milestones:
            created.extend(
                await _schedule_goal_off_track(container, notifier, language=language)
            )
    except Exception:  # noqa: BLE001
        logger.exception("Failed to schedule reminders")
        return created

    if created:
        logger.info("Scheduled %s reminder(s)", len(created))
    return created


async def _schedule_debt_alerts(
    container: Any,
    notifier: Any,
    *,
    language: str,
) -> list[NotificationMessage]:
    """Overdue status sync + due-soon / overdue / idle notifications."""
    created: list[NotificationMessage] = []
    mark_overdue = getattr(container, "mark_overdue_debts", None)
    if mark_overdue is not None:
        try:
            overdue_debts = await mark_overdue.execute()
            for debt in overdue_debts:
                if notifier._has_related(debt.id, NotificationKind.DEBT_OVERDUE):
                    continue
                created.append(
                    notifier.push(
                        title=t("notify.debt_overdue_title", language),
                        body=t("notify.debt_overdue_body", language).format(
                            name=debt.counterparty,
                            amount=f"{debt.remaining_amount} {debt.currency}",
                        ),
                        kind=NotificationKind.DEBT_OVERDUE,
                        related_id=debt.id,
                    )
                )
        except Exception:  # noqa: BLE001
            logger.exception("Failed to mark overdue debts")

    list_debts = getattr(container, "list_debts", None)
    if list_debts is None:
        return created

    now = datetime.now(timezone.utc)
    lead = timedelta(days=3)
    active = await list_debts.execute(status=DebtStatus.ACTIVE)
    overdue = await list_debts.execute(status=DebtStatus.OVERDUE)
    open_debts = [*active, *overdue]

    # Due-soon reminders (existing helper still works for ACTIVE with due_date).
    created.extend(
        notifier.schedule_debt_reminders(active, language=language, lead_days=3)
    )

    # Ensure overdue debts also get an overdue notice if not already pushed.
    for debt in overdue:
        if notifier._has_related(debt.id, NotificationKind.DEBT_OVERDUE):
            continue
        created.append(
            notifier.push(
                title=t("notify.debt_overdue_title", language),
                body=t("notify.debt_overdue_body", language).format(
                    name=debt.counterparty,
                    amount=f"{debt.remaining_amount} {debt.currency}",
                ),
                kind=NotificationKind.DEBT_OVERDUE,
                related_id=debt.id,
            )
        )

    # Idle: no payments for 30+ days — remind at most weekly (dedupe unread).
    list_tx = getattr(container, "list_transactions", None)
    if list_tx is None:
        return created
    idle_cutoff = now - timedelta(days=30)
    for debt in open_debts:
        if debt.remaining_amount <= 0:
            continue
        if notifier._has_related(debt.id, NotificationKind.DEBT_IDLE):
            continue
        try:
            txs = await list_tx.execute(debt_id=debt.id, limit=1, offset=0)
        except Exception:  # noqa: BLE001
            continue
        last_pay = txs[0].date if txs else (debt.started_at or debt.created_at)
        if last_pay.tzinfo is None:
            last_pay = last_pay.replace(tzinfo=timezone.utc)
        if last_pay > idle_cutoff:
            continue
        # Skip if due soon / overdue already covering this debt recently.
        if debt.due_date is not None:
            due = debt.due_date
            if due.tzinfo is None:
                due = due.replace(tzinfo=timezone.utc)
            if due <= now + lead:
                continue
        created.append(
            notifier.push(
                title=t("notify.debt_idle_title", language),
                body=t("notify.debt_idle_body", language).format(
                    name=debt.counterparty
                ),
                kind=NotificationKind.DEBT_IDLE,
                related_id=debt.id,
            )
        )
    return created


async def _schedule_goal_off_track(
    container: Any,
    notifier: Any,
    *,
    language: str,
) -> list[NotificationMessage]:
    """Notify about active goals that are behind schedule."""
    list_goals = getattr(container, "list_goals", None)
    get_projection = getattr(container, "get_goal_projection", None)
    if list_goals is None or get_projection is None:
        return []

    goals = await list_goals.execute(status=GoalStatus.ACTIVE)
    created: list[NotificationMessage] = []
    for goal in goals:
        if goal.deadline is None:
            continue
        try:
            projection = await get_projection.execute(goal.id)
        except Exception:  # noqa: BLE001
            logger.exception("Goal projection failed for %s", goal.id)
            continue
        if projection.is_on_track is not False:
            continue
        if notifier._has_related(goal.id, NotificationKind.GOAL_OFF_TRACK):
            continue
        required = projection.required_monthly_contribution or Decimal("0")
        amount_txt = f"{required} {goal.currency}"
        created.append(
            notifier.push(
                title=t("notify.goal_off_track_title", language),
                body=t(
                    "notify.goal_off_track_body",
                    language,
                ).format(name=goal.name, amount=amount_txt),
                kind=NotificationKind.GOAL_OFF_TRACK,
                related_id=goal.id,
            )
        )
    return created
