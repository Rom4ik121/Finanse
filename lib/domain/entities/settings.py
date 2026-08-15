"""Application settings domain model."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from lib.core.config import (
    DEFAULT_CURRENCY,
    DEFAULT_EXCHANGE_UPDATE_INTERVAL_MINUTES,
    DEFAULT_LANGUAGE,
    DEFAULT_THEME,
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AppSettings(BaseModel):
    """Persisted user preferences for the application."""

    model_config = ConfigDict(from_attributes=True)

    id: str = "default"
    default_currency: str = DEFAULT_CURRENCY
    theme: str = DEFAULT_THEME
    language: str = DEFAULT_LANGUAGE
    exchange_update_interval_minutes: int = DEFAULT_EXCHANGE_UPDATE_INTERVAL_MINUTES
    notifications_enabled: bool = True
    subscription_reminders: bool = True
    debt_reminders: bool = True
    goal_milestones: bool = True
    low_balance_threshold: Optional[float] = None
    reminder_time: str = "09:00"  # local HH:MM for daily reminder sweep
    reminder_days: int = 3  # days before subscription billing to remind
    check_balance_before_subscription: bool = True
    biometric_enabled: bool = False
    updated_at: datetime = Field(default_factory=_utc_now)

    @field_validator("reminder_days")
    @classmethod
    def _validate_reminder_days(cls, value: int) -> int:
        days = int(value)
        if days < 0 or days > 365:
            raise ValueError("reminder_days must be between 0 and 365")
        return days

    @field_validator("reminder_time")
    @classmethod
    def _validate_reminder_time(cls, value: str) -> str:
        text = (value or "09:00").strip()
        parts = text.split(":")
        if len(parts) != 2:
            raise ValueError("reminder_time must be HH:MM")
        hour, minute = int(parts[0]), int(parts[1])
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError("reminder_time out of range")
        return f"{hour:02d}:{minute:02d}"

    @field_validator("default_currency")
    @classmethod
    def _upper_currency(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("updated_at", mode="before")
    @classmethod
    def _ensure_utc(cls, value: object) -> datetime:
        if isinstance(value, datetime):
            if value.tzinfo is None:
                return value.replace(tzinfo=timezone.utc)
            return value.astimezone(timezone.utc)
        raise TypeError("Expected datetime")
