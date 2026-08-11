"""Subscription-related use cases."""

from __future__ import annotations

import calendar
from datetime import datetime, timezone
from typing import Optional

from lib.domain.entities.money import quantize_money
from lib.domain.entities.subscription import Periodicity, Subscription
from lib.domain.entities.transaction import Transaction, TransactionType
from lib.domain.repositories.account_repository import AccountRepository
from lib.domain.repositories.subscription_repository import SubscriptionRepository
from lib.domain.repositories.transaction_repository import TransactionRepository


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _add_months(dt: datetime, months: int) -> datetime:
    """Add calendar months, clamping the day to the target month's length."""
    month_index = dt.month - 1 + months
    year = dt.year + month_index // 12
    month = month_index % 12 + 1
    day = min(dt.day, calendar.monthrange(year, month)[1])
    return dt.replace(year=year, month=month, day=day)


def _advance_billing_date(current: datetime, periodicity: Periodicity) -> datetime:
    """Move billing date forward by one period."""
    if periodicity == Periodicity.YEARLY:
        return _add_months(current, 12)
    return _add_months(current, 1)



class CreateSubscriptionUseCase:
    """Create a recurring subscription."""

    def __init__(self, subscriptions: SubscriptionRepository) -> None:
        self._subscriptions = subscriptions

    async def execute(self, subscription: Subscription) -> Subscription:
        """Persist a new subscription."""
        created = subscription.model_copy(
            update={
                "amount": quantize_money(subscription.amount),
                "created_at": subscription.created_at or _utc_now(),
                "updated_at": _utc_now(),
            }
        )
        return await self._subscriptions.create(created)


class UpdateSubscriptionUseCase:
    """Update an existing subscription."""

    def __init__(self, subscriptions: SubscriptionRepository) -> None:
        self._subscriptions = subscriptions

    async def execute(self, subscription: Subscription) -> Subscription:
        """Update subscription fields."""
        existing = await self._subscriptions.get_by_id(subscription.id)
        if existing is None:
            raise ValueError(f"Subscription not found: {subscription.id}")
        updated = subscription.model_copy(
            update={
                "amount": quantize_money(subscription.amount),
                "updated_at": _utc_now(),
                "created_at": existing.created_at,
            }
        )
        return await self._subscriptions.update(updated)


class DeleteSubscriptionUseCase:
    """Delete a subscription."""

    def __init__(self, subscriptions: SubscriptionRepository) -> None:
        self._subscriptions = subscriptions

    async def execute(self, subscription_id: str) -> bool:
        """Remove a subscription by id."""
        return await self._subscriptions.delete(subscription_id)


class ListSubscriptionsUseCase:
    """List subscriptions."""

    def __init__(self, subscriptions: SubscriptionRepository) -> None:
        self._subscriptions = subscriptions

    async def execute(
        self,
        *,
        active_only: bool = False,
        account_id: Optional[str] = None,
    ) -> list[Subscription]:
        """Return subscriptions with optional filters."""
        return await self._subscriptions.list(
            active_only=active_only,
            account_id=account_id,
        )


class ProcessDueSubscriptionsUseCase:
    """Charge due subscriptions as expense transactions and advance billing dates."""

    def __init__(
        self,
        subscriptions: SubscriptionRepository,
        transactions: TransactionRepository,
        accounts: AccountRepository,
    ) -> None:
        self._subscriptions = subscriptions
        self._transactions = transactions
        self._accounts = accounts

    async def execute(self, *, as_of: Optional[datetime] = None) -> list[Transaction]:
        """Process all active subscriptions due on/before ``as_of`` (UTC now by default).

        For each due subscription:
        - create an expense transaction
        - decrease the linked account balance
        - set ``last_charged_at`` and advance ``next_billing_date``
        """
        as_of = as_of or _utc_now()
        if as_of.tzinfo is None:
            as_of = as_of.replace(tzinfo=timezone.utc)

        due = await self._subscriptions.list_due(as_of)
        created_txs: list[Transaction] = []

        for sub in due:
            account = await self._accounts.get_by_id(sub.account_id)
            if account is None:
                continue

            amount = quantize_money(sub.amount)
            now = _utc_now()
            tx = Transaction(
                account_id=sub.account_id,
                amount=amount,
                category=sub.category,
                tags=["subscription"],
                date=sub.next_billing_date,
                comment=sub.comment or f"Subscription: {sub.name}",
                type=TransactionType.EXPENSE,
                currency=sub.currency or account.currency,
                created_at=now,
                updated_at=now,
            )
            saved_tx = await self._transactions.create(tx)
            account.balance = quantize_money(account.balance - amount)
            await self._accounts.update(account)

            # Advance through any skipped periods so we catch up.
            next_date = sub.next_billing_date
            if next_date.tzinfo is None:
                next_date = next_date.replace(tzinfo=timezone.utc)
            while next_date <= as_of:
                next_date = _advance_billing_date(next_date, sub.periodicity)

            sub.last_charged_at = now
            sub.next_billing_date = next_date
            sub.updated_at = now
            await self._subscriptions.update(sub)
            created_txs.append(saved_tx)

        return created_txs
