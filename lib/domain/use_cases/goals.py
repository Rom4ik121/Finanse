"""Goal-related use cases."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Optional
from uuid import uuid4

from pydantic import BaseModel

from lib.core.config import SAVINGS_CATEGORIES
from lib.domain.entities.goal import Goal, GoalStatus
from lib.domain.entities.money import quantize_money
from lib.domain.entities.transaction import Transaction, TransactionType
from lib.domain.repositories.account_repository import AccountRepository
from lib.domain.repositories.currency_repository import CurrencyRepository
from lib.domain.repositories.goal_repository import GoalRepository
from lib.domain.repositories.transaction_repository import TransactionRepository
from lib.domain.services.rate_book import RateBook

if TYPE_CHECKING:
    from lib.domain.use_cases.transactions import (
        AddTransactionUseCase,
        DeleteTransactionUseCase,
    )


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _savings_category(goal: Goal) -> str:
    link = (goal.category_link or "").strip()
    if link in SAVINGS_CATEGORIES:
        return link
    return "Накопление"


def _months_between(start: datetime, end: datetime) -> float:
    """Approximate fractional months between two UTC datetimes."""
    if end <= start:
        return 0.0
    days = (end - start).total_seconds() / 86400.0
    return max(days / 30.4375, 0.0)


def _add_months(dt: datetime, months: float) -> datetime:
    """Add fractional months to ``dt`` (day-based approximation)."""
    return dt + timedelta(days=months * 30.4375)


def goal_credit_amount(transaction: Transaction) -> Decimal:
    """Amount credited to the goal currency for a contribution transaction."""
    if transaction.goal_credit_amount is not None:
        return quantize_money(transaction.goal_credit_amount)
    return quantize_money(transaction.amount)


class GoalProjection(BaseModel):
    """Projection / on-track metrics for a savings goal."""

    goal_id: str
    required_monthly_contribution: Optional[Decimal] = None
    projected_completion_date: Optional[datetime] = None
    is_on_track: Optional[bool] = None
    average_monthly_contribution: Decimal = Decimal("0.00")
    remaining_amount: Decimal = Decimal("0.00")
    lookback_months: int = 6


class CreateGoalUseCase:
    """Create a savings goal (progress starts at zero — fund via account)."""

    def __init__(self, goals: GoalRepository) -> None:
        self._goals = goals

    async def execute(self, goal: Goal) -> Goal:
        """Persist a new goal; ``current_amount`` always starts at 0."""
        created = goal.model_copy(
            update={
                "target_amount": quantize_money(goal.target_amount),
                "current_amount": Decimal("0.00"),
                "created_at": goal.created_at or _utc_now(),
                "status": GoalStatus.ACTIVE,
                "is_completed": False,
                "cached_projection": None,
            }
        )
        return await self._goals.create(created)


class UpdateGoalUseCase:
    """Update goal metadata (progress only changes via contributions)."""

    def __init__(self, goals: GoalRepository) -> None:
        self._goals = goals

    async def execute(self, goal: Goal) -> Goal:
        """Update name/target/deadline/priority/currency; keep ledger progress."""
        existing = await self._goals.get_by_id(goal.id)
        if existing is None:
            raise ValueError(f"Goal not found: {goal.id}")

        target = quantize_money(goal.target_amount)
        current = quantize_money(existing.current_amount)
        status = goal.status if isinstance(goal.status, GoalStatus) else GoalStatus(goal.status)
        if status == GoalStatus.ARCHIVED:
            pass
        elif current >= target:
            status = GoalStatus.COMPLETED
        elif status == GoalStatus.COMPLETED and current < target:
            status = GoalStatus.ACTIVE

        updated = goal.model_copy(
            update={
                "current_amount": current,
                "target_amount": target,
                "status": status,
                "is_completed": status == GoalStatus.COMPLETED
                or (status == GoalStatus.ARCHIVED and current >= target),
                "cached_projection": existing.cached_projection,
            }
        )
        return await self._goals.update(updated)


class DeleteGoalUseCase:
    """Delete a goal."""

    def __init__(self, goals: GoalRepository) -> None:
        self._goals = goals

    async def execute(self, goal_id: str) -> bool:
        """Remove a goal by id."""
        return await self._goals.delete(goal_id)


class ListGoalsUseCase:
    """List savings goals."""

    def __init__(self, goals: GoalRepository) -> None:
        self._goals = goals

    async def execute(
        self,
        *,
        status: GoalStatus | str | None = None,
        include_completed: bool = True,
        currency: str | None = None,
        min_priority: int | None = None,
        sort_by: str = "priority",
    ) -> list[Goal]:
        """Return goals with optional filters and sorting."""
        return await self._goals.list(
            status=status,
            include_completed=include_completed,
            currency=currency,
            min_priority=min_priority,
            sort_by=sort_by,
        )


class ArchiveGoalUseCase:
    """Move a goal to archived status."""

    def __init__(self, goals: GoalRepository) -> None:
        self._goals = goals

    async def execute(self, goal_id: str) -> Goal:
        goal = await self._goals.get_by_id(goal_id)
        if goal is None:
            raise ValueError(f"Goal not found: {goal_id}")
        if goal.status == GoalStatus.ARCHIVED:
            return goal
        updated = goal.model_copy(update={"status": GoalStatus.ARCHIVED})
        return await self._goals.update(updated)


class DuplicateGoalUseCase:
    """Create a similar goal with zero progress."""

    def __init__(self, goals: GoalRepository) -> None:
        self._goals = goals

    async def execute(self, goal_id: str, *, name_suffix: str = " (копия)") -> Goal:
        source = await self._goals.get_by_id(goal_id)
        if source is None:
            raise ValueError(f"Goal not found: {goal_id}")
        copy = source.model_copy(
            update={
                "id": str(uuid4()),
                "name": f"{source.name}{name_suffix}",
                "current_amount": Decimal("0.00"),
                "status": GoalStatus.ACTIVE,
                "is_completed": False,
                "cached_projection": None,
                "created_at": _utc_now(),
            }
        )
        return await self._goals.create(copy)


class ContributeToGoalUseCase:
    """Move money from an account into a goal (creates an expense transaction)."""

    def __init__(
        self,
        goals: GoalRepository,
        accounts: AccountRepository,
        add_transaction: "AddTransactionUseCase",
        currencies: CurrencyRepository,
        transactions: TransactionRepository | None = None,
    ) -> None:
        self._goals = goals
        self._accounts = accounts
        self._add_transaction = add_transaction
        self._currencies = currencies
        self._transactions = transactions

    async def execute(
        self,
        goal_id: str,
        amount: Decimal,
        *,
        account_id: str,
    ) -> Goal:
        """Debit ``account_id`` and increase the goal's ``current_amount``.

        ``amount`` is in the account currency. It is converted into the goal
        currency via :class:`RateBook` and stored as ``goal_credit_amount``.
        """
        amount = quantize_money(amount)
        if amount <= 0:
            raise ValueError("Contribution amount must be positive")
        if not (account_id or "").strip():
            raise ValueError("Account is required to fund a goal")

        goal = await self._goals.get_by_id(goal_id)
        if goal is None:
            raise ValueError(f"Goal not found: {goal_id}")
        if goal.status != GoalStatus.ACTIVE:
            raise ValueError("Goal is already completed")

        account = await self._accounts.get_by_id(account_id)
        if account is None:
            raise ValueError(f"Account not found: {account_id}")

        rates = await self._currencies.list_rates()
        book = RateBook(rates)
        credit = book.convert(amount, account.currency, goal.currency)
        if credit is None:
            raise ValueError(
                f"No exchange rate for {account.currency}/{goal.currency}"
            )
        credit = quantize_money(credit)
        if credit <= 0:
            raise ValueError("Converted contribution amount must be positive")

        await self._add_transaction.execute(
            Transaction(
                account_id=account.id,
                amount=amount,
                category=_savings_category(goal),
                date=_utc_now(),
                comment=goal.name,
                type=TransactionType.EXPENSE,
                currency=account.currency,
                goal_id=goal.id,
                goal_credit_amount=credit,
            )
        )
        updated = await self._goals.get_by_id(goal_id)
        if updated is None:
            raise ValueError(f"Goal not found after contribution: {goal_id}")

        if self._transactions is not None:
            try:
                await GetGoalProjectionUseCase(
                    self._goals, self._transactions
                ).execute(goal_id)
                refreshed = await self._goals.get_by_id(goal_id)
                if refreshed is not None:
                    return refreshed
            except Exception:  # noqa: BLE001
                pass
        return updated


class GetGoalProjectionUseCase:
    """Compute savings pace, required monthly amount, and on-track status."""

    def __init__(
        self,
        goals: GoalRepository,
        transactions: TransactionRepository,
        *,
        lookback_months: int = 6,
    ) -> None:
        self._goals = goals
        self._transactions = transactions
        self._lookback_months = max(1, int(lookback_months))

    async def execute(self, goal_id: str) -> GoalProjection:
        goal = await self._goals.get_by_id(goal_id)
        if goal is None:
            raise ValueError(f"Goal not found: {goal_id}")

        now = _utc_now()
        remaining = goal.remaining_amount
        projection = GoalProjection(
            goal_id=goal.id,
            remaining_amount=remaining,
            lookback_months=self._lookback_months,
        )

        if remaining <= 0:
            projection.required_monthly_contribution = Decimal("0.00")
            projection.projected_completion_date = now
            projection.is_on_track = True
            await self._cache(goal, projection)
            return projection

        # Required monthly to hit deadline.
        if goal.deadline is not None:
            months_left = _months_between(now, goal.deadline)
            if months_left <= 0:
                projection.required_monthly_contribution = remaining
                projection.is_on_track = False
            else:
                projection.required_monthly_contribution = quantize_money(
                    remaining / Decimal(str(months_left))
                )

        # Average contribution pace from recent history.
        lookback_start = now - timedelta(days=int(self._lookback_months * 30.4375))
        txs = await self._transactions.list(goal_id=goal.id, date_from=lookback_start)
        total_credited = sum(
            (goal_credit_amount(tx) for tx in txs if tx.type == TransactionType.EXPENSE),
            Decimal("0"),
        )
        # Use full lookback window so sparse history doesn't overstate pace.
        avg = quantize_money(
            total_credited / Decimal(str(self._lookback_months))
            if self._lookback_months
            else Decimal("0")
        )
        projection.average_monthly_contribution = avg

        if avg > 0:
            months_needed = float(remaining / avg)
            projection.projected_completion_date = _add_months(now, months_needed)
        else:
            projection.projected_completion_date = None

        if goal.deadline is not None:
            if projection.projected_completion_date is None:
                projection.is_on_track = False
            else:
                projection.is_on_track = (
                    projection.projected_completion_date <= goal.deadline
                )
            # Also compare against linear expected progress.
            created = goal.created_at or now
            total_span = _months_between(created, goal.deadline)
            elapsed = _months_between(created, now)
            if total_span > 0:
                expected = quantize_money(
                    goal.target_amount
                    * (Decimal(str(elapsed)) / Decimal(str(total_span)))
                )
                if goal.current_amount + Decimal("0.01") < expected:
                    projection.is_on_track = False

        await self._cache(goal, projection)
        return projection

    async def _cache(self, goal: Goal, projection: GoalProjection) -> None:
        payload: dict[str, Any] = {
            "required_monthly_contribution": (
                str(projection.required_monthly_contribution)
                if projection.required_monthly_contribution is not None
                else None
            ),
            "projected_completion_date": (
                projection.projected_completion_date.isoformat()
                if projection.projected_completion_date
                else None
            ),
            "is_on_track": projection.is_on_track,
            "average_monthly_contribution": str(
                projection.average_monthly_contribution
            ),
            "remaining_amount": str(projection.remaining_amount),
            "lookback_months": projection.lookback_months,
            "computed_at": _utc_now().isoformat(),
        }
        updated = goal.model_copy(update={"cached_projection": payload})
        try:
            await self._goals.update(updated)
        except Exception:  # noqa: BLE001
            # Cache is best-effort; projection is still returned.
            pass


class DeleteGoalContributionUseCase:
    """Delete a goal contribution transaction and reverse goal progress."""

    def __init__(
        self,
        transactions: TransactionRepository,
        delete_transaction: "DeleteTransactionUseCase",
    ) -> None:
        self._transactions = transactions
        self._delete_transaction = delete_transaction

    async def execute(self, transaction_id: str, *, goal_id: str) -> bool:
        tx = await self._transactions.get_by_id(transaction_id)
        if tx is None:
            return False
        if tx.goal_id != goal_id:
            raise ValueError("Transaction is not linked to this goal")
        return await self._delete_transaction.execute(transaction_id)
