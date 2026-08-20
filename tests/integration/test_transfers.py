"""Account-to-account transfers: pair of linked transactions."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from lib.domain.entities.category import CategoryKind
from lib.domain.entities.currency import ExchangeRate
from lib.domain.entities.transaction import TransactionType
from tests.conftest import run_async
from tests.factories import make_account, make_category


def test_same_currency_transfer_updates_balances(container) -> None:
    async def _run() -> None:
        src = await container.create_account.execute(
            make_account(name="Wallet", balance="1000")
        )
        dst = await container.create_account.execute(
            make_account(name="Cash", balance="100")
        )
        out, incoming = await container.transfer_between_accounts.execute(
            from_account_id=src.id,
            to_account_id=dst.id,
            amount=Decimal("250"),
            comment="pocket",
        )
        assert out.transfer_id == incoming.transfer_id
        assert out.type is TransactionType.EXPENSE
        assert incoming.type is TransactionType.INCOME
        assert out.amount == Decimal("250.00")
        assert incoming.amount == Decimal("250.00")
        assert "Cash" in out.comment
        assert "pocket" in out.comment

        src2 = await container.account_repository.get_by_id(src.id)
        dst2 = await container.account_repository.get_by_id(dst.id)
        assert src2.balance == Decimal("750.00")
        assert dst2.balance == Decimal("350.00")

        listed = await container.list_transactions.execute(has_transfer=True)
        assert len(listed) == 2

    run_async(_run())


def test_fx_transfer_converts_destination_amount(container) -> None:
    async def _run() -> None:
        await container.currency_repository.upsert_rate(
            ExchangeRate(
                base="USD",
                quote="RUB",
                rate=Decimal("90"),
                updated_at=datetime.now(timezone.utc),
            )
        )
        src = await container.create_account.execute(
            make_account(name="USD", currency="USD", balance="100")
        )
        dst = await container.create_account.execute(
            make_account(name="RUB", currency="RUB", balance="0")
        )
        _out, incoming = await container.transfer_between_accounts.execute(
            from_account_id=src.id,
            to_account_id=dst.id,
            amount=Decimal("10"),
        )
        assert incoming.amount == Decimal("900.00")
        assert incoming.currency == "RUB"
        dst2 = await container.account_repository.get_by_id(dst.id)
        assert dst2.balance == Decimal("900.00")

    run_async(_run())


def test_same_account_and_insufficient_funds(container) -> None:
    async def _run() -> None:
        src = await container.create_account.execute(
            make_account(name="A", balance="50")
        )
        dst = await container.create_account.execute(
            make_account(name="B", balance="0")
        )
        with pytest.raises(ValueError, match="same account"):
            await container.transfer_between_accounts.execute(
                from_account_id=src.id,
                to_account_id=src.id,
                amount=Decimal("10"),
            )
        with pytest.raises(ValueError, match="Insufficient"):
            await container.transfer_between_accounts.execute(
                from_account_id=src.id,
                to_account_id=dst.id,
                amount=Decimal("80"),
            )
        with pytest.raises(ValueError, match="exchange rate"):
            usd = await container.create_account.execute(
                make_account(name="USD", currency="USD", balance="20")
            )
            await container.transfer_between_accounts.execute(
                from_account_id=src.id,
                to_account_id=usd.id,
                amount=Decimal("10"),
            )

    run_async(_run())


def test_delete_transfer_removes_both_legs(container) -> None:
    async def _run() -> None:
        src = await container.create_account.execute(
            make_account(name="Wallet", balance="1000")
        )
        dst = await container.create_account.execute(
            make_account(name="Cash", balance="100")
        )
        out, _incoming = await container.transfer_between_accounts.execute(
            from_account_id=src.id,
            to_account_id=dst.id,
            amount=Decimal("200"),
        )
        assert await container.delete_transaction.execute(out.id) is True
        remaining = await container.list_transactions.execute()
        assert remaining == []
        src2 = await container.account_repository.get_by_id(src.id)
        dst2 = await container.account_repository.get_by_id(dst.id)
        assert src2.balance == Decimal("1000.00")
        assert dst2.balance == Decimal("100.00")

    run_async(_run())


def test_transfer_skipped_in_stats_and_budgets(container) -> None:
    async def _run() -> None:
        await container.create_category.execute(
            make_category(name="Перевод", kind=CategoryKind.BOTH)
        )
        await container.create_category.execute(
            make_category(name="Food", kind=CategoryKind.EXPENSE)
        )
        src = await container.create_account.execute(
            make_account(name="Wallet", balance="1000")
        )
        dst = await container.create_account.execute(
            make_account(name="Cash", balance="0")
        )
        now = datetime.now(timezone.utc)
        await container.set_budget.execute("Food", now.month, now.year, Decimal("500"))
        await container.set_budget.execute("Перевод", now.month, now.year, Decimal("500"))

        await container.transfer_between_accounts.execute(
            from_account_id=src.id,
            to_account_id=dst.id,
            amount=Decimal("100"),
        )
        food_progress = await container.get_budget_progress.execute(
            category_id="Food", month=now.month, year=now.year
        )
        transfer_progress = await container.get_budget_progress.execute(
            category_id="Перевод", month=now.month, year=now.year
        )
        assert food_progress.spent == Decimal("0.00")
        assert transfer_progress.spent == Decimal("0.00")

        stats = await container.get_transaction_stats.execute()
        assert stats.total_expense == Decimal("0.00")
        assert stats.total_income == Decimal("0.00")

    run_async(_run())


def test_transfer_amount_cannot_be_edited(container) -> None:
    async def _run() -> None:
        src = await container.create_account.execute(
            make_account(name="Wallet", balance="1000")
        )
        dst = await container.create_account.execute(
            make_account(name="Cash", balance="0")
        )
        out, _incoming = await container.transfer_between_accounts.execute(
            from_account_id=src.id,
            to_account_id=dst.id,
            amount=Decimal("40"),
        )
        with pytest.raises(ValueError, match="independently"):
            await container.update_transaction.execute(
                out.model_copy(update={"amount": Decimal("10")})
            )
        saved = await container.update_transaction.execute(
            out.model_copy(update={"comment": "note"})
        )
        assert saved.comment == "note"
        assert saved.amount == Decimal("40.00")

    run_async(_run())
