"""NotificationService in-memory queue."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from lib.domain.entities.debt import Debt, DebtDirection, DebtStatus
from lib.domain.entities.subscription import Periodicity, Subscription
from lib.infrastructure.services.notification_service import (
    NotificationKind,
    NotificationService,
)


def test_push_and_list() -> None:
    svc = NotificationService()
    msg = svc.push("Hi", "Body", kind=NotificationKind.INFO)
    assert msg.id
    assert svc.list_all()[0].title == "Hi"
    assert len(svc.list_pending()) == 1


def test_mark_read_and_clear() -> None:
    svc = NotificationService()
    msg = svc.push("A", "B")
    svc.mark_read(msg.id)
    assert svc.list_all(unread_only=True) == []
    svc.clear_all()
    assert svc.list_all() == []


def test_schedule_debt_reminders() -> None:
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
    created = svc.schedule_debt_reminders([debt], language="ru")
    assert created
    assert created[0].kind is NotificationKind.DEBT_REMINDER
    assert created[0].title == "Скоро срок погашения долга"


def test_schedule_overdue_debt_reminders() -> None:
    svc = NotificationService(default_lead_days=3)
    due = datetime.now(timezone.utc) - timedelta(days=1)
    debt = Debt(
        counterparty="Bank",
        amount=100,
        remaining_amount=100,
        direction=DebtDirection.I_OWE,
        due_date=due,
        status=DebtStatus.ACTIVE,
    )
    created = svc.schedule_debt_reminders([debt], language="ru")
    assert created
    assert created[0].kind is NotificationKind.DEBT_REMINDER


def test_clear_kinds() -> None:
    svc = NotificationService()
    svc.push("A", "B", kind=NotificationKind.DEBT_REMINDER)
    svc.push("C", "D", kind=NotificationKind.INFO)
    assert svc.clear_kinds(NotificationKind.DEBT_REMINDER) == 1
    assert len(svc.list_all()) == 1
    assert svc.list_all()[0].kind is NotificationKind.INFO


def test_schedule_subscription_reminders() -> None:
    svc = NotificationService(default_lead_days=3)
    next_bill = datetime.now(timezone.utc) + timedelta(days=1)
    sub = Subscription(
        name="Netflix",
        amount=10,
        account_id="a1",
        next_billing_date=next_bill,
        periodicity=Periodicity.MONTHLY,
        is_active=True,
    )
    created = svc.schedule_subscription_reminders([sub])
    assert created
    assert created[0].kind is NotificationKind.SUBSCRIPTION_REMINDER
