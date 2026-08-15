"""Subscriptions CRUD and due processing."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from lib.domain.entities.subscription import Periodicity, SubscriptionStatus
from tests.conftest import run_async
from tests.factories import make_account, make_subscription


def test_subscription_crud(container) -> None:
    async def _run() -> None:
        acc = await container.create_account.execute(make_account())
        sub = await container.create_subscription.execute(
            make_subscription(acc.id, name="Spotify", amount="15")
        )
        listed = await container.list_subscriptions.execute(active_only=True)
        assert any(s.id == sub.id for s in listed)

        updated = await container.update_subscription.execute(
            sub.model_copy(update={"amount": Decimal("20")})
        )
        assert updated.amount == Decimal("20.00")
        assert await container.delete_subscription.execute(sub.id) is True

    run_async(_run())


def test_process_due_subscriptions_charges_account(container) -> None:
    async def _run() -> None:
        acc = await container.create_account.execute(make_account(balance="500"))
        due = datetime.now(timezone.utc) - timedelta(days=1)
        sub = await container.create_subscription.execute(
            make_subscription(
                acc.id,
                amount="50",
                next_billing=due,
                periodicity=Periodicity.MONTHLY,
            )
        )
        txs = await container.process_due_subscriptions.execute()
        assert len(txs) >= 1
        assert all(tx.subscription_id == sub.id for tx in txs)
        account = await container.account_repository.get_by_id(acc.id)
        assert account is not None
        assert account.balance == Decimal("450.00")

        refreshed = await container.subscription_repository.get_by_id(sub.id)
        assert refreshed is not None
        assert refreshed.next_billing_date > due
        assert refreshed.last_charged_at is not None
        assert refreshed.payments_made >= 1

    run_async(_run())


def test_process_due_subscriptions_catchup_multiple_periods(container) -> None:
    async def _run() -> None:
        acc = await container.create_account.execute(make_account(balance="1000"))
        due = datetime.now(timezone.utc) - timedelta(days=95)
        await container.create_subscription.execute(
            make_subscription(
                acc.id,
                amount="100",
                next_billing=due,
                periodicity=Periodicity.MONTHLY,
            )
        )
        txs = await container.process_due_subscriptions.execute()
        assert len(txs) >= 3
        account = await container.account_repository.get_by_id(acc.id)
        assert account is not None
        assert account.balance == Decimal("1000.00") - (Decimal("100.00") * len(txs))

    run_async(_run())


def test_process_due_skips_when_insufficient_balance(container) -> None:
    async def _run() -> None:
        settings = await container.get_settings.execute()
        await container.update_settings.execute(
            settings.model_copy(update={"check_balance_before_subscription": True})
        )
        acc = await container.create_account.execute(make_account(balance="10"))
        due = datetime.now(timezone.utc) - timedelta(days=1)
        sub = await container.create_subscription.execute(
            make_subscription(acc.id, amount="50", next_billing=due)
        )
        txs = await container.process_due_subscriptions.execute()
        assert txs == []
        account = await container.account_repository.get_by_id(acc.id)
        assert account is not None
        assert account.balance == Decimal("10.00")
        refreshed = await container.subscription_repository.get_by_id(sub.id)
        assert refreshed is not None
        assert refreshed.next_billing_date == due
        assert refreshed.last_skip_date is not None

    run_async(_run())


def test_pause_skips_billing_resume_advances(container) -> None:
    async def _run() -> None:
        acc = await container.create_account.execute(make_account(balance="500"))
        due = datetime.now(timezone.utc) - timedelta(days=5)
        sub = await container.create_subscription.execute(
            make_subscription(acc.id, amount="20", next_billing=due)
        )
        paused = await container.pause_subscription.execute(sub.id)
        assert paused.status == SubscriptionStatus.PAUSED
        txs = await container.process_due_subscriptions.execute()
        assert txs == []
        resumed = await container.resume_subscription.execute(sub.id)
        assert resumed.status == SubscriptionStatus.ACTIVE
        assert resumed.next_billing_date > datetime.now(timezone.utc) - timedelta(
            minutes=1
        )

    run_async(_run())


def test_max_payments_expires_subscription(container) -> None:
    async def _run() -> None:
        acc = await container.create_account.execute(make_account(balance="500"))
        due = datetime.now(timezone.utc) - timedelta(days=1)
        sub = await container.create_subscription.execute(
            make_subscription(
                acc.id,
                amount="10",
                next_billing=due,
                max_payments=1,
            )
        )
        # Already at limit before charging.
        await container.update_subscription.execute(
            sub.model_copy(update={"payments_made": 1})
        )
        txs = await container.process_due_subscriptions.execute()
        assert txs == []
        refreshed = await container.subscription_repository.get_by_id(sub.id)
        assert refreshed is not None
        assert refreshed.status == SubscriptionStatus.EXPIRED

    run_async(_run())


def test_custom_periodicity_and_charge_now(container) -> None:
    async def _run() -> None:
        acc = await container.create_account.execute(make_account(balance="200"))
        due = datetime.now(timezone.utc)
        sub = await container.create_subscription.execute(
            make_subscription(
                acc.id,
                amount="15",
                next_billing=due,
                periodicity=Periodicity.CUSTOM,
                custom_interval_days=10,
            )
        )
        tx = await container.charge_subscription_now.execute(
            sub.id, check_balance=False
        )
        assert tx.subscription_id == sub.id
        refreshed = await container.subscription_repository.get_by_id(sub.id)
        assert refreshed is not None
        assert refreshed.next_billing_date >= due + timedelta(days=10)
        history = await container.list_transactions.execute(subscription_id=sub.id)
        assert len(history) == 1
        assert await container.delete_subscription_charge.execute(
            history[0].id, subscription_id=sub.id
        )

    run_async(_run())


def test_subscription_analytics(container) -> None:
    async def _run() -> None:
        acc = await container.create_account.execute(make_account(balance="500"))
        due = datetime.now(timezone.utc) - timedelta(days=1)
        await container.create_subscription.execute(
            make_subscription(acc.id, amount="40", next_billing=due)
        )
        await container.process_due_subscriptions.execute()
        stats = await container.get_subscription_analytics.execute(
            base_currency="RUB"
        )
        assert stats.total_active >= 1
        assert stats.total_spent >= Decimal("40.00")
        assert stats.total_monthly_cost >= Decimal("40.00")

    run_async(_run())


def test_auto_charge_off_skips_process_due(container) -> None:
    async def _run() -> None:
        acc = await container.create_account.execute(make_account(balance="500"))
        due = datetime.now(timezone.utc) - timedelta(days=1)
        sub = await container.create_subscription.execute(
            make_subscription(acc.id, amount="40", next_billing=due)
        )
        await container.update_subscription.execute(
            sub.model_copy(update={"auto_charge": False})
        )
        txs = await container.process_due_subscriptions.execute()
        assert txs == []
        account = await container.account_repository.get_by_id(acc.id)
        assert account is not None
        assert account.balance == Decimal("500.00")

    run_async(_run())


def test_end_date_expires_without_charge(container) -> None:
    async def _run() -> None:
        acc = await container.create_account.execute(make_account(balance="500"))
        due = datetime.now(timezone.utc) - timedelta(days=1)
        sub = await container.create_subscription.execute(
            make_subscription(acc.id, amount="25", next_billing=due)
        )
        # End date clearly before the due billing day (UTC).
        await container.update_subscription.execute(
            sub.model_copy(update={"end_date": (due - timedelta(days=3)).date()})
        )
        txs = await container.process_due_subscriptions.execute()
        assert txs == []
        refreshed = await container.subscription_repository.get_by_id(sub.id)
        assert refreshed is not None
        assert refreshed.status == SubscriptionStatus.EXPIRED

    run_async(_run())
