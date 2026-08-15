"""Subscription-related use cases."""

from __future__ import annotations

import calendar
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Optional

from pydantic import BaseModel, Field

from lib.domain.entities.money import quantize_money
from lib.domain.entities.subscription import (
    Periodicity,
    Subscription,
    SubscriptionStatus,
)
from lib.domain.entities.transaction import Transaction, TransactionType
from lib.domain.repositories.account_repository import AccountRepository
from lib.domain.repositories.subscription_repository import SubscriptionRepository
from lib.domain.repositories.transaction_repository import TransactionRepository
from lib.domain.services.rate_book import RateBook

if TYPE_CHECKING:
    from lib.domain.repositories.currency_repository import CurrencyRepository
    from lib.domain.repositories.settings_repository import SettingsRepository
    from lib.domain.use_cases.transactions import DeleteTransactionUseCase


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _add_months(dt: datetime, months: int) -> datetime:
    """Add calendar months, clamping the day to the target month's length."""
    month_index = dt.month - 1 + months
    year = dt.year + month_index // 12
    month = month_index % 12 + 1
    day = min(dt.day, calendar.monthrange(year, month)[1])
    return dt.replace(year=year, month=month, day=day)


def advance_billing_date(
    current: datetime,
    periodicity: Periodicity,
    *,
    custom_interval_days: Optional[int] = None,
) -> datetime:
    """Move billing date forward by one period."""
    current = _as_utc(current)
    if periodicity == Periodicity.DAILY:
        return current + timedelta(days=1)
    if periodicity == Periodicity.WEEKLY:
        return current + timedelta(days=7)
    if periodicity == Periodicity.BIWEEKLY:
        return current + timedelta(days=14)
    if periodicity == Periodicity.MONTHLY:
        return _add_months(current, 1)
    if periodicity == Periodicity.QUARTERLY:
        return _add_months(current, 3)
    if periodicity == Periodicity.SEMI_ANNUAL:
        return _add_months(current, 6)
    if periodicity == Periodicity.YEARLY:
        return _add_months(current, 12)
    if periodicity == Periodicity.CUSTOM:
        days = custom_interval_days or 1
        return current + timedelta(days=days)
    return _add_months(current, 1)


# Backward-compatible alias used by unit tests.
_advance_billing_date = advance_billing_date


def monthly_equivalent(
    amount: Decimal,
    periodicity: Periodicity,
    *,
    custom_interval_days: Optional[int] = None,
) -> Decimal:
    """Convert a subscription amount into an approximate monthly cost."""
    amount = quantize_money(amount)
    if periodicity == Periodicity.DAILY:
        return quantize_money(amount * Decimal("30.4375"))
    if periodicity == Periodicity.WEEKLY:
        return quantize_money(amount * Decimal("52") / Decimal("12"))
    if periodicity == Periodicity.BIWEEKLY:
        return quantize_money(amount * Decimal("26") / Decimal("12"))
    if periodicity == Periodicity.MONTHLY:
        return amount
    if periodicity == Periodicity.QUARTERLY:
        return quantize_money(amount / Decimal("3"))
    if periodicity == Periodicity.SEMI_ANNUAL:
        return quantize_money(amount / Decimal("6"))
    if periodicity == Periodicity.YEARLY:
        return quantize_money(amount / Decimal("12"))
    if periodicity == Periodicity.CUSTOM:
        days = max(1, int(custom_interval_days or 1))
        return quantize_money(amount * Decimal("30.4375") / Decimal(days))
    return amount


def _sync_active(status: SubscriptionStatus) -> bool:
    return status == SubscriptionStatus.ACTIVE


