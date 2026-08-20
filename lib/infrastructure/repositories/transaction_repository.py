"""SQLAlchemy transaction repository."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, Sequence

from sqlalchemy import select

from lib.domain.entities.transaction import Transaction, TransactionType
from lib.domain.repositories.transaction_repository import TransactionRepository
from lib.infrastructure.db_models import TransactionModel
from lib.infrastructure.repositories._base import SessionFactory, ensure_utc, session_scope

logger = logging.getLogger("finanse.infrastructure.repositories.transaction")


def _to_entity(model: TransactionModel) -> Transaction:
    tags = list(model.tags or [])
    return Transaction(
        id=model.id,
        account_id=model.account_id,
        amount=Decimal(str(model.amount)),
        category=model.category,
        tags=tags,
        date=ensure_utc(model.date) or datetime.now(timezone.utc),
        comment=model.comment or "",
        type=TransactionType(model.type),
        currency=model.currency,
        goal_id=model.goal_id,
        debt_id=getattr(model, "debt_id", None),
        subscription_id=getattr(model, "subscription_id", None),
        goal_credit_amount=(
            Decimal(str(model.goal_credit_amount))
            if getattr(model, "goal_credit_amount", None) is not None
            else None
        ),
        debt_credit_amount=(
            Decimal(str(model.debt_credit_amount))
            if getattr(model, "debt_credit_amount", None) is not None
            else None
        ),
        transfer_id=getattr(model, "transfer_id", None),
        transfer_peer_account_id=getattr(model, "transfer_peer_account_id", None),
        created_at=ensure_utc(model.created_at) or datetime.now(timezone.utc),
        updated_at=ensure_utc(model.updated_at) or datetime.now(timezone.utc),
    )


def _apply_entity(model: TransactionModel, entity: Transaction) -> None:
    model.id = entity.id
    model.account_id = entity.account_id
    model.amount = entity.amount
    model.category = entity.category
    model.tags = list(entity.tags or [])
    model.date = ensure_utc(entity.date) or datetime.now(timezone.utc)
    model.comment = entity.comment or ""
    model.type = entity.type.value if isinstance(entity.type, TransactionType) else str(entity.type)
    model.currency = entity.currency
    model.goal_id = entity.goal_id
    model.debt_id = entity.debt_id
    model.subscription_id = entity.subscription_id
    model.goal_credit_amount = entity.goal_credit_amount
    model.debt_credit_amount = entity.debt_credit_amount
    model.transfer_id = entity.transfer_id
    model.transfer_peer_account_id = entity.transfer_peer_account_id
    model.created_at = ensure_utc(entity.created_at) or datetime.now(timezone.utc)
    model.updated_at = ensure_utc(entity.updated_at) or datetime.now(timezone.utc)


class SqlAlchemyTransactionRepository(TransactionRepository):
    """Transaction persistence via SQLAlchemy sync session + ``asyncio.to_thread``."""

    def __init__(self, session_factory: SessionFactory) -> None:
        self._session_factory = session_factory

    async def create(self, transaction: Transaction) -> Transaction:
        return await asyncio.to_thread(self._create_sync, transaction)

    async def update(self, transaction: Transaction) -> Transaction:
        return await asyncio.to_thread(self._update_sync, transaction)

    async def delete(self, transaction_id: str) -> bool:
        return await asyncio.to_thread(self._delete_sync, transaction_id)

    async def get_by_id(self, transaction_id: str) -> Optional[Transaction]:
        return await asyncio.to_thread(self._get_by_id_sync, transaction_id)

    async def list(
        self,
        *,
        account_id: Optional[str] = None,
        category: Optional[str] = None,
        transaction_type: Optional[TransactionType] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        tags: Optional[Sequence[str]] = None,
        goal_id: Optional[str] = None,
        debt_id: Optional[str] = None,
        subscription_id: Optional[str] = None,
        has_subscription: Optional[bool] = None,
        transfer_id: Optional[str] = None,
        has_transfer: Optional[bool] = None,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> list[Transaction]:
        return await asyncio.to_thread(
            self._list_sync,
            account_id,
            category,
            transaction_type,
            date_from,
            date_to,
            list(tags) if tags is not None else None,
            goal_id,
            debt_id,
            subscription_id,
            has_subscription,
            transfer_id,
            has_transfer,
            limit,
            offset,
        )

    def _create_sync(self, entity: Transaction) -> Transaction:
        with session_scope(self._session_factory) as session:
            model = TransactionModel()
            _apply_entity(model, entity)
            session.add(model)
            session.flush()
            logger.debug("Created transaction %s", model.id)
            return _to_entity(model)

    def _update_sync(self, entity: Transaction) -> Transaction:
        with session_scope(self._session_factory) as session:
            model = session.get(TransactionModel, entity.id)
            if model is None:
                raise KeyError(f"Transaction not found: {entity.id}")
            _apply_entity(model, entity)
            model.updated_at = datetime.now(timezone.utc)
            session.flush()
            logger.debug("Updated transaction %s", model.id)
            return _to_entity(model)

    def _delete_sync(self, transaction_id: str) -> bool:
        with session_scope(self._session_factory) as session:
            model = session.get(TransactionModel, transaction_id)
            if model is None:
                logger.warning("Delete skipped; transaction not found: %s", transaction_id)
                return False
            session.delete(model)
            logger.debug("Deleted transaction %s", transaction_id)
            return True

    def _get_by_id_sync(self, transaction_id: str) -> Optional[Transaction]:
        with session_scope(self._session_factory) as session:
            model = session.get(TransactionModel, transaction_id)
            return _to_entity(model) if model else None

    def _list_sync(
        self,
        account_id: Optional[str],
        category: Optional[str],
        transaction_type: Optional[TransactionType],
        date_from: Optional[datetime],
        date_to: Optional[datetime],
        tags: Optional[list[str]],
        goal_id: Optional[str],
        debt_id: Optional[str],
        subscription_id: Optional[str],
        has_subscription: Optional[bool],
        transfer_id: Optional[str],
        has_transfer: Optional[bool],
        limit: Optional[int],
        offset: int,
    ) -> list[Transaction]:
        with session_scope(self._session_factory) as session:
            stmt = select(TransactionModel)
            if account_id is not None:
                stmt = stmt.where(TransactionModel.account_id == account_id)
            if category is not None:
                stmt = stmt.where(TransactionModel.category == category)
            if transaction_type is not None:
                value = (
                    transaction_type.value
                    if isinstance(transaction_type, TransactionType)
                    else str(transaction_type)
                )
                stmt = stmt.where(TransactionModel.type == value)
            if date_from is not None:
                stmt = stmt.where(TransactionModel.date >= ensure_utc(date_from))
            if date_to is not None:
                stmt = stmt.where(TransactionModel.date <= ensure_utc(date_to))
            if goal_id is not None:
                stmt = stmt.where(TransactionModel.goal_id == goal_id)
            if debt_id is not None:
                stmt = stmt.where(TransactionModel.debt_id == debt_id)
            if subscription_id is not None:
                stmt = stmt.where(TransactionModel.subscription_id == subscription_id)
            if has_subscription is True:
                stmt = stmt.where(TransactionModel.subscription_id.is_not(None))
            elif has_subscription is False:
                stmt = stmt.where(TransactionModel.subscription_id.is_(None))
            if transfer_id is not None:
                stmt = stmt.where(TransactionModel.transfer_id == transfer_id)
            if has_transfer is True:
                stmt = stmt.where(TransactionModel.transfer_id.is_not(None))
            elif has_transfer is False:
                stmt = stmt.where(TransactionModel.transfer_id.is_(None))
            stmt = stmt.order_by(TransactionModel.date.desc())
            if offset:
                stmt = stmt.offset(offset)
            if limit is not None:
                stmt = stmt.limit(limit)
            rows = session.scalars(stmt).all()
            entities = [_to_entity(r) for r in rows]
            if tags:
                required = set(tags)
                entities = [e for e in entities if required.issubset(set(e.tags))]
            return entities
