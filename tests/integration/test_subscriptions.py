"""Subscriptions CRUD and due processing."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from lib.domain.entities.subscription import Periodicity
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
        account = await container.account_repository.get_by_id(acc.id)
        assert account is not None
        assert account.balance == Decimal("450.00")

        refreshed = await container.subscription_repository.get_by_id(sub.id)
        assert refreshed is not None
        assert refreshed.next_billing_date > due
        assert refreshed.last_charged_at is not None

    run_async(_run())
