"""Abstract debt repository."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from lib.domain.entities.debt import Debt, DebtDirection, DebtStatus


class DebtRepository(ABC):
    """Persistence port for :class:`~lib.domain.entities.debt.Debt`."""

    @abstractmethod
    async def create(self, debt: Debt) -> Debt:
        """Persist a new debt."""

    @abstractmethod
    async def get_by_id(self, debt_id: str) -> Optional[Debt]:
        """Fetch a debt by id."""

    @abstractmethod
    async def update(self, debt: Debt) -> Debt:
        """Update an existing debt."""

    @abstractmethod
    async def delete(self, debt_id: str) -> bool:
        """Delete a debt. Returns ``True`` if removed."""

    @abstractmethod
    async def list(
        self,
        *,
        status: Optional[DebtStatus | str] = None,
        direction: Optional[DebtDirection | str] = None,
        currency: Optional[str] = None,
        sort_by: str = "due_date",
    ) -> list[Debt]:
        """List debts with optional filters and sorting.

        ``sort_by``: ``due_date`` | ``remaining`` | ``amount`` | ``interest`` |
        ``created_at`` | ``counterparty`` | ``status``.
        """

    async def list_all(self) -> list[Debt]:
        """Compatibility helper — list every debt."""
        return await self.list()
