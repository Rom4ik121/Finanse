"""Unit tests for debt payoff projection."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from lib.domain.entities.debt import Debt, DebtDirection, DebtStatus
from lib.domain.entities.money import quantize_money
from lib.domain.entities.transaction import Transaction, TransactionType
from lib.domain.use_cases.debts import GetDebtProjectionUseCase
from tests.conftest import run_async


class _FakeDebts:
    def __init__(self, debt: Debt) -> None:
        self.debt = debt

    async def get_by_id(self, debt_id: str):
        return self.debt if self.debt.id == debt_id else None


class _FakeTx:
    def __init__(self, rows: list[Transaction]) -> None:
        self.rows = rows

    async def list(self, **kwargs):
        debt_id = kwargs.get("debt_id")
        date_from = kwargs.get("date_from")
        out = [tx for tx in self.rows if tx.debt_id == debt_id]
        if date_from is not None:
            out = [tx for tx in out if tx.date >= date_from]
        return out


def test_no_payments_does_not_fake_payoff_date() -> None:
    async def _run() -> None:
        now = datetime.now(timezone.utc)
        debt = Debt(
            counterparty="Bank",
            amount=Decimal("900"),
            remaining_amount=Decimal("900"),
            direction=DebtDirection.I_OWE,
            status=DebtStatus.ACTIVE,
            due_date=now + timedelta(days=90),
            started_at=now - timedelta(days=10),
        )
        uc = GetDebtProjectionUseCase(_FakeDebts(debt), _FakeTx([]), lookback_months=3)
        projection = await uc.execute(debt.id)
        months_left = Decimal("90") / Decimal("30.4375")
        assert projection.recommended_monthly_payment == quantize_money(
            Decimal("900") / months_left
        )
        assert projection.projected_payoff_date is None
        assert projection.average_monthly_payment == Decimal("0.00")
        assert projection.is_on_track is False

    run_async(_run())


def test_short_history_average_not_diluted_by_lookback() -> None:
    async def _run() -> None:
        now = datetime.now(timezone.utc)
        debt = Debt(
            counterparty="Bank",
            amount=Decimal("600"),
            remaining_amount=Decimal("400"),
            direction=DebtDirection.I_OWE,
            due_date=now + timedelta(days=120),
            started_at=now - timedelta(days=20),
        )
        tx = Transaction(
            account_id="a1",
            amount=Decimal("200"),
            category="Долг",
            date=now - timedelta(days=5),
            type=TransactionType.EXPENSE,
            currency="RUB",
            debt_id=debt.id,
            debt_credit_amount=Decimal("200"),
        )
        uc = GetDebtProjectionUseCase(
            _FakeDebts(debt), _FakeTx([tx]), lookback_months=3
        )
        projection = await uc.execute(debt.id)
        assert projection.average_monthly_payment == Decimal("200.00")
        assert projection.projected_payoff_date is not None
        assert projection.is_on_track is True

    run_async(_run())


def test_interest_slows_payoff_and_raises_recommended() -> None:
    async def _run() -> None:
        now = datetime.now(timezone.utc)
        debt = Debt(
            counterparty="Bank",
            amount=Decimal("1200"),
            remaining_amount=Decimal("1200"),
            direction=DebtDirection.I_OWE,
            interest_rate=Decimal("12"),
            due_date=now + timedelta(days=365),
            started_at=now,
        )
        uc = GetDebtProjectionUseCase(_FakeDebts(debt), _FakeTx([]), lookback_months=3)
        projection = await uc.execute(debt.id)
        months_left = Decimal("365") / Decimal("30.4375")
        monthly_interest = quantize_money(Decimal("1200") * Decimal("12") / Decimal("100") / Decimal("12"))
        assert monthly_interest == Decimal("12.00")
        assert projection.recommended_monthly_payment == quantize_money(
            Decimal("1200") / months_left + monthly_interest
        )
        assert projection.projected_payoff_date is None
        assert projection.is_on_track is False

        tx = Transaction(
            account_id="a1",
            amount=Decimal("12"),
            category="Долг",
            date=now - timedelta(days=3),
            type=TransactionType.EXPENSE,
            currency="RUB",
            debt_id=debt.id,
            debt_credit_amount=Decimal("12"),
        )
        uc2 = GetDebtProjectionUseCase(
            _FakeDebts(debt), _FakeTx([tx]), lookback_months=3
        )
        interest_only = await uc2.execute(debt.id)
        assert interest_only.projected_payoff_date is None
        assert interest_only.is_on_track is False

    run_async(_run())
