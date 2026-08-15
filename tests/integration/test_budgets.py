"""Monthly category budgets: repository, use cases, transaction hooks."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from lib.domain.entities.category import CategoryKind
from lib.domain.entities.transaction import TransactionType
from lib.infrastructure.services.notification_service import NotificationKind
from tests.conftest import run_async
from tests.factories import make_account, make_category, make_transaction


def test_set_and_list_budget(container) -> None:
    async def _run() -> None:
        await container.create_category.execute(
            make_category(name="Food", kind=CategoryKind.EXPENSE)
        )
        budget = await container.set_budget.execute(
            "Food", 8, 2026, Decimal("300")
        )
        assert budget.amount_limit == Decimal("300.00")
        assert budget.spent == Decimal("0.00")

        again = await container.set_budget.execute(
            "Food", 8, 2026, Decimal("400")
        )
        assert again.id == budget.id
        assert again.amount_limit == Decimal("400.00")

        listed = await container.get_budgets_for_month.execute(8, 2026)
        assert len(listed) == 1
        assert listed[0].limit == Decimal("400.00")

        progress = await container.get_budget_progress.execute(budget_id=budget.id)
        assert progress.category_id == "Food"

        assert await container.delete_budget.execute(budget.id) is True
        assert await container.get_budgets_for_month.execute(8, 2026) == []

    run_async(_run())


def test_income_category_cannot_have_budget(container) -> None:
    async def _run() -> None:
        await container.create_category.execute(
            make_category(name="Salary", kind=CategoryKind.INCOME)
        )
        with pytest.raises(ValueError, match="expense"):
            await container.set_budget.execute("Salary", 8, 2026, Decimal("100"))

    run_async(_run())


def test_transaction_updates_spent_and_alerts(container) -> None:
    async def _run() -> None:
        await container.create_category.execute(
            make_category(name="Food", kind=CategoryKind.EXPENSE)
        )
        acc = await container.create_account.execute(make_account(balance="5000"))
        now = datetime.now(timezone.utc)
        await container.set_budget.execute("Food", now.month, now.year, Decimal("100"))

        tx = await container.add_transaction.execute(
            make_transaction(acc.id, amount="80", category="Food")
        )
        progress = await container.get_budget_progress.execute(
            category_id="Food", month=now.month, year=now.year
        )
        assert progress.spent == Decimal("80.00")
        assert progress.percent == Decimal("80.00")
        pending = container.notification_service.list_pending()
        assert any(m.kind is NotificationKind.BUDGET_WARNING for m in pending)

        await container.update_transaction.execute(
            tx.model_copy(update={"amount": Decimal("120")})
        )
        progress = await container.get_budget_progress.execute(
            category_id="Food", month=now.month, year=now.year
        )
        assert progress.spent == Decimal("120.00")
        assert progress.is_over_budget is True
        pending = container.notification_service.list_pending()
        assert any(m.kind is NotificationKind.BUDGET_OVER for m in pending)

        await container.delete_transaction.execute(tx.id)
        progress = await container.get_budget_progress.execute(
            category_id="Food", month=now.month, year=now.year
        )
        assert progress.spent == Decimal("0.00")

    run_async(_run())


def test_income_transaction_does_not_change_spent(container) -> None:
    async def _run() -> None:
        await container.create_category.execute(
            make_category(name="Both", kind=CategoryKind.BOTH)
        )
        acc = await container.create_account.execute(make_account())
        now = datetime.now(timezone.utc)
        await container.set_budget.execute("Both", now.month, now.year, Decimal("50"))
        await container.add_transaction.execute(
            make_transaction(
                acc.id,
                amount="40",
                category="Both",
                tx_type=TransactionType.INCOME,
            )
        )
        progress = await container.get_budget_progress.execute(
            category_id="Both", month=now.month, year=now.year
        )
        assert progress.spent == Decimal("0.00")

    run_async(_run())


def test_recalculate_spent(container) -> None:
    async def _run() -> None:
        await container.create_category.execute(
            make_category(name="Food", kind=CategoryKind.EXPENSE)
        )
        acc = await container.create_account.execute(make_account())
        now = datetime.now(timezone.utc)
        budget = await container.set_budget.execute(
            "Food", now.month, now.year, Decimal("200")
        )
        await container.add_transaction.execute(
            make_transaction(acc.id, amount="30", category="Food")
        )
        await container.budget_repository.update_spent(budget.id, Decimal("999"))
        updated = await container.recalculate_budget_spent.execute(
            month=now.month, year=now.year
        )
        assert updated[0].spent == Decimal("30.00")

    run_async(_run())


def test_budget_alerts_respect_settings(container) -> None:
    async def _run() -> None:
        settings = await container.get_settings.execute()
        await container.update_settings.execute(
            settings.model_copy(update={"budget_alerts": False})
        )
        await container.create_category.execute(
            make_category(name="Food", kind=CategoryKind.EXPENSE)
        )
        acc = await container.create_account.execute(make_account())
        now = datetime.now(timezone.utc)
        await container.set_budget.execute("Food", now.month, now.year, Decimal("10"))
        await container.add_transaction.execute(
            make_transaction(acc.id, amount="10", category="Food")
        )
        kinds = {m.kind for m in container.notification_service.list_pending()}
        assert NotificationKind.BUDGET_OVER not in kinds
        assert NotificationKind.BUDGET_WARNING not in kinds

    run_async(_run())


def test_delete_category_removes_budgets(container) -> None:
    async def _run() -> None:
        cat = await container.create_category.execute(
            make_category(name="Snacks", kind=CategoryKind.EXPENSE)
        )
        now = datetime.now(timezone.utc)
        await container.set_budget.execute("Snacks", now.month, now.year, Decimal("20"))
        assert await container.delete_category.execute(cat.id) is True
        listed = await container.get_budgets_for_month.execute(now.month, now.year)
        assert listed == []

    run_async(_run())
