"""Abstract category repository."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from lib.domain.entities.category import Category, CategoryKind


class CategoryRepository(ABC):
    """Persistence port for :class:`~lib.domain.entities.category.Category`."""

    @abstractmethod
    async def create(self, category: Category) -> Category:
        """Persist a new category."""

    @abstractmethod
    async def update(self, category: Category) -> Category:
        """Update an existing category."""

    @abstractmethod
    async def delete(self, category_id: str) -> bool:
        """Delete a category. Returns ``True`` if removed."""

    @abstractmethod
    async def get_by_id(self, category_id: str) -> Optional[Category]:
        """Fetch by id."""

    @abstractmethod
    async def get_by_name(self, name: str) -> Optional[Category]:
        """Fetch by unique name (case-insensitive)."""

    @abstractmethod
    async def find_or_create(self, category: Category) -> Category:
        """Return existing category by name, or create ``category`` if missing."""

    @abstractmethod
    async def list(
        self,
        *,
        kind: Optional[CategoryKind] = None,
        active_only: bool = True,
    ) -> list[Category]:
        """List categories, optionally filtered by kind."""
