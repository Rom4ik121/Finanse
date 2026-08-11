"""Currency and exchange-rate domain entities."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

from lib.domain.entities.money import quantize_rate


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Currency(BaseModel):
    """A fiat or crypto currency definition."""

    model_config = ConfigDict(from_attributes=True)

    code: str  # ISO-like code, e.g. RUB, USD, BTC
    name: str
    symbol: str
    is_crypto: bool = False

    @field_validator("code")
    @classmethod
    def _upper_code(cls, value: str) -> str:
        return value.strip().upper()


class ExchangeRate(BaseModel):
    """Quoted exchange rate: ``1 base = rate quote``."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(default_factory=lambda: str(uuid4()))
    base: str
    quote: str
    rate: Decimal
    updated_at: datetime = Field(default_factory=_utc_now)

    @field_validator("base", "quote")
    @classmethod
    def _upper_codes(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("rate", mode="before")
    @classmethod
    def _quantize_rate_field(cls, value: object) -> Decimal:
        # Prefer high precision; callers may pass crypto flag via model_validate later.
        return quantize_rate(value, crypto=True)  # type: ignore[arg-type]

    @field_validator("updated_at", mode="before")
    @classmethod
    def _ensure_utc(cls, value: object) -> datetime:
        if isinstance(value, datetime):
            if value.tzinfo is None:
                return value.replace(tzinfo=timezone.utc)
            return value.astimezone(timezone.utc)
        raise TypeError("Expected datetime")

    @field_validator("rate")
    @classmethod
    def _positive_rate(cls, value: Decimal) -> Decimal:
        if value <= 0:
            raise ValueError("Exchange rate must be positive")
        return value
