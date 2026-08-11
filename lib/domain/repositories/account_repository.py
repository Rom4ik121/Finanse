"""Abstract account repository."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from lib.domain.entities.account import Account


class AccountRepository(ABC):
    """Persistence port for :class:`~lib.domain.entities.account.Account`."""

    @abstractmethod
    async def create(self, account: Account) -> Account:
        """Persist a new account."""

    @abstractmethod
    async def get_by_id(self, account_id: str) -> Optional[Account]:
        """Fetch an account by id."""

    @abstractmethod
    async def update(self, account: Account) -> Account:
        """Update an existing account."""

    @abstractmethod
    async def delete(self, account_id: str) -> bool:
        """Delete an account. Returns ``True`` if removed."""

    @abstractmethod
    async def list(self, *, active_only: bool = False) -> list[Account]:
        """List accounts, optionally filtering inactive ones."""

    async def list_all(self) -> list[Account]:
        """Compatibility helper — list every account."""
        return await self.list(active_only=False)

    async def list_active(self) -> list[Account]:
        """Compatibility helper — list active accounts only."""
        return await self.list(active_only=True)
