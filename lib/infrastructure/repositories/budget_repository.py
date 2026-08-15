"""SQLAlchemy budget repository."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, Sequence

from sqlalchemy import delete, select, update

from lib.domain.entities.budget import Budget
from lib.domain.entities.money import quantize_money
from lib.domain.repositories.budget_repository import BudgetRepository
from lib.infrastructure.db_models import BudgetModel
from lib.infrastructure.repositories._base import SessionFactory, ensure_utc, session_scope

logger = logging.getLogger("finanse.infrastructure.repositories.budget")


def _to_entity(model: BudgetModel) -> Budget:
    return Budget(
        id=model.id,
        category_id=model.category_id,
        month=int(model.month),
        year=int(model.year),
        amount_limit=Decimal(str(model.amount_limit)),
        spent=Decimal(str(model.spent)),
        last_alert_level=int(getattr(model, "last_alert_level", 0) or 0),
        created_at=ensure_utc(model.created_at) or datetime.now(timezone.utc),
        updated_at=ensure_utc(model.updated_at) or datetime.now(timezone.utc),
    )


def _apply_entity(model: BudgetModel, entity: Budget) -> None:
    model.id = entity.id
    model.category_id = entity.category_id
    model.month = entity.month
    model.year = entity.year
    model.amount_limit = entity.amount_limit
    model.spent = entity.spent
    model.last_alert_level = int(entity.last_alert_level or 0)
    model.created_at = ensure_utc(entity.created_at) or datetime.now(timezone.utc)
    model.updated_at = ensure_utc(entity.updated_at) or datetime.now(timezone.utc)


class SqlAlchemyBudgetRepository(BudgetRepository):
    """Budget persistence via SQLAlchemy sync session + ``asyncio.to_thread``."""

    def __init__(self, session_factory: SessionFactory) -> None:
        self._session_factory = session_factory

    async def get_by_id(self, budget_id: str) -> Optional[Budget]:
        return await asyncio.to_thread(self._get_by_id_sync, budget_id)

    async def get_by_category_and_month(
        self, category_id: str, month: int, year: int
    ) -> Optional[Budget]:
        return await asyncio.to_thread(
            self._get_by_category_and_month_sync, category_id, month, year
        )

    async def list_for_month(
        self,
        month: int,
        year: int,
        category_ids: Optional[Sequence[str]] = None,
    ) -> list[Budget]:
        names = tuple(category_ids) if category_ids else None
        return await asyncio.to_thread(self._list_for_month_sync, month, year, names)

    async def save(self, budget: Budget) -> Budget:
        return await asyncio.to_thread(self._save_sync, budget)

    async def delete(self, budget_id: str) -> bool:
        return await asyncio.to_thread(self._delete_sync, budget_id)

    async def update_spent(self, budget_id: str, new_spent: Decimal) -> Optional[Budget]:
        return await asyncio.to_thread(self._update_spent_sync, budget_id, new_spent)

    async def delete_for_category(self, category_id: str) -> int:
        return await asyncio.to_thread(self._delete_for_category_sync, category_id)

    async def reassign_category(self, old_name: str, new_name: str) -> int:
        return await asyncio.to_thread(self._reassign_category_sync, old_name, new_name)

    def _get_by_id_sync(self, budget_id: str) -> Optional[Budget]:
        with session_scope(self._session_factory) as session:
            model = session.get(BudgetModel, budget_id)
            return _to_entity(model) if model is not None else None

    def _get_by_category_and_month_sync(
        self, category_id: str, month: int, year: int
    ) -> Optional[Budget]:
        with session_scope(self._session_factory) as session:
            stmt = select(BudgetModel).where(
                BudgetModel.category_id == category_id,
                BudgetModel.month == month,
                BudgetModel.year == year,
            )
            model = session.scalars(stmt).first()
            return _to_entity(model) if model is not None else None

    def _list_for_month_sync(
        self, month: int, year: int, category_ids: Optional[tuple[str, ...]]
    ) -> list[Budget]:
        with session_scope(self._session_factory) as session:
            stmt = select(BudgetModel).where(
                BudgetModel.month == month,
                BudgetModel.year == year,
            )
            if category_ids:
                stmt = stmt.where(BudgetModel.category_id.in_(category_ids))
            stmt = stmt.order_by(BudgetModel.category_id)
            return [_to_entity(m) for m in session.scalars(stmt).all()]

    def _save_sync(self, entity: Budget) -> Budget:
        with session_scope(self._session_factory) as session:
            model = session.get(BudgetModel, entity.id)
            if model is None:
                stmt = select(BudgetModel).where(
                    BudgetModel.category_id == entity.category_id,
                    BudgetModel.month == entity.month,
                    BudgetModel.year == entity.year,
                )
                model = session.scalars(stmt).first()
            if model is None:
                model = BudgetModel()
                session.add(model)
            _apply_entity(model, entity)
            session.flush()
            logger.debug("Saved budget %s", model.id)
            return _to_entity(model)

    def _delete_sync(self, budget_id: str) -> bool:
        with session_scope(self._session_factory) as session:
            model = session.get(BudgetModel, budget_id)
            if model is None:
                return False
            session.delete(model)
            return True

    def _update_spent_sync(self, budget_id: str, new_spent: Decimal) -> Optional[Budget]:
        spent = quantize_money(max(Decimal("0"), new_spent))
        with session_scope(self._session_factory) as session:
            model = session.get(BudgetModel, budget_id)
            if model is None:
                return None
            model.spent = spent
            model.updated_at = datetime.now(timezone.utc)
            session.flush()
            return _to_entity(model)

    def _delete_for_category_sync(self, category_id: str) -> int:
        with session_scope(self._session_factory) as session:
            result = session.execute(
                delete(BudgetModel).where(BudgetModel.category_id == category_id)
            )
            return int(result.rowcount or 0)

    def _reassign_category_sync(self, old_name: str, new_name: str) -> int:
        if old_name == new_name:
            return 0
        with session_scope(self._session_factory) as session:
            result = session.execute(
                update(BudgetModel)
                .where(BudgetModel.category_id == old_name)
                .values(category_id=new_name, updated_at=datetime.now(timezone.utc))
            )
            return int(result.rowcount or 0)
