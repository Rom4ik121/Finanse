"""Abstract transaction repository."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional, Sequence

from lib.domain.entities.transaction import Transaction, TransactionType


class TransactionRepository(ABC):
    """Persistence port for :class:`~lib.domain.entities.transaction.Transaction`."""

    @abstractmethod
    async def create(self, transaction: Transaction) -> Transaction:
        """Persist a new transaction."""

    @abstractmethod
    async def get_by_id(self, transaction_id: str) -> Optional[Transaction]:
        """Fetch a transaction by id, or ``None`` if missing."""

    @abstractmethod
    async def update(self, transaction: Transaction) -> Transaction:
        """Update an existing transaction."""

    @abstractmethod
    async def delete(self, transaction_id: str) -> bool:
        """Delete a transaction. Returns ``True`` if a row was removed."""

    @abstractmethod
    async def list(
        self,
        *,
        account_id: Optional[str] = None,
        category: Optional[str] = None,
        transaction_type: Optional[TransactionType] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        tags: Optional[Sequence[str]] = None,
        goal_id: Optional[str] = None,
        debt_id: Optional[str] = None,
        subscription_id: Optional[str] = None,
        has_subscription: Optional[bool] = None,
        transfer_id: Optional[str] = None,
        has_transfer: Optional[bool] = None,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> list[Transaction]:
        """List transactions with optional filters."""

    async def list_by_account(self, account_id: str) -> list[Transaction]:
        """Return all transactions for an account."""
        return await self.list(account_id=account_id)

    async def list_all(self) -> list[Transaction]:
        """Compatibility helper — list every transaction."""
        return await self.list()
