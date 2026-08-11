"""Generic repository ABC."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Generic, Optional, TypeVar

T = TypeVar("T")
ID = TypeVar("ID", bound=str)


class Repository(ABC, Generic[T, ID]):
    """Async CRUD contract for domain aggregates."""

    @abstractmethod
    async def create(self, entity: T) -> T:
        """Persist a new entity and return it."""

    @abstractmethod
    async def update(self, entity: T) -> T:
        """Update an existing entity and return it."""

    @abstractmethod
    async def delete(self, id: ID) -> None:
        """Delete an entity by identifier."""

    @abstractmethod
    async def get_by_id(self, id: ID) -> Optional[T]:
        """Fetch a single entity or ``None``."""

    @abstractmethod
    async def list_all(self) -> list[T]:
        """Return all entities."""
