"""Transaction update/delete and stats."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from lib.domain.entities.transaction import TransactionType
from lib.domain.use_cases.transactions import StatsPeriod
from tests.conftest import run_async
from tests.factories import make_account, make_transaction


def test_update_and_delete_transaction_reconciles_balance(container) -> None:
    async def _run() -> None:
        acc = await container.create_account.execute(make_account(balance="500"))
        tx = await container.add_transaction.execute(
            make_transaction(acc.id, amount="100")
        )
        mid = await container.account_repository.get_by_id(acc.id)
        assert mid is not None
        assert mid.balance == Decimal("400.00")

        await container.update_transaction.execute(
            tx.model_copy(update={"amount": Decimal("50")})
        )
        after_update = await container.account_repository.get_by_id(acc.id)
        assert after_update is not None
        assert after_update.balance == Decimal("450.00")

        assert await container.delete_transaction.execute(tx.id) is True
        final = await container.account_repository.get_by_id(acc.id)
        assert final is not None
        assert final.balance == Decimal("500.00")

    run_async(_run())


def test_list_transactions_filters(container) -> None:
    async def _run() -> None:
        acc = await container.create_account.execute(make_account())
        await container.add_transaction.execute(
            make_transaction(acc.id, amount="10", category="Еда")
        )
        await container.add_transaction.execute(
            make_transaction(
                acc.id,
                amount="20",
                category="Зарплата",
                tx_type=TransactionType.INCOME,
            )
        )
        expenses = await container.list_transactions.execute(
            account_id=acc.id,
            transaction_type=TransactionType.EXPENSE,
        )
        assert len(expenses) == 1
        assert expenses[0].category == "Еда"

    run_async(_run())


def test_transaction_stats(container) -> None:
    async def _run() -> None:
        acc = await container.create_account.execute(make_account())
        now = datetime.now(timezone.utc)
        await container.add_transaction.execute(
            make_transaction(acc.id, amount="40", category="Еда")
        )
        await container.add_transaction.execute(
            make_transaction(
                acc.id,
                amount="100",
                category="Зарплата",
                tx_type=TransactionType.INCOME,
            )
        )
        stats = await container.get_transaction_stats.execute(
            account_id=acc.id,
            group_by=StatsPeriod.DAY,
        )
        assert stats.total_expense == Decimal("40.00")
        assert stats.total_income == Decimal("100.00")
        assert stats.by_category
        assert stats.by_period
        _ = now

    run_async(_run())
