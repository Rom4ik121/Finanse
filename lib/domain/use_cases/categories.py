"""Category CRUD and find-or-create use cases."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from lib.domain.entities.category import Category, CategoryKind
from lib.domain.repositories.budget_repository import BudgetRepository
from lib.domain.repositories.category_repository import CategoryRepository


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ListCategoriesUseCase:
    """List categories for pickers / filters."""

    def __init__(self, categories: CategoryRepository) -> None:
        self._categories = categories

    async def execute(
        self,
        *,
        kind: Optional[CategoryKind] = None,
        active_only: bool = True,
        for_type: Optional[str] = None,
    ) -> list[Category]:
        items = await self._categories.list(kind=kind, active_only=active_only)
        if for_type:
            items = [c for c in items if c.matches_type(for_type)]
        return sorted(items, key=lambda c: c.name.lower())


class CreateCategoryUseCase:
    """Create a user category (unique name)."""

    def __init__(self, categories: CategoryRepository) -> None:
        self._categories = categories

    async def execute(self, category: Category) -> Category:
        existing = await self._categories.get_by_name(category.name)
        if existing is not None:
            raise ValueError(f"Category already exists: {category.name}")
        return await self._categories.create(category)


class UpdateCategoryUseCase:
    """Update category name / icon / color / kind."""

    def __init__(
        self,
        categories: CategoryRepository,
        budgets: Optional[BudgetRepository] = None,
    ) -> None:
        self._categories = categories
        self._budgets = budgets

    async def execute(self, category: Category) -> Category:
        previous = await self._categories.get_by_id(category.id)
        category = category.model_copy(update={"updated_at": _utc_now()})
        clash = await self._categories.get_by_name(category.name)
        if clash is not None and clash.id != category.id:
            raise ValueError(f"Category already exists: {category.name}")
        saved = await self._categories.update(category)
        if (
            self._budgets is not None
            and previous is not None
            and previous.name != saved.name
        ):
            await self._budgets.reassign_category(previous.name, saved.name)
        return saved


class DeleteCategoryUseCase:
    """Delete a non-system category."""

    def __init__(
        self,
        categories: CategoryRepository,
        budgets: Optional[BudgetRepository] = None,
    ) -> None:
        self._categories = categories
        self._budgets = budgets

    async def execute(self, category_id: str) -> bool:
        existing = await self._categories.get_by_id(category_id)
        if existing is None:
            return False
        if existing.is_system:
            raise ValueError("System categories cannot be deleted")
        if self._budgets is not None:
            await self._budgets.delete_for_category(existing.name)
        return await self._categories.delete(category_id)


class FindOrCreateCategoryUseCase:
    """Resolve a category name, creating it when missing."""

    def __init__(self, categories: CategoryRepository) -> None:
        self._categories = categories

    async def execute(
        self,
        name: str,
        *,
        kind: CategoryKind = CategoryKind.BOTH,
        icon: str = "category",
        color: str = "#00897B",
    ) -> Category:
        text = (name or "").strip()
        if not text:
            raise ValueError("Category name is required")
        try:
            return await self._categories.find_or_create(
                Category(
                    name=text,
                    kind=kind,
                    icon=icon,
                    color=color,
                    is_system=False,
                )
            )
        except Exception:
            # UNIQUE race or concurrent save — reuse the row that already exists.
            existing = await self._categories.get_by_name(text)
            if existing is not None:
                return existing
            raise
