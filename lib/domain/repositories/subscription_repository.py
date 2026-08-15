"""Abstract subscription repository."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional

from lib.domain.entities.subscription import Subscription, SubscriptionStatus


class SubscriptionRepository(ABC):
    """Persistence port for :class:`~lib.domain.entities.subscription.Subscription`."""

    @abstractmethod
    async def create(self, subscription: Subscription) -> Subscription:
        """Persist a new subscription."""

    @abstractmethod
    async def get_by_id(self, subscription_id: str) -> Optional[Subscription]:
        """Fetch a subscription by id."""

    @abstractmethod
    async def update(self, subscription: Subscription) -> Subscription:
        """Update an existing subscription."""

    @abstractmethod
    async def delete(self, subscription_id: str) -> bool:
        """Delete a subscription. Returns ``True`` if removed."""

    @abstractmethod
    async def list(
        self,
        *,
        active_only: bool = False,
        account_id: Optional[str] = None,
        status: Optional[SubscriptionStatus] = None,
    ) -> list[Subscription]:
        """List subscriptions with optional filters."""

    @abstractmethod
    async def list_due(self, as_of: datetime) -> list[Subscription]:
        """Return active subscriptions whose next billing date is on/before ``as_of``."""

    async def list_all(self) -> list[Subscription]:
        """Compatibility helper — list every subscription."""
        return await self.list(active_only=False)
