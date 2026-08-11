"""Subscription domain entity."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

from lib.domain.entities.money import quantize_money


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Periodicity(str, Enum):
    """Billing cadence for a recurring subscription."""

    MONTHLY = "monthly"
    YEARLY = "yearly"


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
    next_billing_date: datetime
    is_active: bool = True
    last_charged_at: Optional[datetime] = None
    comment: str = ""
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)

    @field_validator("amount", mode="before")
    @classmethod
    def _quantize_amount(cls, value: object) -> Decimal:
        return quantize_money(value)  # type: ignore[arg-type]

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
