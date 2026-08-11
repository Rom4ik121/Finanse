"""Abstract settings repository."""

from __future__ import annotations

from abc import ABC, abstractmethod

from lib.domain.entities.settings import AppSettings


class SettingsRepository(ABC):
    """Persistence port for :class:`~lib.domain.entities.settings.AppSettings`."""

    @abstractmethod
    async def get(self) -> AppSettings:
        """Return current settings, creating defaults if absent."""

    @abstractmethod
    async def update(self, settings: AppSettings) -> AppSettings:
        """Persist updated settings."""
