"""SQLAlchemy goal repository."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import select

from lib.domain.entities.goal import Goal
from lib.domain.repositories.goal_repository import GoalRepository
from lib.infrastructure.db_models import GoalModel
from lib.infrastructure.repositories._base import SessionFactory, ensure_utc, session_scope

logger = logging.getLogger("finanse.infrastructure.repositories.goal")


def _to_entity(model: GoalModel) -> Goal:
    return Goal(
        id=model.id,
        name=model.name,
        target_amount=Decimal(str(model.target_amount)),
        current_amount=Decimal(str(model.current_amount)),
        deadline=ensure_utc(model.deadline),
        priority=model.priority,
        category_link=model.category_link,
        is_completed=model.is_completed,
        created_at=ensure_utc(model.created_at) or datetime.now(timezone.utc),
    )


def _apply_entity(model: GoalModel, entity: Goal) -> None:
    model.id = entity.id
    model.name = entity.name
    model.target_amount = entity.target_amount
    model.current_amount = entity.current_amount
    model.deadline = ensure_utc(entity.deadline)
    model.priority = entity.priority
    model.category_link = entity.category_link
    model.is_completed = entity.is_completed
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
        include_completed: bool = True,
        min_priority: Optional[int] = None,
    ) -> list[Goal]:
        return await asyncio.to_thread(self._list_sync, include_completed, min_priority)

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
        include_completed: bool,
        min_priority: Optional[int],
    ) -> list[Goal]:
        with session_scope(self._session_factory) as session:
            stmt = select(GoalModel)
            if not include_completed:
                stmt = stmt.where(GoalModel.is_completed.is_(False))
            if min_priority is not None:
                stmt = stmt.where(GoalModel.priority >= min_priority)
            stmt = stmt.order_by(GoalModel.priority.asc(), GoalModel.name)
            return [_to_entity(r) for r in session.scalars(stmt).all()]