class CreateSubscriptionUseCase:
    """Create a recurring subscription."""

    def __init__(self, subscriptions: SubscriptionRepository) -> None:
        self._subscriptions = subscriptions

    async def execute(self, subscription: Subscription) -> Subscription:
        """Persist a new subscription."""
        status = subscription.status or SubscriptionStatus.ACTIVE
        created = subscription.model_copy(
            update={
                "amount": quantize_money(subscription.amount),
                "status": status,
                "is_active": _sync_active(status),
                "payments_made": int(subscription.payments_made or 0),
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
        status = subscription.status or existing.status
        updated = subscription.model_copy(
            update={
                "amount": quantize_money(subscription.amount),
                "status": status,
                "is_active": _sync_active(status),
                "updated_at": _utc_now(),
                "created_at": existing.created_at,
                "payments_made": subscription.payments_made,
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
        status: Optional[SubscriptionStatus] = None,
    ) -> list[Subscription]:
        """Return subscriptions with optional filters."""
        return await self._subscriptions.list(
            active_only=active_only,
            account_id=account_id,
            status=status,
        )


class PauseSubscriptionUseCase:
    """Pause an active subscription (billing stops, next date kept)."""

    def __init__(self, subscriptions: SubscriptionRepository) -> None:
        self._subscriptions = subscriptions

    async def execute(self, subscription_id: str) -> Subscription:
        sub = await self._subscriptions.get_by_id(subscription_id)
        if sub is None:
            raise ValueError(f"Subscription not found: {subscription_id}")
        if sub.status != SubscriptionStatus.ACTIVE:
            return sub
        updated = sub.model_copy(
            update={
                "status": SubscriptionStatus.PAUSED,
                "is_active": False,
                "updated_at": _utc_now(),
            }
        )
        return await self._subscriptions.update(updated)


class ResumeSubscriptionUseCase:
    """Resume a paused subscription and skip missed periods without charging."""

    def __init__(self, subscriptions: SubscriptionRepository) -> None:
        self._subscriptions = subscriptions

    async def execute(
        self,
        subscription_id: str,
        *,
        as_of: Optional[datetime] = None,
    ) -> Subscription:
        sub = await self._subscriptions.get_by_id(subscription_id)
        if sub is None:
            raise ValueError(f"Subscription not found: {subscription_id}")
        if sub.status not in (SubscriptionStatus.PAUSED, SubscriptionStatus.CANCELLED):
            return sub

        moment = _as_utc(as_of or _utc_now())
        next_date = _as_utc(sub.next_billing_date)
        # Advance past missed periods so catch-up does not charge pause gaps.
        safety = 0
        while next_date <= moment and safety < 500:
            next_date = advance_billing_date(
                next_date,
                sub.periodicity,
                custom_interval_days=sub.custom_interval_days,
            )
            safety += 1

        updated = sub.model_copy(
            update={
                "status": SubscriptionStatus.ACTIVE,
                "is_active": True,
                "next_billing_date": next_date,
                "updated_at": _utc_now(),
            }
        )
        return await self._subscriptions.update(updated)


class ChargeSubscriptionNowUseCase:
    """Force a single charge for a subscription (optional balance check)."""

    def __init__(
        self,
        subscriptions: SubscriptionRepository,
        transactions: TransactionRepository,
        accounts: AccountRepository,
        settings: Optional["SettingsRepository"] = None,
    ) -> None:
        self._subscriptions = subscriptions
        self._transactions = transactions
        self._accounts = accounts
        self._settings = settings

    async def execute(
        self,
        subscription_id: str,
        *,
        check_balance: Optional[bool] = None,
        language: str = "ru",
        notifier: Any = None,
    ) -> Transaction:
        sub = await self._subscriptions.get_by_id(subscription_id)
        if sub is None:
            raise ValueError(f"Subscription not found: {subscription_id}")
        if sub.status not in (SubscriptionStatus.ACTIVE, SubscriptionStatus.PAUSED):
            raise ValueError(f"Subscription cannot be charged: {sub.status}")

        account = await self._accounts.get_by_id(sub.account_id)
        if account is None:
            raise ValueError(f"Account not found: {sub.account_id}")

        if check_balance is None and self._settings is not None:
            settings = await self._settings.get()
            check_balance = bool(
                getattr(settings, "check_balance_before_subscription", True)
            )
        if check_balance is None:
            check_balance = True

        amount = quantize_money(sub.amount)
        if check_balance and account.balance < amount:
            raise ValueError("insufficient_funds")

        now = _utc_now()
        currency = sub.currency or account.currency
        tx = Transaction(
            account_id=sub.account_id,
            amount=amount,
            category=sub.category,
            tags=["subscription"],
            date=now,
            comment=sub.comment or f"Subscription: {sub.name}",
            type=TransactionType.EXPENSE,
            currency=currency,
            subscription_id=sub.id,
            created_at=now,
            updated_at=now,
        )
        saved = await self._transactions.create(tx)
        account.balance = quantize_money(account.balance - amount)
        await self._accounts.update(account)

        next_date = advance_billing_date(
            _as_utc(sub.next_billing_date),
            sub.periodicity,
            custom_interval_days=sub.custom_interval_days,
        )
        # If we charged manually while paused, keep paused but advance billing.
        updated = sub.model_copy(
            update={
                "last_charged_at": now,
                "next_billing_date": next_date,
                "payments_made": int(sub.payments_made or 0) + 1,
                "updated_at": now,
            }
        )
        await self._subscriptions.update(updated)
        return saved


class DeleteSubscriptionChargeUseCase:
    """Delete a subscription charge transaction (no next_billing_date recalculation)."""

    def __init__(
        self,
        transactions: TransactionRepository,
        subscriptions: SubscriptionRepository,
        delete_transaction: "DeleteTransactionUseCase",
    ) -> None:
        self._transactions = transactions
        self._subscriptions = subscriptions
        self._delete_transaction = delete_transaction

    async def execute(self, transaction_id: str, *, subscription_id: str) -> bool:
        tx = await self._transactions.get_by_id(transaction_id)
        if tx is None:
            return False
        if tx.subscription_id != subscription_id:
            raise ValueError("Transaction is not linked to this subscription")

        deleted = await self._delete_transaction.execute(transaction_id)
        if not deleted:
            return False

        sub = await self._subscriptions.get_by_id(subscription_id)
        if sub is None:
            return True

        remaining = await self._transactions.list(
            subscription_id=subscription_id,
            limit=1,
            offset=0,
        )
        last_charged = remaining[0].date if remaining else None
        payments = max(0, int(sub.payments_made or 0) - 1)
        updated = sub.model_copy(
            update={
                "last_charged_at": last_charged,
                "payments_made": payments,
                "updated_at": _utc_now(),
            }
        )
        await self._subscriptions.update(updated)
        return True


class ProcessDueSubscriptionsUseCase:
    """Charge due subscriptions as expense transactions and advance billing dates."""

    def __init__(
        self,
        subscriptions: SubscriptionRepository,
        transactions: TransactionRepository,
        accounts: AccountRepository,
        settings: Optional["SettingsRepository"] = None,
    ) -> None:
        self._subscriptions = subscriptions
        self._transactions = transactions
        self._accounts = accounts
        self._settings = settings

    async def execute(
        self,
        *,
        as_of: Optional[datetime] = None,
        language: str = "ru",
        notifier: Any = None,
    ) -> list[Transaction]:
        """Process all active subscriptions due on/before ``as_of`` (UTC now by default).

        For each due billing period:
        - expire when ``end_date`` / ``max_payments`` is reached
        - optionally skip when account balance is insufficient
        - otherwise create an expense, debit the account, and advance the date
        """
        as_of = _as_utc(as_of or _utc_now())
        check_balance = True
        if self._settings is not None:
            settings = await self._settings.get()
            check_balance = bool(
                getattr(settings, "check_balance_before_subscription", True)
            )

        due = await self._subscriptions.list_due(as_of)
        created_txs: list[Transaction] = []

        # Prefetch accounts once to avoid N+1 lookups.
        account_ids = {sub.account_id for sub in due}
        accounts_by_id: dict[str, Any] = {}
        if account_ids:
            for account in await self._accounts.list(active_only=False):
                if account.id in account_ids:
                    accounts_by_id[account.id] = account

        for sub in due:
            if sub.status != SubscriptionStatus.ACTIVE or not sub.is_active:
                continue
            if not bool(getattr(sub, "auto_charge", True)):
                continue

            account = accounts_by_id.get(sub.account_id)
            if account is None:
                continue

            amount = quantize_money(sub.amount)
            currency = sub.currency or account.currency
            next_date = _as_utc(sub.next_billing_date)
            payments_made = int(sub.payments_made or 0)
            charged_any = False
            expired = False

            while next_date <= as_of:
                billing_day = next_date.date()
                if sub.end_date is not None and billing_day > sub.end_date:
                    expired = True
                    break
                if sub.max_payments is not None and payments_made >= sub.max_payments:
                    expired = True
                    break

                if check_balance and account.balance < amount:
                    sub = sub.model_copy(
                        update={
                            "last_skip_date": billing_day,
                            "updated_at": _utc_now(),
                        }
                    )
                    await self._subscriptions.update(sub)
                    self._notify_insufficient(
                        notifier,
                        sub,
                        account_name=getattr(account, "name", ""),
                        language=language,
                    )
                    # Do not advance billing — retry next run for this period.
                    break

                now = _utc_now()
                tx = Transaction(
                    account_id=sub.account_id,
                    amount=amount,
                    category=sub.category,
                    tags=["subscription"],
                    date=next_date,
                    comment=sub.comment or f"Subscription: {sub.name}",
                    type=TransactionType.EXPENSE,
                    currency=currency,
                    subscription_id=sub.id,
                    created_at=now,
                    updated_at=now,
                )
                saved_tx = await self._transactions.create(tx)
                account.balance = quantize_money(account.balance - amount)
                await self._accounts.update(account)
                accounts_by_id[account.id] = account
                created_txs.append(saved_tx)
                charged_any = True
                payments_made += 1
                sub.last_charged_at = now
                next_date = advance_billing_date(
                    next_date,
                    sub.periodicity,
                    custom_interval_days=sub.custom_interval_days,
                )

            if expired:
                sub = sub.model_copy(
                    update={
                        "status": SubscriptionStatus.EXPIRED,
                        "is_active": False,
                        "next_billing_date": next_date,
                        "payments_made": payments_made,
                        "updated_at": _utc_now(),
                    }
                )
                await self._subscriptions.update(sub)
                self._notify_expired(notifier, sub, language=language)
                continue

            if charged_any:
                sub = sub.model_copy(
                    update={
                        "next_billing_date": next_date,
                        "payments_made": payments_made,
                        "last_charged_at": sub.last_charged_at,
                        "updated_at": _utc_now(),
                    }
                )
                await self._subscriptions.update(sub)

        return created_txs

    @staticmethod
    def _notify_insufficient(
        notifier: Any,
        sub: Subscription,
        *,
        account_name: str,
        language: str,
    ) -> None:
        if notifier is None:
            return
        try:
            from lib.infrastructure.services.localization import t
            from lib.infrastructure.services.notification_service import NotificationKind

            if notifier._has_related(sub.id, NotificationKind.SUBSCRIPTION_SKIPPED):
                return
            notifier.push(
                title=t("notify.subscription_skipped", language),
                body=t(
                    "notify.subscription_skipped_body",
                    language,
                ).format(
                    name=sub.name,
                    amount=sub.amount,
                    currency=sub.currency,
                    account=account_name or sub.account_id,
                ),
                kind=NotificationKind.SUBSCRIPTION_SKIPPED,
                related_id=sub.id,
            )
        except Exception:  # noqa: BLE001
            return

    @staticmethod
    def _notify_expired(notifier: Any, sub: Subscription, *, language: str) -> None:
        if notifier is None:
            return
        try:
            from lib.infrastructure.services.localization import t
            from lib.infrastructure.services.notification_service import NotificationKind

            if notifier._has_related(sub.id, NotificationKind.SUBSCRIPTION_EXPIRED):
                return
            notifier.push(
                title=t("notify.subscription_expired", language),
                body=t("notify.subscription_expired_body", language).format(
                    name=sub.name
                ),
                kind=NotificationKind.SUBSCRIPTION_EXPIRED,
                related_id=sub.id,
            )
        except Exception:  # noqa: BLE001
            return


class SubscriptionAnalytics(BaseModel):
    """Aggregated subscription metrics for analytics screens."""

    total_spent: Decimal = Decimal("0")
    monthly_trend: list[dict[str, object]] = Field(default_factory=list)
    top_subscriptions: list[dict[str, object]] = Field(default_factory=list)
    total_active: int = 0
    total_monthly_cost: Decimal = Decimal("0")
    currency: str = "RUB"


class GetSubscriptionAnalyticsUseCase:
    """Compute spend / trend / top / monthly cost for subscriptions."""

    def __init__(
        self,
        subscriptions: SubscriptionRepository,
        transactions: TransactionRepository,
        currencies: "CurrencyRepository",
    ) -> None:
        self._subscriptions = subscriptions
        self._transactions = transactions
        self._currencies = currencies

    async def execute(
        self,
        *,
        base_currency: str,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> SubscriptionAnalytics:
        rates = await self._currencies.list_rates()
        book = RateBook(rates)
        base = (base_currency or "RUB").upper()

        subs = await self._subscriptions.list(active_only=False)
        active = [s for s in subs if s.status == SubscriptionStatus.ACTIVE]
        monthly_cost = Decimal("0")
        for sub in active:
            monthly = monthly_equivalent(
                sub.amount,
                sub.periodicity,
                custom_interval_days=sub.custom_interval_days,
            )
            converted = book.convert(monthly, sub.currency, base)
            if converted is None and sub.currency.upper() == base:
                converted = monthly
            if converted is not None:
                monthly_cost += converted

        # Prefer FK-linked charges; fall back to legacy tagged expenses.
        charge_txs = await self._transactions.list(
            date_from=date_from,
            date_to=date_to,
            has_subscription=True,
        )
        if not charge_txs:
            charge_txs = await self._transactions.list(
                date_from=date_from,
                date_to=date_to,
                tags=["subscription"],
            )

        total_spent = Decimal("0")
        per_sub: dict[str, Decimal] = {}
        trend_map: dict[str, Decimal] = {}

        for tx in charge_txs:
            if tx.type != TransactionType.EXPENSE:
                continue
            converted = book.convert(tx.amount, tx.currency, base)
            if converted is None and tx.currency.upper() == base:
                converted = tx.amount
            if converted is None:
                continue
            total_spent += converted
            key = tx.subscription_id or tx.comment or tx.id
            per_sub[key] = per_sub.get(key, Decimal("0")) + converted
            month_key = _as_utc(tx.date).strftime("%Y-%m")
            trend_map[month_key] = trend_map.get(month_key, Decimal("0")) + converted

        name_by_id = {s.id: s.name for s in subs}
        top = sorted(per_sub.items(), key=lambda item: item[1], reverse=True)[:5]
        top_subscriptions = [
            {
                "id": sid,
                "name": name_by_id.get(sid, sid),
                "amount": quantize_money(amount),
            }
            for sid, amount in top
        ]

        # Build last-12-months trend (or span of filtered period).
        end = _as_utc(date_to or _utc_now())
        months: list[dict[str, object]] = []
        cursor = date(end.year, end.month, 1)
        for _ in range(12):
            key = f"{cursor.year:04d}-{cursor.month:02d}"
            months.append(
                {
                    "month": key,
                    "sum": quantize_money(trend_map.get(key, Decimal("0"))),
                }
            )
            if cursor.month == 1:
                cursor = date(cursor.year - 1, 12, 1)
            else:
                cursor = date(cursor.year, cursor.month - 1, 1)
        months.reverse()

        return SubscriptionAnalytics(
            total_spent=quantize_money(total_spent),
            monthly_trend=months,
            top_subscriptions=top_subscriptions,
            total_active=len(active),
            total_monthly_cost=quantize_money(monthly_cost),
            currency=base,
        )
