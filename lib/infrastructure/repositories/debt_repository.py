"""SQLAlchemy debt repository."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

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
        interest_rate=Decimal(str(model.interest_rate)) if model.interest_rate is not None else None,
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
        status: Optional[DebtStatus] = None,
        direction: Optional[DebtDirection] = None,
    ) -> list[Debt]:
        return await asyncio.to_thread(self._list_sync, status, direction)

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
        status: Optional[DebtStatus],
        direction: Optional[DebtDirection],
    ) -> list[Debt]:
        with session_scope(self._session_factory) as session:
            stmt = select(DebtModel)
            if status is not None:
                value = status.value if isinstance(status, DebtStatus) else str(status)
                stmt = stmt.where(DebtModel.status == value)
            if direction is not None:
                value = direction.value if isinstance(direction, DebtDirection) else str(direction)
                stmt = stmt.where(DebtModel.direction == value)
            stmt = stmt.order_by(DebtModel.due_date.asc(), DebtModel.counterparty)
            return [_to_entity(r) for r in session.scalars(stmt).all()]
