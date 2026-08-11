"""SQLAlchemy category repository."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from lib.domain.entities.category import Category, CategoryKind
from lib.domain.repositories.category_repository import CategoryRepository
from lib.infrastructure.db_models import CategoryModel
from lib.infrastructure.repositories._base import SessionFactory, ensure_utc, session_scope

logger = logging.getLogger("finanse.infrastructure.repositories.category")


def _to_entity(model: CategoryModel) -> Category:
    return Category(
        id=model.id,
        name=model.name,
        icon=model.icon,
        color=model.color,
        kind=CategoryKind(model.kind),
        is_system=bool(model.is_system),
        is_active=bool(model.is_active),
        created_at=ensure_utc(model.created_at) or datetime.now(timezone.utc),
        updated_at=ensure_utc(model.updated_at) or datetime.now(timezone.utc),
    )


def _apply_entity(model: CategoryModel, entity: Category) -> None:
    model.id = entity.id
    model.name = entity.name
    model.icon = entity.icon
    model.color = entity.color
    model.kind = entity.kind.value if isinstance(entity.kind, CategoryKind) else str(entity.kind)
    model.is_system = entity.is_system
    model.is_active = entity.is_active
    model.created_at = ensure_utc(entity.created_at) or datetime.now(timezone.utc)
    model.updated_at = ensure_utc(entity.updated_at) or datetime.now(timezone.utc)


def _name_matches(stored: str, needle: str) -> bool:
    """Case-insensitive match that works for Cyrillic (SQLite LOWER is ASCII-only)."""
    return stored == needle or stored.casefold() == needle.casefold()


class SqlAlchemyCategoryRepository(CategoryRepository):
    """Category persistence via SQLAlchemy sync session + ``asyncio.to_thread``."""

    def __init__(self, session_factory: SessionFactory) -> None:
        self._session_factory = session_factory

    async def create(self, category: Category) -> Category:
        return await asyncio.to_thread(self._create_sync, category)

    async def update(self, category: Category) -> Category:
        return await asyncio.to_thread(self._update_sync, category)

    async def delete(self, category_id: str) -> bool:
        return await asyncio.to_thread(self._delete_sync, category_id)

    async def get_by_id(self, category_id: str) -> Optional[Category]:
        return await asyncio.to_thread(self._get_by_id_sync, category_id)

    async def get_by_name(self, name: str) -> Optional[Category]:
        return await asyncio.to_thread(self._get_by_name_sync, name)

    async def find_or_create(self, category: Category) -> Category:
        return await asyncio.to_thread(self._find_or_create_sync, category)

    async def list(
        self,
        *,
        kind: Optional[CategoryKind] = None,
        active_only: bool = True,
    ) -> list[Category]:
        return await asyncio.to_thread(self._list_sync, kind, active_only)

    def _create_sync(self, entity: Category) -> Category:
        try:
            with session_scope(self._session_factory) as session:
                model = CategoryModel()
                _apply_entity(model, entity)
                session.add(model)
                session.flush()
                logger.debug("Created category %s", model.name)
                return _to_entity(model)
        except IntegrityError:
            # Duplicate name (race or Unicode case): return the existing row.
            existing = self._get_by_name_sync(entity.name)
            if existing is not None:
                return existing
            raise

    def _update_sync(self, entity: Category) -> Category:
        with session_scope(self._session_factory) as session:
            model = session.get(CategoryModel, entity.id)
            if model is None:
                raise ValueError(f"Category not found: {entity.id}")
            _apply_entity(model, entity)
            session.flush()
            return _to_entity(model)

    def _delete_sync(self, category_id: str) -> bool:
        with session_scope(self._session_factory) as session:
            model = session.get(CategoryModel, category_id)
            if model is None:
                return False
            session.delete(model)
            session.flush()
            return True

    def _get_by_id_sync(self, category_id: str) -> Optional[Category]:
        with session_scope(self._session_factory) as session:
            model = session.get(CategoryModel, category_id)
            return _to_entity(model) if model else None

    def _get_by_name_sync(self, name: str) -> Optional[Category]:
        needle = (name or "").strip()
        if not needle:
            return None
        with session_scope(self._session_factory) as session:
            # Prefer exact match, then Unicode-aware casefold (SQLite LOWER is ASCII-only).
            rows = session.execute(select(CategoryModel)).scalars().all()
            exact = next((row for row in rows if row.name == needle), None)
            if exact is not None:
                return _to_entity(exact)
            folded = next(
                (row for row in rows if _name_matches(row.name, needle)),
                None,
            )
            return _to_entity(folded) if folded is not None else None

    def _find_or_create_sync(self, entity: Category) -> Category:
        existing = self._get_by_name_sync(entity.name)
        if existing is not None:
            return existing
        return self._create_sync(entity)

    def _list_sync(
        self,
        kind: Optional[CategoryKind],
        active_only: bool,
    ) -> list[Category]:
        with session_scope(self._session_factory) as session:
            stmt = select(CategoryModel)
            if active_only:
                stmt = stmt.where(CategoryModel.is_active.is_(True))
            if kind is not None:
                # Include BOTH when filtering by income/expense.
                if kind in (CategoryKind.INCOME, CategoryKind.EXPENSE):
                    stmt = stmt.where(
                        CategoryModel.kind.in_([kind.value, CategoryKind.BOTH.value])
                    )
                else:
                    stmt = stmt.where(CategoryModel.kind == kind.value)
            stmt = stmt.order_by(CategoryModel.name.asc())
            rows = session.execute(stmt).scalars().all()
            return [_to_entity(m) for m in rows]
