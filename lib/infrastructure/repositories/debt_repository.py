"""SQLAlchemy debt repository."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import select

from lib.domain.entities.debt import Debt, DebtDirection, DebtStatus
from lib.domain.repositories.debt_repository import DebtRepository
from lib.infrastructure.db_models import DebtModel
from lib.infrastructure.repositories._base import SessionFactory, ensure_utc, session_scope

logger = logging.getLogger("finanse.infrastructure.repositories.debt")


def _to_entity(model: DebtModel) -> Debt:
    return Debt(
        id=model.id,
        counterparty=model.counterparty,
        amount=Decimal(str(model.amount)),
        remaining_amount=Decimal(str(model.remaining_amount)),
        currency=model.currency,
        direction=DebtDirection(model.direction),
        status=DebtStatus(model.status),
        interest_rate=(
            Decimal(str(model.interest_rate)) if model.interest_rate is not None else None
        ),
        due_date=ensure_utc(model.due_date),
        started_at=ensure_utc(model.started_at) or datetime.now(timezone.utc),
        comment=model.comment or "",
        created_at=ensure_utc(model.created_at) or datetime.now(timezone.utc),
        updated_at=ensure_utc(model.updated_at) or datetime.now(timezone.utc),
    )


def _apply_entity(model: DebtModel, entity: Debt) -> None:
    model.id = entity.id
    model.counterparty = entity.counterparty
    model.amount = entity.amount
    model.remaining_amount = entity.remaining_amount
    model.currency = entity.currency
    model.direction = (
        entity.direction.value
        if isinstance(entity.direction, DebtDirection)
        else str(entity.direction)
    )
    model.status = (
        entity.status.value if isinstance(entity.status, DebtStatus) else str(entity.status)
    )
    model.interest_rate = entity.interest_rate
    model.due_date = ensure_utc(entity.due_date)
    model.started_at = ensure_utc(entity.started_at) or datetime.now(timezone.utc)
    model.comment = entity.comment or ""
    model.created_at = ensure_utc(entity.created_at) or datetime.now(timezone.utc)
    model.updated_at = ensure_utc(entity.updated_at) or datetime.now(timezone.utc)


def _sort_debts(debts: list[Debt], sort_by: str) -> list[Debt]:
    key = (sort_by or "due_date").lower()
    far = datetime.max.replace(tzinfo=timezone.utc)
    if key == "remaining":
        return sorted(debts, key=lambda d: (d.remaining_amount, d.counterparty))
    if key == "amount":
        return sorted(debts, key=lambda d: (d.amount, d.counterparty), reverse=True)
    if key == "interest":
        return sorted(
            debts,
            key=lambda d: (d.interest_rate is None, -(d.interest_rate or 0), d.counterparty),
        )
    if key == "created_at":
        return sorted(debts, key=lambda d: d.created_at, reverse=True)
    if key == "counterparty":
        return sorted(debts, key=lambda d: d.counterparty.lower())
    if key == "status":
        order = {
            DebtStatus.OVERDUE: 0,
            DebtStatus.ACTIVE: 1,
            DebtStatus.PAID: 2,
            DebtStatus.ARCHIVED: 3,
        }
        return sorted(
            debts,
            key=lambda d: (order.get(d.status, 9), d.counterparty.lower()),
        )
    # due_date default — soonest first, nulls last
    return sorted(
        debts,
        key=lambda d: (d.due_date is None, d.due_date or far, d.counterparty.lower()),
    )


class SqlAlchemyDebtRepository(DebtRepository):
    """Debt persistence via SQLAlchemy sync session + ``asyncio.to_thread``."""

    def __init__(self, session_factory: SessionFactory) -> None:
        self._session_factory = session_factory

    async def create(self, debt: Debt) -> Debt:
        return await asyncio.to_thread(self._create_sync, debt)

    async def update(self, debt: Debt) -> Debt:
        return await asyncio.to_thread(self._update_sync, debt)

    async def delete(self, debt_id: str) -> bool:
        return await asyncio.to_thread(self._delete_sync, debt_id)

    async def get_by_id(self, debt_id: str) -> Optional[Debt]:
        return await asyncio.to_thread(self._get_by_id_sync, debt_id)

    async def list(
        self,
        *,
        status: Optional[DebtStatus | str] = None,
        direction: Optional[DebtDirection | str] = None,
        currency: Optional[str] = None,
        sort_by: str = "due_date",
    ) -> list[Debt]:
        return await asyncio.to_thread(
            self._list_sync, status, direction, currency, sort_by
        )

    def _create_sync(self, entity: Debt) -> Debt:
        with session_scope(self._session_factory) as session:
            model = DebtModel()
            _apply_entity(model, entity)
            session.add(model)
            session.flush()
            logger.debug("Created debt %s", model.id)
            return _to_entity(model)

    def _update_sync(self, entity: Debt) -> Debt:
        with session_scope(self._session_factory) as session:
            model = session.get(DebtModel, entity.id)
            if model is None:
                raise KeyError(f"Debt not found: {entity.id}")
            _apply_entity(model, entity)
            model.updated_at = datetime.now(timezone.utc)
            session.flush()
            logger.debug("Updated debt %s", model.id)
            return _to_entity(model)

    def _delete_sync(self, debt_id: str) -> bool:
        with session_scope(self._session_factory) as session:
            model = session.get(DebtModel, debt_id)
            if model is None:
                logger.warning("Delete skipped; debt not found: %s", debt_id)
                return False
            session.delete(model)
            logger.debug("Deleted debt %s", debt_id)
            return True

    def _get_by_id_sync(self, debt_id: str) -> Optional[Debt]:
        with session_scope(self._session_factory) as session:
            model = session.get(DebtModel, debt_id)
            return _to_entity(model) if model else None

    def _list_sync(
        self,
        status: Optional[DebtStatus | str],
        direction: Optional[DebtDirection | str],
        currency: Optional[str],
        sort_by: str,
    ) -> list[Debt]:
        with session_scope(self._session_factory) as session:
            stmt = select(DebtModel)
            if status is not None:
                value = status.value if isinstance(status, DebtStatus) else str(status)
                stmt = stmt.where(DebtModel.status == value)
            if direction is not None:
                value = (
                    direction.value
                    if isinstance(direction, DebtDirection)
                    else str(direction)
                )
                stmt = stmt.where(DebtModel.direction == value)
            if currency is not None:
                stmt = stmt.where(DebtModel.currency == currency.upper())
            entities = [_to_entity(r) for r in session.scalars(stmt).all()]
            return _sort_debts(entities, sort_by)
