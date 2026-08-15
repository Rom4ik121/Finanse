"""SQLAlchemy goal repository."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import select

from lib.domain.entities.goal import Goal, GoalStatus
from lib.domain.repositories.goal_repository import GoalRepository
from lib.infrastructure.db_models import GoalModel
from lib.infrastructure.repositories._base import SessionFactory, ensure_utc, session_scope

logger = logging.getLogger("finanse.infrastructure.repositories.goal")


def _to_entity(model: GoalModel) -> Goal:
    status_raw = getattr(model, "status", None)
    if not status_raw:
        status_raw = (
            GoalStatus.COMPLETED.value
            if model.is_completed
            else GoalStatus.ACTIVE.value
        )
    cached = getattr(model, "cached_projection", None)
    return Goal(
        id=model.id,
        name=model.name,
        target_amount=Decimal(str(model.target_amount)),
        current_amount=Decimal(str(model.current_amount)),
        currency=getattr(model, "currency", None) or "RUB",
        deadline=ensure_utc(model.deadline),
        priority=model.priority,
        category_link=model.category_link,
        status=status_raw,
        is_completed=model.is_completed,
        cached_projection=dict(cached) if isinstance(cached, dict) else cached,
        created_at=ensure_utc(model.created_at) or datetime.now(timezone.utc),
    )


def _apply_entity(model: GoalModel, entity: Goal) -> None:
    model.id = entity.id
    model.name = entity.name
    model.target_amount = entity.target_amount
    model.current_amount = entity.current_amount
    model.currency = entity.currency
    model.deadline = ensure_utc(entity.deadline)
    model.priority = entity.priority
    model.category_link = entity.category_link
    status = entity.status
    if isinstance(status, GoalStatus):
        model.status = status.value
    else:
        model.status = str(status)
    model.is_completed = bool(entity.is_completed)
    model.cached_projection = entity.cached_projection
    model.created_at = ensure_utc(entity.created_at) or datetime.now(timezone.utc)


class SqlAlchemyGoalRepository(GoalRepository):
    """Goal persistence via SQLAlchemy sync session + ``asyncio.to_thread``."""

    def __init__(self, session_factory: SessionFactory) -> None:
        self._session_factory = session_factory

    async def create(self, goal: Goal) -> Goal:
        return await asyncio.to_thread(self._create_sync, goal)

    async def update(self, goal: Goal) -> Goal:
        return await asyncio.to_thread(self._update_sync, goal)

    async def delete(self, goal_id: str) -> bool:
        return await asyncio.to_thread(self._delete_sync, goal_id)

    async def get_by_id(self, goal_id: str) -> Optional[Goal]:
        return await asyncio.to_thread(self._get_by_id_sync, goal_id)

    async def list(
        self,
        *,
        status: Optional[GoalStatus | str] = None,
        include_completed: bool = True,
        currency: Optional[str] = None,
        min_priority: Optional[int] = None,
        sort_by: str = "priority",
    ) -> list[Goal]:
        return await asyncio.to_thread(
            self._list_sync,
            status,
            include_completed,
            currency,
            min_priority,
            sort_by,
        )

    def _create_sync(self, entity: Goal) -> Goal:
        with session_scope(self._session_factory) as session:
            model = GoalModel()
            _apply_entity(model, entity)
            session.add(model)
            session.flush()
            logger.debug("Created goal %s", model.id)
            return _to_entity(model)

    def _update_sync(self, entity: Goal) -> Goal:
        with session_scope(self._session_factory) as session:
            model = session.get(GoalModel, entity.id)
            if model is None:
                raise KeyError(f"Goal not found: {entity.id}")
            _apply_entity(model, entity)
            session.flush()
            logger.debug("Updated goal %s", model.id)
            return _to_entity(model)

    def _delete_sync(self, goal_id: str) -> bool:
        with session_scope(self._session_factory) as session:
            model = session.get(GoalModel, goal_id)
            if model is None:
                logger.warning("Delete skipped; goal not found: %s", goal_id)
                return False
            session.delete(model)
            logger.debug("Deleted goal %s", goal_id)
            return True

    def _get_by_id_sync(self, goal_id: str) -> Optional[Goal]:
        with session_scope(self._session_factory) as session:
            model = session.get(GoalModel, goal_id)
            return _to_entity(model) if model else None

    def _list_sync(
        self,
        status: Optional[GoalStatus | str],
        include_completed: bool,
        currency: Optional[str],
        min_priority: Optional[int],
        sort_by: str,
    ) -> list[Goal]:
        with session_scope(self._session_factory) as session:
            stmt = select(GoalModel)
            if status is not None:
                value = status.value if isinstance(status, GoalStatus) else str(status)
                stmt = stmt.where(GoalModel.status == value)
            elif not include_completed:
                stmt = stmt.where(GoalModel.status == GoalStatus.ACTIVE.value)
            if currency is not None:
                stmt = stmt.where(GoalModel.currency == currency.upper())
            if min_priority is not None:
                stmt = stmt.where(GoalModel.priority >= min_priority)

            entities = [_to_entity(r) for r in session.scalars(stmt).all()]
            return _sort_goals(entities, sort_by)


def _sort_goals(goals: list[Goal], sort_by: str) -> list[Goal]:
    key = (sort_by or "priority").lower()
    if key == "deadline":
        far = datetime.max.replace(tzinfo=timezone.utc)

        def _deadline_key(g: Goal) -> Any:
            return (g.deadline is None, g.deadline or far, -g.priority, g.name)

        return sorted(goals, key=_deadline_key)
    if key == "progress":
        return sorted(
            goals,
            key=lambda g: (float(g.progress_ratio), -g.priority, g.name),
        )
    if key == "created_at":
        return sorted(
            goals,
            key=lambda g: (g.created_at, g.name),
            reverse=True,
        )
    # priority desc (5 first), then name
    return sorted(goals, key=lambda g: (-g.priority, g.name))
