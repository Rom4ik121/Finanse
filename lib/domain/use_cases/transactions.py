"""Transaction-related use cases."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Optional, Sequence

from pydantic import BaseModel, Field

from lib.domain.entities.debt import DebtStatus, resolve_debt_status
from lib.domain.entities.goal import GoalStatus
from lib.domain.entities.money import quantize_money
from lib.domain.entities.transaction import Transaction, TransactionType
from lib.domain.repositories.account_repository import AccountRepository
from lib.domain.repositories.budget_repository import BudgetRepository
from lib.domain.repositories.debt_repository import DebtRepository
from lib.domain.repositories.goal_repository import GoalRepository
from lib.domain.repositories.settings_repository import SettingsRepository
from lib.domain.repositories.transaction_repository import TransactionRepository
from lib.domain.use_cases.debts import debt_credit_amount
from lib.domain.use_cases.goals import goal_credit_amount


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


def _mark_goal_progress(goal: object, current: Decimal) -> None:
    """Sync ``current_amount`` / status / completed flag on a goal entity."""
    from lib.domain.entities.goal import Goal

    if not isinstance(goal, Goal):
        return
    goal.current_amount = quantize_money(current)
    if goal.status == GoalStatus.ARCHIVED:
        goal.is_completed = goal.current_amount >= goal.target_amount
        return
    if goal.current_amount >= goal.target_amount:
        goal.status = GoalStatus.COMPLETED
        goal.is_completed = True
    else:
        goal.status = GoalStatus.ACTIVE
        goal.is_completed = False


def _mark_debt_remaining(debt: object, remaining: Decimal) -> None:
    """Sync remaining amount and status on a debt entity."""
    from lib.domain.entities.debt import Debt

    if not isinstance(debt, Debt):
        return
    remaining = quantize_money(max(Decimal("0"), remaining))
    if remaining > debt.amount:
        remaining = quantize_money(debt.amount)
    debt.remaining_amount = remaining
    if debt.status != DebtStatus.ARCHIVED:
        debt.status = resolve_debt_status(
            remaining_amount=remaining,
            due_date=debt.due_date,
            current=debt.status,
        )
    debt.updated_at = _utc_now()


def _is_debt_payment(transaction: Transaction) -> bool:
    return bool(transaction.debt_id)


async def _sync_budget_expense(
    budgets: Optional[BudgetRepository],
    transaction: Transaction,
    *,
    sign: int,
    settings_repo: Optional[SettingsRepository] = None,
    notifications: object = None,
) -> None:
    """Apply or reverse an expense against the matching monthly budget."""
    if budgets is None or transaction.type != TransactionType.EXPENSE:
        return
    if transaction.transfer_id:
        return
    from lib.domain.use_cases.budgets import apply_expense_delta

    settings = None
    language = "ru"
    currency = "RUB"
    if settings_repo is not None:
        try:
            settings = await settings_repo.get()
            language = settings.language
            currency = settings.default_currency
        except Exception:  # noqa: BLE001
            settings = None
    await apply_expense_delta(
        budgets,
        category=transaction.category,
        when=transaction.date,
        amount=transaction.amount,
        sign=sign,
        settings=settings,
        notifications=notifications,  # type: ignore[arg-type]
        currency=currency,
        language=language,
    )


class AddTransactionUseCase:
    """Create a transaction and adjust account (and optional goal / debt) balances."""

    def __init__(
        self,
        transactions: TransactionRepository,
        accounts: AccountRepository,
        goals: GoalRepository,
        debts: Optional[DebtRepository] = None,
        budgets: Optional[BudgetRepository] = None,
        settings: Optional[SettingsRepository] = None,
        notifications: object = None,
    ) -> None:
        self._transactions = transactions
        self._accounts = accounts
        self._goals = goals
        self._debts = debts
        self._budgets = budgets
        self._settings = settings
        self._notifications = notifications

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
        await _sync_budget_expense(
            self._budgets,
            created,
            sign=1,
            settings_repo=self._settings,
            notifications=self._notifications,
        )
        return created

    async def _apply_goal_contribution(self, transaction: Transaction) -> None:
        if not _is_goal_contribution(transaction):
            return
        goal = await self._goals.get_by_id(transaction.goal_id or "")
        if goal is None:
            return
        credit = goal_credit_amount(transaction)
        _mark_goal_progress(goal, goal.current_amount + credit)
        await self._goals.update(goal)

    async def _apply_debt_payment(self, transaction: Transaction) -> None:
        if self._debts is None or not _is_debt_payment(transaction):
            return
        debt = await self._debts.get_by_id(transaction.debt_id or "")
        if debt is None:
            return
        credit = debt_credit_amount(transaction)
        _mark_debt_remaining(debt, debt.remaining_amount - credit)
        await self._debts.update(debt)


class UpdateTransactionUseCase:
    """Update a transaction and reconcile account / goal / debt balances."""

    def __init__(
        self,
        transactions: TransactionRepository,
        accounts: AccountRepository,
        goals: GoalRepository,
        debts: Optional[DebtRepository] = None,
        budgets: Optional[BudgetRepository] = None,
        settings: Optional[SettingsRepository] = None,
        notifications: object = None,
    ) -> None:
        self._transactions = transactions
        self._accounts = accounts
        self._goals = goals
        self._debts = debts
        self._budgets = budgets
        self._settings = settings
        self._notifications = notifications

    async def execute(self, transaction: Transaction) -> Transaction:
        """Replace an existing transaction and fix derived balances."""
        existing = await self._transactions.get_by_id(transaction.id)
        if existing is None:
            raise ValueError(f"Transaction not found: {transaction.id}")
        if existing.transfer_id:
            if (
                transaction.amount != existing.amount
                or transaction.account_id != existing.account_id
                or transaction.type != existing.type
                or transaction.currency != existing.currency
                or transaction.category != existing.category
            ):
                raise ValueError("Transfer legs cannot be edited independently")
            transaction = transaction.model_copy(
                update={
                    "transfer_id": existing.transfer_id,
                    "transfer_peer_account_id": existing.transfer_peer_account_id,
                    "goal_id": None,
                    "debt_id": None,
                    "subscription_id": None,
                }
            )

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
        await _sync_budget_expense(
            self._budgets,
            existing,
            sign=-1,
            settings_repo=self._settings,
            notifications=self._notifications,
        )
        await _sync_budget_expense(
            self._budgets,
            saved,
            sign=1,
            settings_repo=self._settings,
            notifications=self._notifications,
        )
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
        credit = goal_credit_amount(transaction)
        _mark_goal_progress(goal, goal.current_amount + credit)
        await self._goals.update(goal)

    async def _reverse_goal_contribution(self, transaction: Transaction) -> None:
        if not _is_goal_contribution(transaction):
            return
        goal = await self._goals.get_by_id(transaction.goal_id or "")
        if goal is None:
            return
        credit = goal_credit_amount(transaction)
        _mark_goal_progress(
            goal,
            max(Decimal("0"), goal.current_amount - credit),
        )
        await self._goals.update(goal)

    async def _apply_debt_payment(self, transaction: Transaction) -> None:
        if self._debts is None or not _is_debt_payment(transaction):
            return
        debt = await self._debts.get_by_id(transaction.debt_id or "")
        if debt is None:
            return
        credit = debt_credit_amount(transaction)
        _mark_debt_remaining(debt, debt.remaining_amount - credit)
        await self._debts.update(debt)

    async def _reverse_debt_payment(self, transaction: Transaction) -> None:
        if self._debts is None or not _is_debt_payment(transaction):
            return
        debt = await self._debts.get_by_id(transaction.debt_id or "")
        if debt is None:
            return
        credit = debt_credit_amount(transaction)
        _mark_debt_remaining(debt, debt.remaining_amount + credit)
        await self._debts.update(debt)


class DeleteTransactionUseCase:
    """Delete a transaction and reverse its balance effects."""

    def __init__(
        self,
        transactions: TransactionRepository,
        accounts: AccountRepository,
        goals: GoalRepository,
        debts: Optional[DebtRepository] = None,
        budgets: Optional[BudgetRepository] = None,
        settings: Optional[SettingsRepository] = None,
        notifications: object = None,
    ) -> None:
        self._transactions = transactions
        self._accounts = accounts
        self._goals = goals
        self._debts = debts
        self._budgets = budgets
        self._settings = settings
        self._notifications = notifications

    async def execute(self, transaction_id: str) -> bool:
        """Remove a transaction and undo account / goal / debt side effects."""
        existing = await self._transactions.get_by_id(transaction_id)
        if existing is None:
            return False
        peer_ids: list[str] = []
        if existing.transfer_id:
            peers = await self._transactions.list(transfer_id=existing.transfer_id)
            peer_ids = [p.id for p in peers if p.id != existing.id]
        ok = await self._delete_one(existing)
        for peer_id in peer_ids:
            peer = await self._transactions.get_by_id(peer_id)
            if peer is not None:
                await self._delete_one(peer)
        return ok

    async def _delete_one(self, existing: Transaction) -> bool:
        """Reverse one row without looking up its transfer peer."""
        account = await self._accounts.get_by_id(existing.account_id)
        if account is not None:
            account.balance = quantize_money(
                account.balance - _balance_delta(existing.type, existing.amount)
            )
            await self._accounts.update(account)

        if _is_goal_contribution(existing):
            goal = await self._goals.get_by_id(existing.goal_id or "")
            if goal is not None:
                credit = goal_credit_amount(existing)
                _mark_goal_progress(
                    goal,
                    max(Decimal("0"), goal.current_amount - credit),
                )
                await self._goals.update(goal)

        if self._debts is not None and _is_debt_payment(existing):
            debt = await self._debts.get_by_id(existing.debt_id or "")
            if debt is not None:
                credit = debt_credit_amount(existing)
                _mark_debt_remaining(debt, debt.remaining_amount + credit)
                await self._debts.update(debt)

        await _sync_budget_expense(
            self._budgets,
            existing,
            sign=-1,
            settings_repo=self._settings,
            notifications=self._notifications,
        )
        return await self._transactions.delete(existing.id)


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
        debt_id: Optional[str] = None,
        subscription_id: Optional[str] = None,
        has_subscription: Optional[bool] = None,
        transfer_id: Optional[str] = None,
        has_transfer: Optional[bool] = None,
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
            debt_id=debt_id,
            subscription_id=subscription_id,
            has_subscription=has_subscription,
            transfer_id=transfer_id,
            has_transfer=has_transfer,
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
            if tx.transfer_id:
                continue
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


TRANSFER_CATEGORY = "Перевод"


class TransferAccountsUseCase:
    """Move money between two accounts as a linked expense + income pair."""

    def __init__(
        self,
        add_transaction: AddTransactionUseCase,
        delete_transaction: DeleteTransactionUseCase,
        accounts: AccountRepository,
        currencies: object,
        find_or_create_category: object = None,
    ) -> None:
        self._add = add_transaction
        self._delete = delete_transaction
        self._accounts = accounts
        self._currencies = currencies
        self._find_or_create_category = find_or_create_category

    async def execute(
        self,
        *,
        from_account_id: str,
        to_account_id: str,
        amount: Decimal,
        comment: str = "",
        date: Optional[datetime] = None,
    ) -> tuple[Transaction, Transaction]:
        """Create both transfer legs and return ``(outgoing, incoming)``."""
        from uuid import uuid4

        from lib.domain.entities.category import CategoryKind
        from lib.domain.services.rate_book import RateBook

        if from_account_id == to_account_id:
            raise ValueError("Cannot transfer to the same account")
        amount = quantize_money(amount)
        if amount <= 0:
            raise ValueError("Transfer amount must be positive")

        source = await self._accounts.get_by_id(from_account_id)
        dest = await self._accounts.get_by_id(to_account_id)
        if source is None:
            raise ValueError(f"Account not found: {from_account_id}")
        if dest is None:
            raise ValueError(f"Account not found: {to_account_id}")
        if source.balance < amount:
            raise ValueError("Insufficient funds")

        dest_amount = amount
        if source.currency.upper() != dest.currency.upper():
            rates = await self._currencies.list_rates()
            converted = RateBook(rates).convert(amount, source.currency, dest.currency)
            if converted is None:
                raise ValueError("No exchange rate for this currency pair")
            dest_amount = converted
            if dest_amount <= 0:
                raise ValueError("No exchange rate for this currency pair")

        if self._find_or_create_category is not None:
            await self._find_or_create_category.execute(
                TRANSFER_CATEGORY,
                kind=CategoryKind.BOTH,
                icon="sync_alt",
            )

        when = date or _utc_now()
        extra = (comment or "").strip()
        out_comment = f"→ {dest.name}"
        in_comment = f"← {source.name}"
        if extra:
            out_comment = f"{out_comment} · {extra}"
            in_comment = f"{in_comment} · {extra}"

        transfer_id = str(uuid4())
        outgoing = Transaction(
            account_id=source.id,
            amount=amount,
            category=TRANSFER_CATEGORY,
            date=when,
            comment=out_comment,
            type=TransactionType.EXPENSE,
            currency=source.currency,
            transfer_id=transfer_id,
            transfer_peer_account_id=dest.id,
        )
        incoming = Transaction(
            account_id=dest.id,
            amount=dest_amount,
            category=TRANSFER_CATEGORY,
            date=when,
            comment=in_comment,
            type=TransactionType.INCOME,
            currency=dest.currency,
            transfer_id=transfer_id,
            transfer_peer_account_id=source.id,
        )
        created_out = await self._add.execute(outgoing)
        try:
            created_in = await self._add.execute(incoming)
        except Exception:
            await self._delete.execute(created_out.id)
            raise
        return created_out, created_in
