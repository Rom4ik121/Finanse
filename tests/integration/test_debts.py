"""Debt interest, FX repay, archive, projection."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from lib.domain.entities.currency import ExchangeRate
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


def test_repay_converts_foreign_currency(container) -> None:
    async def _run() -> None:
        await container.currency_repository.upsert_rate(
            ExchangeRate(
                base="USD",
                quote="RUB",
                rate=Decimal("100"),
                updated_at=datetime.now(timezone.utc),
            )
        )
        usd = await container.create_account.execute(
            make_account(name="USD", currency="USD", balance="50")
        )
        debt = await container.create_debt.execute(
            make_debt(amount="500", currency="RUB", direction=DebtDirection.I_OWE)
        )
        paid = await container.repay_debt.execute(
            debt.id, Decimal("5"), account_id=usd.id
        )
        assert paid.remaining_amount == Decimal("0.00")
        assert paid.status == DebtStatus.PAID
        txs = await container.list_transactions.execute(debt_id=debt.id)
        assert len(txs) == 1
        assert txs[0].amount == Decimal("5.00")
        assert txs[0].currency == "USD"
        assert txs[0].debt_credit_amount == Decimal("500.00")

    run_async(_run())


def test_repay_blocks_missing_rate(container) -> None:
    async def _run() -> None:
        eur = await container.create_account.execute(
            make_account(name="EUR", currency="EUR", balance="100")
        )
        debt = await container.create_debt.execute(
            make_debt(amount="100", currency="RUB")
        )
        with pytest.raises(ValueError, match="No exchange rate"):
            await container.repay_debt.execute(
                debt.id, Decimal("10"), account_id=eur.id
            )

    run_async(_run())


def test_archive_and_filter_status(container) -> None:
    async def _run() -> None:
        acc = await container.create_account.execute(make_account(balance="1000"))
        debt = await container.create_debt.execute(
            make_debt(amount="50"), account_id=acc.id
        )
        await container.repay_debt.execute(debt.id, Decimal("50"), account_id=acc.id)
        archived = await container.archive_debt.execute(debt.id)
        assert archived.status == DebtStatus.ARCHIVED
        active = await container.list_debts.execute(status=DebtStatus.ACTIVE)
        assert all(d.id != debt.id for d in active)
        archived_list = await container.list_debts.execute(status=DebtStatus.ARCHIVED)
        assert any(d.id == debt.id for d in archived_list)

    run_async(_run())


def test_mark_overdue_and_projection(container) -> None:
    async def _run() -> None:
        past = datetime.now(timezone.utc) - timedelta(days=5)
        debt = await container.create_debt.execute(
            make_debt(amount="300").model_copy(update={"due_date": past})
        )
        changed = await container.mark_overdue_debts.execute()
        assert any(d.id == debt.id for d in changed)
        refreshed = await container.debt_repository.get_by_id(debt.id)
        assert refreshed is not None
        assert refreshed.status == DebtStatus.OVERDUE

        future = datetime.now(timezone.utc) + timedelta(days=90)
        debt2 = await container.create_debt.execute(
            make_debt(amount="900").model_copy(update={"due_date": future})
        )
        projection = await container.get_debt_projection.execute(debt2.id)
        assert projection.remaining_amount == Decimal("900.00")
        assert projection.recommended_monthly_payment is not None
        assert projection.recommended_monthly_payment > 0

    run_async(_run())


def test_delete_debt_payment_restores_remaining(container) -> None:
    async def _run() -> None:
        acc = await container.create_account.execute(make_account(balance="1000"))
        debt = await container.create_debt.execute(
            make_debt(amount="200"), account_id=acc.id
        )
        await container.repay_debt.execute(debt.id, Decimal("80"), account_id=acc.id)
        txs = await container.list_transactions.execute(debt_id=debt.id)
        assert len(txs) == 1
        deleted = await container.delete_debt_payment.execute(
            txs[0].id, debt_id=debt.id
        )
        assert deleted is True
        refreshed = await container.debt_repository.get_by_id(debt.id)
        assert refreshed is not None
        assert refreshed.remaining_amount == Decimal("200.00")
        assert refreshed.status == DebtStatus.ACTIVE

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
