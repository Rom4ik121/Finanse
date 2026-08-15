"""Abstract goal repository."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from lib.domain.entities.goal import Goal, GoalStatus


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
        status: Optional[GoalStatus | str] = None,
        include_completed: bool = True,
        currency: Optional[str] = None,
        min_priority: Optional[int] = None,
        sort_by: str = "priority",
    ) -> list[Goal]:
        """List goals with optional status/currency filters and sorting.

        ``sort_by``: ``priority`` | ``deadline`` | ``progress`` | ``created_at``.
        When ``status`` is set it takes precedence over ``include_completed``.
        """

    async def list_all(self) -> list[Goal]:
        """Compatibility helper — list every goal."""
        return await self.list(include_completed=True)

    async def list_active(self) -> list[Goal]:
        """Compatibility helper — active (incomplete) goals only."""
        return await self.list(status=GoalStatus.ACTIVE)

    async def list_completed(self) -> list[Goal]:
        """Compatibility helper — completed goals only."""
        return await self.list(status=GoalStatus.COMPLETED)
