"""Category use cases."""

from __future__ import annotations

import pytest

from lib.domain.entities.category import CategoryKind
from tests.conftest import run_async
from tests.factories import make_category


def test_create_unique_and_find_or_create(container) -> None:
    async def _run() -> None:
        created = await container.create_category.execute(
            make_category(name="Coffee")
        )
        with pytest.raises(ValueError):
            await container.create_category.execute(make_category(name="Coffee"))

        same = await container.find_or_create_category.execute("Coffee")
        assert same.id == created.id

        other = await container.find_or_create_category.execute("Tea")
        assert other.name == "Tea"

    run_async(_run())


def test_system_category_cannot_be_deleted(container) -> None:
    async def _run() -> None:
        system = await container.create_category.execute(
            make_category(name="SystemCat", is_system=True)
        )
        with pytest.raises(ValueError):
            await container.delete_category.execute(system.id)

        user = await container.create_category.execute(
            make_category(name="UserCat", is_system=False)
        )
        assert await container.delete_category.execute(user.id) is True

    run_async(_run())


def test_list_categories_for_type(container) -> None:
    async def _run() -> None:
        await container.create_category.execute(
            make_category(name="OnlyExpense", kind=CategoryKind.EXPENSE)
        )
        await container.create_category.execute(
            make_category(name="OnlyIncome", kind=CategoryKind.INCOME)
        )
        await container.create_category.execute(
            make_category(name="Both", kind=CategoryKind.BOTH)
        )
        for_expense = await container.list_categories.execute(for_type="expense")
        names = {c.name for c in for_expense}
        assert "OnlyExpense" in names
        assert "Both" in names
        assert "OnlyIncome" not in names

    run_async(_run())
