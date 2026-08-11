"""Debt interest and overpay clamp."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from lib.domain.entities.debt import DebtDirection, DebtStatus
from tests.conftest import run_async
from tests.factories import make_account, make_debt


def test_debt_crud_and_list(container) -> None:
    async def _run() -> None:
        debt = await container.create_debt.execute(make_debt())
        listed = await container.list_debts.execute()
        assert any(d.id == debt.id for d in listed)
        assert await container.delete_debt.execute(debt.id) is True

    run_async(_run())


def test_repay_clamps_to_remaining(container) -> None:
    async def _run() -> None:
        acc = await container.create_account.execute(make_account(balance="1000"))
        debt = await container.create_debt.execute(
            make_debt(amount="100", direction=DebtDirection.I_OWE),
            account_id=acc.id,
        )
        paid = await container.repay_debt.execute(
            debt.id, Decimal("999"), account_id=acc.id
        )
        assert paid.remaining_amount == Decimal("0.00")
        assert paid.status == DebtStatus.PAID

    run_async(_run())


def test_calculate_interest(container) -> None:
    async def _run() -> None:
        started = datetime.now(timezone.utc) - timedelta(days=365)
        debt = await container.create_debt.execute(
            make_debt(amount="1000", interest_rate=Decimal("10"))
        )
        await container.update_debt.execute(
            debt.model_copy(update={"started_at": started})
        )
        result = await container.calculate_debt_interest.execute(debt.id)
        assert result.days >= 365
        assert result.interest_amount >= Decimal("100.00")

    run_async(_run())


def test_interest_requires_rate(container) -> None:
    async def _run() -> None:
        debt = await container.create_debt.execute(make_debt())
        with pytest.raises(ValueError):
            await container.calculate_debt_interest.execute(debt.id)

    run_async(_run())
