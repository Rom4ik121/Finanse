"""Account CRUD and balance recalculation."""

from __future__ import annotations

from decimal import Decimal

from tests.conftest import run_async
from tests.factories import make_account, make_transaction
from lib.domain.entities.transaction import TransactionType


def test_create_list_update_delete_account(container) -> None:
    async def _run() -> None:
        created = await container.create_account.execute(make_account(name="Wallet"))
        listed = await container.list_accounts.execute()
        assert any(a.id == created.id for a in listed)

        updated = await container.update_account.execute(
            created.model_copy(update={"name": "Main"})
        )
        assert updated.name == "Main"

        assert await container.delete_account.execute(created.id) is True
        remaining = await container.list_accounts.execute()
        assert all(a.id != created.id for a in remaining)

    run_async(_run())


def test_income_and_recalculate_balance(container) -> None:
    async def _run() -> None:
        acc = await container.create_account.execute(
            make_account(balance="100")
        )
        await container.add_transaction.execute(
            make_transaction(
                acc.id,
                amount="50",
                tx_type=TransactionType.INCOME,
                category="Зарплата",
            )
        )
        await container.add_transaction.execute(
            make_transaction(acc.id, amount="30", category="Еда")
        )
        refreshed = await container.account_repository.get_by_id(acc.id)
        assert refreshed is not None
        assert refreshed.balance == Decimal("120.00")

        # Corrupt balance then recalculate from ledger.
        await container.update_account.execute(
            refreshed.model_copy(update={"balance": Decimal("0")})
        )
        fixed = await container.recalculate_account_balance.execute(acc.id)
        assert fixed.balance == Decimal("120.00")

    run_async(_run())
