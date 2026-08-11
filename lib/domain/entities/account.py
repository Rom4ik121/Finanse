"""Account domain entity."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

from lib.domain.entities.money import quantize_money


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Account(BaseModel):
    """A wallet or bank account holding a balance in a single currency."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    currency: str = "RUB"
    balance: Decimal = Decimal("0.00")
    initial_balance: Decimal = Decimal("0.00")
    icon: str = "wallet"
    color: str = "#2E7D32"
    is_active: bool = True
    created_at: datetime = Field(default_factory=_utc_now)

    @field_validator("balance", "initial_balance", mode="before")
    @classmethod
    def _quantize_money_fields(cls, value: object) -> Decimal:
        return quantize_money(value)  # type: ignore[arg-type]

    @field_validator("created_at", mode="before")
    @classmethod
    def _ensure_utc(cls, value: object) -> datetime:
        if isinstance(value, datetime):
            if value.tzinfo is None:
                return value.replace(tzinfo=timezone.utc)
            return value.astimezone(timezone.utc)
        raise TypeError("Expected datetime")
