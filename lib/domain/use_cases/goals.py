"""Goal-related use cases."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING

from lib.core.config import SAVINGS_CATEGORIES
from lib.domain.entities.goal import Goal
from lib.domain.entities.money import quantize_money
from lib.domain.entities.transaction import Transaction, TransactionType
from lib.domain.repositories.account_repository import AccountRepository
from lib.domain.repositories.goal_repository import GoalRepository

if TYPE_CHECKING:
    from lib.domain.use_cases.transactions import AddTransactionUseCase


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _savings_category(goal: Goal) -> str:
    link = (goal.category_link or "").strip()
    if link in SAVINGS_CATEGORIES:
        return link
    return "Накопление"


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
                "is_completed": False,
            }
        )
        return await self._goals.create(created)


class UpdateGoalUseCase:
    """Update goal metadata (progress only changes via contributions)."""

    def __init__(self, goals: GoalRepository) -> None:
        self._goals = goals

    async def execute(self, goal: Goal) -> Goal:
        """Update name/target/deadline/priority; keep ledger-based progress."""
        existing = await self._goals.get_by_id(goal.id)
        if existing is None:
            raise ValueError(f"Goal not found: {goal.id}")

        target = quantize_money(goal.target_amount)
        current = quantize_money(existing.current_amount)
        updated = goal.model_copy(
            update={
                "current_amount": current,
                "target_amount": target,
                "is_completed": current >= target,
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
        include_completed: bool = True,
        min_priority: int | None = None,
    ) -> list[Goal]:
        """Return goals with optional filters."""
        return await self._goals.list(
            include_completed=include_completed,
            min_priority=min_priority,
        )


class ContributeToGoalUseCase:
    """Move money from an account into a goal (creates an expense transaction)."""

    def __init__(
        self,
        goals: GoalRepository,
        accounts: AccountRepository,
        add_transaction: "AddTransactionUseCase",
    ) -> None:
        self._goals = goals
        self._accounts = accounts
        self._add_transaction = add_transaction

    async def execute(
        self,
        goal_id: str,
        amount: Decimal,
        *,
        account_id: str,
    ) -> Goal:
        """Debit ``account_id`` and increase the goal's ``current_amount``."""
        amount = quantize_money(amount)
        if amount <= 0:
            raise ValueError("Contribution amount must be positive")
        if not (account_id or "").strip():
            raise ValueError("Account is required to fund a goal")

        goal = await self._goals.get_by_id(goal_id)
        if goal is None:
            raise ValueError(f"Goal not found: {goal_id}")
        if goal.is_completed:
            raise ValueError("Goal is already completed")

        account = await self._accounts.get_by_id(account_id)
        if account is None:
            raise ValueError(f"Account not found: {account_id}")

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
            )
        )
        updated = await self._goals.get_by_id(goal_id)
        if updated is None:
            raise ValueError(f"Goal not found after contribution: {goal_id}")
        return updated
