"""Tests for reminder scheduling from settings."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from lib.domain.entities.debt import Debt, DebtDirection, DebtStatus
from lib.domain.entities.settings import AppSettings
from lib.domain.entities.subscription import Periodicity, Subscription
from lib.infrastructure.services.notification_service import (
    NotificationKind,
    NotificationService,
)
from lib.infrastructure.services.reminder_scheduler import schedule_reminders


@pytest.mark.asyncio
async def test_schedule_reminders_respects_master_switch() -> None:
    svc = NotificationService(default_lead_days=3)
    svc.push("stale", "body", kind=NotificationKind.DEBT_REMINDER)
    container = MagicMock()
    container.notification_service = svc
    container.list_debts = MagicMock()
    container.list_subscriptions = MagicMock()
    container.get_goal_projection = None
    container.list_goals = None

    settings = AppSettings(notifications_enabled=False, debt_reminders=True)
    assert await schedule_reminders(container, settings) == []
    container.list_debts.execute.assert_not_called()
    assert svc.list_all() == []


@pytest.mark.asyncio
async def test_schedule_reminders_creates_debt_and_subscription() -> None:
    svc = NotificationService(default_lead_days=3)
    due = datetime.now(timezone.utc) + timedelta(days=1)
    debt = Debt(
        counterparty="Bank",
        amount=100,
        remaining_amount=100,
        direction=DebtDirection.I_OWE,
        due_date=due,
        status=DebtStatus.ACTIVE,
    )
    sub = Subscription(
        name="Netflix",
        amount=10,
        account_id="a1",
        next_billing_date=due,
        periodicity=Periodicity.MONTHLY,
        is_active=True,
    )
    list_debts = MagicMock()

    async def _list_debts(**kwargs):
        status = kwargs.get("status")
        if status == DebtStatus.OVERDUE:
            return []
        return [debt]

    list_debts.execute = AsyncMock(side_effect=_list_debts)
    list_subscriptions = MagicMock()
    list_subscriptions.execute = AsyncMock(return_value=[sub])
    container = MagicMock()
    container.notification_service = svc
    container.list_debts = list_debts
    container.list_subscriptions = list_subscriptions
    container.mark_overdue_debts = None
    container.list_transactions = None
    container.get_goal_projection = None
    container.list_goals = None

    settings = AppSettings(
        notifications_enabled=True,
        debt_reminders=True,
        subscription_reminders=True,
        language="ru",
    )
    created = await schedule_reminders(container, settings, language="ru")
    assert len(created) == 2
    kinds = {item.kind for item in svc.list_pending()}
    assert NotificationKind.DEBT_REMINDER in kinds
    assert NotificationKind.SUBSCRIPTION_REMINDER in kinds


@pytest.mark.asyncio
async def test_schedule_goal_off_track_reminder() -> None:
    from decimal import Decimal

    from lib.domain.entities.goal import Goal, GoalStatus
    from lib.domain.use_cases.goals import GoalProjection

    svc = NotificationService(default_lead_days=3)
    now = datetime.now(timezone.utc)
    goal = Goal(
        name="Trip",
        target_amount=Decimal("1000"),
        current_amount=Decimal("50"),
        currency="RUB",
        deadline=now + timedelta(days=30),
        status=GoalStatus.ACTIVE,
    )
    projection = GoalProjection(
        goal_id=goal.id,
        required_monthly_contribution=Decimal("300"),
        projected_completion_date=now + timedelta(days=90),
        is_on_track=False,
        remaining_amount=Decimal("950"),
    )
    list_goals = MagicMock()
    list_goals.execute = AsyncMock(return_value=[goal])
    get_projection = MagicMock()
    get_projection.execute = AsyncMock(return_value=projection)
    container = MagicMock()
    container.notification_service = svc
    container.list_debts = None
    container.list_subscriptions = None
    container.list_goals = list_goals
    container.get_goal_projection = get_projection

    settings = AppSettings(
        notifications_enabled=True,
        debt_reminders=False,
        subscription_reminders=False,
        goal_milestones=True,
    )
    created = await schedule_reminders(container, settings, language="ru")
    assert len(created) == 1
    assert created[0].kind is NotificationKind.GOAL_OFF_TRACK
    assert "Trip" in created[0].body
