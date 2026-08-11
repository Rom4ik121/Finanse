"""Settings use cases."""

from __future__ import annotations

from datetime import datetime, timezone

from lib.domain.entities.settings import AppSettings
from lib.domain.repositories.settings_repository import SettingsRepository


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class GetSettingsUseCase:
    """Load persisted application settings."""

    def __init__(self, settings: SettingsRepository) -> None:
        self._settings = settings

    async def execute(self) -> AppSettings:
        """Return current settings (defaults created if missing)."""
        return await self._settings.get()


class UpdateSettingsUseCase:
    """Persist updated application settings."""

    def __init__(self, settings: SettingsRepository) -> None:
        self._settings = settings

    async def execute(self, settings: AppSettings) -> AppSettings:
        """Save settings and stamp ``updated_at`` in UTC."""
        updated = settings.model_copy(update={"updated_at": _utc_now()})
        return await self._settings.update(updated)
