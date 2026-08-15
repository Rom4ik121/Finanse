"""Unit tests for goal projection helpers."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from lib.domain.entities.goal import Goal, GoalStatus
from lib.domain.entities.money import quantize_money
from lib.domain.entities.transaction import Transaction, TransactionType
from lib.domain.use_cases.goals import GetGoalProjectionUseCase, goal_credit_amount
from tests.conftest import run_async


class _FakeGoals:
    def __init__(self, goal: Goal) -> None:
        self.goal = goal

    async def get_by_id(self, goal_id: str):
        return self.goal if self.goal.id == goal_id else None

    async def update(self, goal: Goal) -> Goal:
        self.goal = goal
        return goal


class _FakeTx:
    def __init__(self, rows: list[Transaction]) -> None:
        self.rows = rows

    async def list(self, **kwargs):
        goal_id = kwargs.get("goal_id")
        date_from = kwargs.get("date_from")
        out = [tx for tx in self.rows if tx.goal_id == goal_id]
        if date_from is not None:
            out = [tx for tx in out if tx.date >= date_from]
        return out


def test_projection_required_monthly() -> None:
    async def _run() -> None:
        now = datetime.now(timezone.utc)
        goal = Goal(
            name="Car",
            target_amount=Decimal("1200"),
            current_amount=Decimal("200"),
            currency="RUB",
            deadline=now + timedelta(days=120),
            created_at=now - timedelta(days=30),
            status=GoalStatus.ACTIVE,
        )
        tx = Transaction(
            account_id="a1",
            amount=Decimal("200"),
            category="Накопление",
            date=now - timedelta(days=10),
            type=TransactionType.EXPENSE,
            currency="RUB",
            goal_id=goal.id,
            goal_credit_amount=Decimal("200"),
        )
        uc = GetGoalProjectionUseCase(
            _FakeGoals(goal), _FakeTx([tx]), lookback_months=6
        )
        projection = await uc.execute(goal.id)
        assert projection.remaining_amount == Decimal("1000.00")
        months_left = Decimal("120") / Decimal("30.4375")
        assert projection.required_monthly_contribution == quantize_money(
            Decimal("1000") / months_left
        )
        # Short history: do not divide a recent lump by the full 6-month window.
        assert projection.average_monthly_contribution == Decimal("200.00")
        assert goal_credit_amount(tx) == Decimal("200.00")

    run_async(_run())


def test_projection_on_track_uses_pace_not_linear_schedule() -> None:
    async def _run() -> None:
        now = datetime.now(timezone.utc)
        goal = Goal(
            name="Catch up",
            target_amount=Decimal("1200"),
            current_amount=Decimal("850"),
            currency="RUB",
            deadline=now + timedelta(days=90),
            created_at=now - timedelta(days=365),
            status=GoalStatus.ACTIVE,
        )
        tx = Transaction(
            account_id="a1",
            amount=Decimal("850"),
            category="Накопление",
            date=now - timedelta(days=30),
            type=TransactionType.EXPENSE,
            currency="RUB",
            goal_id=goal.id,
            goal_credit_amount=Decimal("850"),
        )
        uc = GetGoalProjectionUseCase(
            _FakeGoals(goal), _FakeTx([tx]), lookback_months=6
        )
        projection = await uc.execute(goal.id)
        assert projection.projected_completion_date is not None
        assert projection.projected_completion_date <= goal.deadline
        assert projection.is_on_track is True

    run_async(_run())


def test_projection_off_track_when_no_contributions() -> None:
    async def _run() -> None:
        now = datetime.now(timezone.utc)
        goal = Goal(
            name="Idle",
            target_amount=Decimal("500"),
            current_amount=Decimal("0"),
            deadline=now + timedelta(days=90),
            created_at=now - timedelta(days=30),
            status=GoalStatus.ACTIVE,
        )
        uc = GetGoalProjectionUseCase(_FakeGoals(goal), _FakeTx([]), lookback_months=6)
        projection = await uc.execute(goal.id)
        assert projection.average_monthly_contribution == Decimal("0.00")
        assert projection.projected_completion_date is None
        assert projection.is_on_track is False

    run_async(_run())


def test_goal_status_auto_completes_from_amount() -> None:
    goal = Goal(
        name="X",
        target_amount=Decimal("100"),
        current_amount=Decimal("100"),
        status=GoalStatus.ACTIVE,
    )
    assert goal.status == GoalStatus.COMPLETED
    assert goal.is_completed is True
