"""Subscription domain entity."""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from lib.domain.entities.money import quantize_money


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _today_utc() -> date:
    return datetime.now(timezone.utc).date()


class Periodicity(str, Enum):
    """Billing cadence for a recurring subscription."""

    DAILY = "daily"
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    SEMI_ANNUAL = "semi-annual"
    YEARLY = "yearly"
    CUSTOM = "custom"


class SubscriptionStatus(str, Enum):
    """Lifecycle status of a subscription."""

    ACTIVE = "active"
    PAUSED = "paused"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class Subscription(BaseModel):
    """A recurring charge linked to an account."""

    model_config = ConfigDict(from_attributes=True, use_enum_values=False)

    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    amount: Decimal
    currency: str = "RUB"
    account_id: str
    category: str = "Прочее"
    periodicity: Periodicity = Periodicity.MONTHLY
    custom_interval_days: Optional[int] = None
    start_date: date = Field(default_factory=_today_utc)
    end_date: Optional[date] = None
    max_payments: Optional[int] = None
    payments_made: int = 0
    next_billing_date: datetime
    status: SubscriptionStatus = SubscriptionStatus.ACTIVE
    is_active: bool = True
    auto_charge: bool = True
    last_charged_at: Optional[datetime] = None
    last_skip_date: Optional[date] = None
    comment: str = ""
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)

    @field_validator("amount", mode="before")
    @classmethod
    def _quantize_amount(cls, value: object) -> Decimal:
        return quantize_money(value)  # type: ignore[arg-type]

    @field_validator("custom_interval_days", "max_payments", "payments_made", mode="before")
    @classmethod
    def _non_negative_int(cls, value: object) -> object:
        if value is None:
            return None
        number = int(value)
        if number < 0:
            raise ValueError("Value must be non-negative")
        return number

    @field_validator(
        "next_billing_date",
        "last_charged_at",
        "created_at",
        "updated_at",
        mode="before",
    )
    @classmethod
    def _ensure_utc(cls, value: object) -> object:
        if value is None:
            return None
        if isinstance(value, datetime):
            if value.tzinfo is None:
                return value.replace(tzinfo=timezone.utc)
            return value.astimezone(timezone.utc)
        raise TypeError("Expected datetime or None")

    @model_validator(mode="after")
    def _sync_status_and_active(self) -> "Subscription":
        """Keep ``is_active`` aligned with ``status`` (source of truth)."""
        if self.status == SubscriptionStatus.ACTIVE:
            object.__setattr__(self, "is_active", True)
        else:
            object.__setattr__(self, "is_active", False)
        if (
            self.periodicity == Periodicity.CUSTOM
            and (self.custom_interval_days is None or self.custom_interval_days < 1)
        ):
            raise ValueError("custom_interval_days is required for custom periodicity")
        return self
