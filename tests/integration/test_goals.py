"""Goals CRUD and contribution edge cases."""

from __future__ import annotations

from decimal import Decimal

import pytest

from tests.conftest import run_async
from tests.factories import make_account, make_goal


def test_goal_crud(container) -> None:
    async def _run() -> None:
        goal = await container.create_goal.execute(make_goal(name="Laptop"))
        listed = await container.list_goals.execute()
        assert any(g.id == goal.id for g in listed)

        updated = await container.update_goal.execute(
            goal.model_copy(update={"name": "Laptop Pro", "target_amount": Decimal("900")})
        )
        assert updated.name == "Laptop Pro"
        assert updated.target_amount == Decimal("900.00")

        assert await container.delete_goal.execute(goal.id) is True

    run_async(_run())


def test_contribute_to_completed_goal_fails(container) -> None:
    async def _run() -> None:
        acc = await container.create_account.execute(make_account(balance="1000"))
        goal = await container.create_goal.execute(make_goal(target="100"))
        await container.contribute_to_goal.execute(
            goal.id, Decimal("100"), account_id=acc.id
        )
        with pytest.raises(ValueError, match="already completed"):
            await container.contribute_to_goal.execute(
                goal.id, Decimal("10"), account_id=acc.id
            )

    run_async(_run())

def test_contribute_completes_goal(container) -> None:
    async def _run() -> None:
        acc = await container.create_account.execute(make_account(balance="1000"))
        goal = await container.create_goal.execute(make_goal(target="200"))
        updated = await container.contribute_to_goal.execute(
            goal.id, Decimal("200"), account_id=acc.id
        )
        assert updated.is_completed is True
        assert updated.current_amount == Decimal("200.00")

    run_async(_run())
