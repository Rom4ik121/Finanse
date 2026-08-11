"""SQLAlchemy account repository."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import select

from lib.domain.entities.account import Account
from lib.domain.repositories.account_repository import AccountRepository
from lib.infrastructure.db_models import AccountModel
from lib.infrastructure.repositories._base import SessionFactory, ensure_utc, session_scope

logger = logging.getLogger("finanse.infrastructure.repositories.account")


def _to_entity(model: AccountModel) -> Account:
    return Account(
        id=model.id,
        name=model.name,
        currency=model.currency,
        balance=Decimal(str(model.balance)),
        initial_balance=Decimal(str(model.initial_balance)),
        icon=model.icon,
        color=model.color,
        is_active=model.is_active,
        created_at=ensure_utc(model.created_at) or datetime.now(timezone.utc),
    )


def _apply_entity(model: AccountModel, entity: Account) -> None:
    model.id = entity.id
    model.name = entity.name
    model.currency = entity.currency
    model.balance = entity.balance
    model.initial_balance = entity.initial_balance
    model.icon = entity.icon
    model.color = entity.color
    model.is_active = entity.is_active
    model.created_at = ensure_utc(entity.created_at) or datetime.now(timezone.utc)


class SqlAlchemyAccountRepository(AccountRepository):
    """Account persistence via SQLAlchemy sync session + ``asyncio.to_thread``."""

    def __init__(self, session_factory: SessionFactory) -> None:
        self._session_factory = session_factory

    async def create(self, account: Account) -> Account:
        return await asyncio.to_thread(self._create_sync, account)

    async def update(self, account: Account) -> Account:
        return await asyncio.to_thread(self._update_sync, account)

    async def delete(self, account_id: str) -> bool:
        return await asyncio.to_thread(self._delete_sync, account_id)

    async def get_by_id(self, account_id: str) -> Optional[Account]:
        return await asyncio.to_thread(self._get_by_id_sync, account_id)

    async def list(self, *, active_only: bool = False) -> list[Account]:
        return await asyncio.to_thread(self._list_sync, active_only)

    def _create_sync(self, entity: Account) -> Account:
        with session_scope(self._session_factory) as session:
            model = AccountModel()
            _apply_entity(model, entity)
            session.add(model)
            session.flush()
            logger.debug("Created account %s", model.id)
            return _to_entity(model)

    def _update_sync(self, entity: Account) -> Account:
        with session_scope(self._session_factory) as session:
            model = session.get(AccountModel, entity.id)
            if model is None:
                raise KeyError(f"Account not found: {entity.id}")
            _apply_entity(model, entity)
            session.flush()
            logger.debug("Updated account %s", model.id)
            return _to_entity(model)

    def _delete_sync(self, account_id: str) -> bool:
        with session_scope(self._session_factory) as session:
            model = session.get(AccountModel, account_id)
            if model is None:
                logger.warning("Delete skipped; account not found: %s", account_id)
                return False
            session.delete(model)
            logger.debug("Deleted account %s", account_id)
            return True

    def _get_by_id_sync(self, account_id: str) -> Optional[Account]:
        with session_scope(self._session_factory) as session:
            model = session.get(AccountModel, account_id)
            return _to_entity(model) if model else None

    def _list_sync(self, active_only: bool) -> list[Account]:
        with session_scope(self._session_factory) as session:
            stmt = select(AccountModel)
            if active_only:
                stmt = stmt.where(AccountModel.is_active.is_(True))
            stmt = stmt.order_by(AccountModel.name)
            return [_to_entity(r) for r in session.scalars(stmt).all()]
