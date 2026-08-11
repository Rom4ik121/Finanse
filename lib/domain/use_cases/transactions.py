"""Transaction-related use cases."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Optional, Sequence

from pydantic import BaseModel, Field

from lib.domain.entities.debt import DebtStatus
from lib.domain.entities.money import quantize_money
from lib.domain.entities.transaction import Transaction, TransactionType
from lib.domain.repositories.account_repository import AccountRepository
from lib.domain.repositories.debt_repository import DebtRepository
from lib.domain.repositories.goal_repository import GoalRepository
from lib.domain.repositories.transaction_repository import TransactionRepository


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _balance_delta(tx_type: TransactionType, amount: Decimal) -> Decimal:
    """Return signed balance change for an account (income +, expense −)."""
    amount = quantize_money(amount)
    if tx_type == TransactionType.INCOME:
        return amount
    return -amount


def _is_goal_contribution(transaction: Transaction) -> bool:
    return transaction.type == TransactionType.EXPENSE and bool(transaction.goal_id)


def _is_debt_payment(transaction: Transaction) -> bool:
    return bool(transaction.debt_id)


class AddTransactionUseCase:
    """Create a transaction and adjust account (and optional goal / debt) balances."""

    def __init__(
        self,
        transactions: TransactionRepository,
        accounts: AccountRepository,
        goals: GoalRepository,
        debts: Optional[DebtRepository] = None,
    ) -> None:
        self._transactions = transactions
        self._accounts = accounts
        self._goals = goals
        self._debts = debts

    async def execute(self, transaction: Transaction) -> Transaction:
        """Persist ``transaction``, update account balance, sync goal/debt if linked."""
        account = await self._accounts.get_by_id(transaction.account_id)
        if account is None:
            raise ValueError(f"Account not found: {transaction.account_id}")

        now = _utc_now()
        transaction = transaction.model_copy(
            update={
                "amount": quantize_money(transaction.amount),
                "currency": transaction.currency or account.currency,
                "created_at": now,
                "updated_at": now,
            }
        )

        created = await self._transactions.create(transaction)

        account.balance = quantize_money(
            account.balance + _balance_delta(created.type, created.amount)
        )
        await self._accounts.update(account)

        await self._apply_goal_contribution(created)
        await self._apply_debt_payment(created)
        return created

    async def _apply_goal_contribution(self, transaction: Transaction) -> None:
        if not _is_goal_contribution(transaction):
            return
        goal = await self._goals.get_by_id(transaction.goal_id or "")
        if goal is None:
            return
        goal.current_amount = quantize_money(goal.current_amount + transaction.amount)
        if goal.current_amount >= goal.target_amount:
            goal.is_completed = True
        await self._goals.update(goal)

    async def _apply_debt_payment(self, transaction: Transaction) -> None:
        if self._debts is None or not _is_debt_payment(transaction):
            return
        debt = await self._debts.get_by_id(transaction.debt_id or "")
        if debt is None:
            return
        remaining = quantize_money(
            max(Decimal("0"), debt.remaining_amount - transaction.amount)
        )
        debt.remaining_amount = remaining
        debt.status = DebtStatus.PAID if remaining <= 0 else DebtStatus.ACTIVE
        debt.updated_at = _utc_now()
        await self._debts.update(debt)


class UpdateTransactionUseCase:
    """Update a transaction and reconcile account / goal / debt balances."""

    def __init__(
        self,
        transactions: TransactionRepository,
        accounts: AccountRepository,
        goals: GoalRepository,
        debts: Optional[DebtRepository] = None,
    ) -> None:
        self._transactions = transactions
        self._accounts = accounts
        self._goals = goals
        self._debts = debts

    async def execute(self, transaction: Transaction) -> Transaction:
        """Replace an existing transaction and fix derived balances."""
        existing = await self._transactions.get_by_id(transaction.id)
        if existing is None:
            raise ValueError(f"Transaction not found: {transaction.id}")

        await self._apply_account_delta(
            existing.account_id,
            -_balance_delta(existing.type, existing.amount),
        )
        await self._reverse_goal_contribution(existing)
        await self._reverse_debt_payment(existing)

        updated = transaction.model_copy(
            update={
                "amount": quantize_money(transaction.amount),
                "updated_at": _utc_now(),
                "created_at": existing.created_at,
            }
        )
        saved = await self._transactions.update(updated)

        await self._apply_account_delta(
            saved.account_id,
            _balance_delta(saved.type, saved.amount),
        )
        await self._apply_goal_contribution(saved)
        await self._apply_debt_payment(saved)
        return saved

    async def _apply_account_delta(self, account_id: str, delta: Decimal) -> None:
        account = await self._accounts.get_by_id(account_id)
        if account is None:
            raise ValueError(f"Account not found: {account_id}")
        account.balance = quantize_money(account.balance + delta)
        await self._accounts.update(account)

    async def _apply_goal_contribution(self, transaction: Transaction) -> None:
        if not _is_goal_contribution(transaction):
            return
        goal = await self._goals.get_by_id(transaction.goal_id or "")
        if goal is None:
            return
        goal.current_amount = quantize_money(goal.current_amount + transaction.amount)
        if goal.current_amount >= goal.target_amount:
            goal.is_completed = True
        await self._goals.update(goal)

    async def _reverse_goal_contribution(self, transaction: Transaction) -> None:
        if not _is_goal_contribution(transaction):
            return
        goal = await self._goals.get_by_id(transaction.goal_id or "")
        if goal is None:
            return
        goal.current_amount = quantize_money(
            max(Decimal("0"), goal.current_amount - transaction.amount)
        )
        goal.is_completed = goal.current_amount >= goal.target_amount
        await self._goals.update(goal)

    async def _apply_debt_payment(self, transaction: Transaction) -> None:
        if self._debts is None or not _is_debt_payment(transaction):
            return
        debt = await self._debts.get_by_id(transaction.debt_id or "")
        if debt is None:
            return
        remaining = quantize_money(
            max(Decimal("0"), debt.remaining_amount - transaction.amount)
        )
        debt.remaining_amount = remaining
        debt.status = DebtStatus.PAID if remaining <= 0 else DebtStatus.ACTIVE
        debt.updated_at = _utc_now()
        await self._debts.update(debt)

    async def _reverse_debt_payment(self, transaction: Transaction) -> None:
        if self._debts is None or not _is_debt_payment(transaction):
            return
        debt = await self._debts.get_by_id(transaction.debt_id or "")
        if debt is None:
            return
        remaining = quantize_money(debt.remaining_amount + transaction.amount)
        # Cap at original principal.
        if remaining > debt.amount:
            remaining = quantize_money(debt.amount)
        debt.remaining_amount = remaining
        debt.status = DebtStatus.PAID if remaining <= 0 else DebtStatus.ACTIVE
        debt.updated_at = _utc_now()
        await self._debts.update(debt)


class DeleteTransactionUseCase:
    """Delete a transaction and reverse its balance effects."""

    def __init__(
        self,
        transactions: TransactionRepository,
        accounts: AccountRepository,
        goals: GoalRepository,
        debts: Optional[DebtRepository] = None,
    ) -> None:
        self._transactions = transactions
        self._accounts = accounts
        self._goals = goals
        self._debts = debts

    async def execute(self, transaction_id: str) -> bool:
        """Remove a transaction and undo account / goal / debt side effects."""
        existing = await self._transactions.get_by_id(transaction_id)
        if existing is None:
            return False

        account = await self._accounts.get_by_id(existing.account_id)
        if account is not None:
            account.balance = quantize_money(
                account.balance - _balance_delta(existing.type, existing.amount)
            )
            await self._accounts.update(account)

        if _is_goal_contribution(existing):
            goal = await self._goals.get_by_id(existing.goal_id or "")
            if goal is not None:
                goal.current_amount = quantize_money(
                    max(Decimal("0"), goal.current_amount - existing.amount)
                )
                goal.is_completed = goal.current_amount >= goal.target_amount
                await self._goals.update(goal)

        if self._debts is not None and _is_debt_payment(existing):
            debt = await self._debts.get_by_id(existing.debt_id or "")
            if debt is not None:
                remaining = quantize_money(debt.remaining_amount + existing.amount)
                if remaining > debt.amount:
                    remaining = quantize_money(debt.amount)
                debt.remaining_amount = remaining
                debt.status = DebtStatus.PAID if remaining <= 0 else DebtStatus.ACTIVE
                debt.updated_at = _utc_now()
                await self._debts.update(debt)

        return await self._transactions.delete(transaction_id)


class ListTransactionsUseCase:
    """List / filter transactions."""

    def __init__(self, transactions: TransactionRepository) -> None:
        self._transactions = transactions

    async def execute(
        self,
        *,
        account_id: Optional[str] = None,
        category: Optional[str] = None,
        transaction_type: Optional[TransactionType] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        tags: Optional[Sequence[str]] = None,
        goal_id: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> list[Transaction]:
        """Return transactions matching the given filters."""
        return await self._transactions.list(
            account_id=account_id,
            category=category,
            transaction_type=transaction_type,
            date_from=date_from,
            date_to=date_to,
            tags=tags,
            goal_id=goal_id,
            limit=limit,
            offset=offset,
        )


class StatsPeriod(str, Enum):
    """Aggregation bucket for transaction statistics."""

    DAY = "day"
    WEEK = "week"
    MONTH = "month"


class CategorySlice(BaseModel):
    """Pie-chart slice for a category."""

    category: str
    amount: Decimal
    share: Decimal = Field(description="Fraction of total (0–1)")


class TimeSeriesPoint(BaseModel):
    """Single point on a time-series (line) chart."""

    period: str
    income: Decimal
    expense: Decimal
    net: Decimal


class TransactionStats(BaseModel):
    """Aggregated transaction statistics for charts."""

    total_income: Decimal
    total_expense: Decimal
    net: Decimal
    by_period: list[TimeSeriesPoint]
    by_category: list[CategorySlice]


class GetTransactionStatsUseCase:
    """Compute income/expense stats for charts (time series + category pie)."""

    def __init__(self, transactions: TransactionRepository) -> None:
        self._transactions = transactions

    async def execute(
        self,
        *,
        account_id: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        group_by: StatsPeriod = StatsPeriod.MONTH,
    ) -> TransactionStats:
        """Aggregate transactions into period and category summaries."""
        items = await self._transactions.list(
            account_id=account_id,
            date_from=date_from,
            date_to=date_to,
        )

        total_income = Decimal("0.00")
        total_expense = Decimal("0.00")
        period_income: dict[str, Decimal] = defaultdict(lambda: Decimal("0.00"))
        period_expense: dict[str, Decimal] = defaultdict(lambda: Decimal("0.00"))
        category_totals: dict[str, Decimal] = defaultdict(lambda: Decimal("0.00"))

        for tx in items:
            key = self._period_key(tx.date, group_by)
            if tx.type == TransactionType.INCOME:
                total_income += tx.amount
                period_income[key] += tx.amount
            else:
                total_expense += tx.amount
                period_expense[key] += tx.amount
                category_totals[tx.category] += tx.amount

        total_income = quantize_money(total_income)
        total_expense = quantize_money(total_expense)
        keys = sorted(set(period_income) | set(period_expense))
        by_period = [
            TimeSeriesPoint(
                period=key,
                income=quantize_money(period_income[key]),
                expense=quantize_money(period_expense[key]),
                net=quantize_money(period_income[key] - period_expense[key]),
            )
            for key in keys
        ]

        expense_total = total_expense if total_expense > 0 else Decimal("1")
        by_category = [
            CategorySlice(
                category=cat,
                amount=quantize_money(amount),
                share=quantize_money(amount / expense_total),
            )
            for cat, amount in sorted(
                category_totals.items(), key=lambda kv: kv[1], reverse=True
            )
        ]

        return TransactionStats(
            total_income=total_income,
            total_expense=total_expense,
            net=quantize_money(total_income - total_expense),
            by_period=by_period,
            by_category=by_category,
        )

    @staticmethod
    def _period_key(dt: datetime, group_by: StatsPeriod) -> str:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        if group_by == StatsPeriod.DAY:
            return dt.strftime("%Y-%m-%d")
        if group_by == StatsPeriod.WEEK:
            iso = dt.isocalendar()
            return f"{iso.year}-W{iso.week:02d}"
        return dt.strftime("%Y-%m")
