"""Abstract goal repository."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from lib.domain.entities.goal import Goal


class GoalRepository(ABC):
    """Persistence port for :class:`~lib.domain.entities.goal.Goal`."""

    @abstractmethod
    async def create(self, goal: Goal) -> Goal:
        """Persist a new goal."""

    @abstractmethod
    async def get_by_id(self, goal_id: str) -> Optional[Goal]:
        """Fetch a goal by id."""

    @abstractmethod
    async def update(self, goal: Goal) -> Goal:
        """Update an existing goal."""

    @abstractmethod
    async def delete(self, goal_id: str) -> bool:
        """Delete a goal. Returns ``True`` if removed."""

    @abstractmethod
    async def list(
        self,
        *,
        include_completed: bool = True,
        min_priority: Optional[int] = None,
    ) -> list[Goal]:
        """List goals with optional filters."""

    async def list_all(self) -> list[Goal]:
        """Compatibility helper — list every goal."""
        return await self.list(include_completed=True)

    async def list_active(self) -> list[Goal]:
        """Compatibility helper — incomplete goals only."""
        return await self.list(include_completed=False)

    async def list_completed(self) -> list[Goal]:
        """Compatibility helper — completed goals only."""
        goals = await self.list(include_completed=True)
        return [g for g in goals if g.is_completed]
