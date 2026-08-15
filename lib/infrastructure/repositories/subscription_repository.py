"""SQLAlchemy subscription repository."""

from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import select

from lib.domain.entities.subscription import (
    Periodicity,
    Subscription,
    SubscriptionStatus,
)
from lib.domain.repositories.subscription_repository import SubscriptionRepository
from lib.infrastructure.db_models import SubscriptionModel
from lib.infrastructure.repositories._base import SessionFactory, ensure_utc, session_scope

logger = logging.getLogger("finanse.infrastructure.repositories.subscription")


def _to_date(value: object, fallback: Optional[date] = None) -> Optional[date]:
    if value is None:
        return fallback
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return fallback


def _to_entity(model: SubscriptionModel) -> Subscription:
    status_raw = getattr(model, "status", None) or (
        "active" if model.is_active else "paused"
    )
    try:
        status = SubscriptionStatus(status_raw)
    except ValueError:
        status = (
            SubscriptionStatus.ACTIVE if model.is_active else SubscriptionStatus.PAUSED
        )
    start = _to_date(getattr(model, "start_date", None))
    if start is None:
        billed = ensure_utc(model.next_billing_date) or datetime.now(timezone.utc)
        start = billed.date()
    return Subscription(
        id=model.id,
        name=model.name,
        amount=Decimal(str(model.amount)),
        currency=model.currency,
        account_id=model.account_id,
        category=model.category,
        periodicity=Periodicity(model.periodicity),
        custom_interval_days=getattr(model, "custom_interval_days", None),
        start_date=start,
        end_date=_to_date(getattr(model, "end_date", None)),
        max_payments=getattr(model, "max_payments", None),
        payments_made=int(getattr(model, "payments_made", 0) or 0),
        next_billing_date=ensure_utc(model.next_billing_date) or datetime.now(timezone.utc),
        status=status,
        is_active=bool(model.is_active and status == SubscriptionStatus.ACTIVE),
        auto_charge=bool(getattr(model, "auto_charge", True)),
        last_charged_at=ensure_utc(model.last_charged_at),
        last_skip_date=_to_date(getattr(model, "last_skip_date", None)),
        comment=model.comment or "",
        created_at=ensure_utc(model.created_at) or datetime.now(timezone.utc),
        updated_at=ensure_utc(model.updated_at) or datetime.now(timezone.utc),
    )


def _apply_entity(model: SubscriptionModel, entity: Subscription) -> None:
    model.id = entity.id
    model.name = entity.name
    model.amount = entity.amount
    model.currency = entity.currency
    model.account_id = entity.account_id
    model.category = entity.category
    model.periodicity = (
        entity.periodicity.value
        if isinstance(entity.periodicity, Periodicity)
        else str(entity.periodicity)
    )
    model.custom_interval_days = entity.custom_interval_days
    model.start_date = entity.start_date
    model.end_date = entity.end_date
    model.max_payments = entity.max_payments
    model.payments_made = int(entity.payments_made or 0)
    model.next_billing_date = (
        ensure_utc(entity.next_billing_date) or datetime.now(timezone.utc)
    )
    status = (
        entity.status.value
        if isinstance(entity.status, SubscriptionStatus)
        else str(entity.status)
    )
    model.status = status
    model.is_active = status == SubscriptionStatus.ACTIVE.value
    model.auto_charge = bool(entity.auto_charge)
    model.last_charged_at = ensure_utc(entity.last_charged_at)
    model.last_skip_date = entity.last_skip_date
    model.comment = entity.comment or ""
    model.created_at = ensure_utc(entity.created_at) or datetime.now(timezone.utc)
    model.updated_at = ensure_utc(entity.updated_at) or datetime.now(timezone.utc)


class SqlAlchemySubscriptionRepository(SubscriptionRepository):
    """Subscription persistence via SQLAlchemy sync session + ``asyncio.to_thread``."""

    def __init__(self, session_factory: SessionFactory) -> None:
        self._session_factory = session_factory

    async def create(self, subscription: Subscription) -> Subscription:
        return await asyncio.to_thread(self._create_sync, subscription)

    async def update(self, subscription: Subscription) -> Subscription:
        return await asyncio.to_thread(self._update_sync, subscription)

    async def delete(self, subscription_id: str) -> bool:
        return await asyncio.to_thread(self._delete_sync, subscription_id)

    async def get_by_id(self, subscription_id: str) -> Optional[Subscription]:
        return await asyncio.to_thread(self._get_by_id_sync, subscription_id)

    async def list(
        self,
        *,
        active_only: bool = False,
        account_id: Optional[str] = None,
        status: Optional[SubscriptionStatus] = None,
    ) -> list[Subscription]:
        return await asyncio.to_thread(
            self._list_sync, active_only, account_id, None, status
        )

    async def list_due(self, as_of: datetime) -> list[Subscription]:
        return await asyncio.to_thread(
            self._list_sync, True, None, as_of, SubscriptionStatus.ACTIVE
        )

    def _create_sync(self, entity: Subscription) -> Subscription:
        with session_scope(self._session_factory) as session:
            model = SubscriptionModel()
            _apply_entity(model, entity)
            session.add(model)
            session.flush()
            logger.debug("Created subscription %s", model.id)
            return _to_entity(model)

    def _update_sync(self, entity: Subscription) -> Subscription:
        with session_scope(self._session_factory) as session:
            model = session.get(SubscriptionModel, entity.id)
            if model is None:
                raise KeyError(f"Subscription not found: {entity.id}")
            _apply_entity(model, entity)
            model.updated_at = datetime.now(timezone.utc)
            session.flush()
            logger.debug("Updated subscription %s", model.id)
            return _to_entity(model)

    def _delete_sync(self, subscription_id: str) -> bool:
        with session_scope(self._session_factory) as session:
            model = session.get(SubscriptionModel, subscription_id)
            if model is None:
                logger.warning("Delete skipped; subscription not found: %s", subscription_id)
                return False
            session.delete(model)
            logger.debug("Deleted subscription %s", subscription_id)
            return True

    def _get_by_id_sync(self, subscription_id: str) -> Optional[Subscription]:
        with session_scope(self._session_factory) as session:
            model = session.get(SubscriptionModel, subscription_id)
            return _to_entity(model) if model else None

    def _list_sync(
        self,
        active_only: bool,
        account_id: Optional[str],
        due_before: Optional[datetime],
        status: Optional[SubscriptionStatus],
    ) -> list[Subscription]:
        with session_scope(self._session_factory) as session:
            stmt = select(SubscriptionModel)
            if status is not None:
                value = (
                    status.value if isinstance(status, SubscriptionStatus) else str(status)
                )
                stmt = stmt.where(SubscriptionModel.status == value)
            elif active_only:
                stmt = stmt.where(SubscriptionModel.is_active.is_(True))
                # Prefer status when column exists / is populated.
                stmt = stmt.where(SubscriptionModel.status == SubscriptionStatus.ACTIVE.value)
            if account_id is not None:
                stmt = stmt.where(SubscriptionModel.account_id == account_id)
            if due_before is not None:
                stmt = stmt.where(
                    SubscriptionModel.next_billing_date <= ensure_utc(due_before)
                )
            stmt = stmt.order_by(SubscriptionModel.next_billing_date.asc())
            return [_to_entity(r) for r in session.scalars(stmt).all()]
