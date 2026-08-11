"""Savings goal domain entity."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

from lib.domain.entities.money import quantize_money


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Goal(BaseModel):
    """A savings target with optional deadline and priority."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    target_amount: Decimal
    current_amount: Decimal = Decimal("0.00")
    deadline: Optional[datetime] = None
    priority: int = Field(default=3, ge=1, le=5)
    category_link: str = "Накопление"
    is_completed: bool = False
    created_at: datetime = Field(default_factory=_utc_now)

    @field_validator("target_amount", "current_amount", mode="before")
    @classmethod
    def _quantize_money_fields(cls, value: object) -> Decimal:
        return quantize_money(value)  # type: ignore[arg-type]

    @field_validator("deadline", "created_at", mode="before")
    @classmethod
    def _ensure_utc(cls, value: object) -> object:
        if value is None:
            return None
        if isinstance(value, datetime):
            if value.tzinfo is None:
                return value.replace(tzinfo=timezone.utc)
            return value.astimezone(timezone.utc)
        raise TypeError("Expected datetime or None")

    @field_validator("target_amount")
    @classmethod
    def _positive_target(cls, value: Decimal) -> Decimal:
        if value <= 0:
            raise ValueError("Goal target_amount must be positive")
        return value

    @property
    def progress_ratio(self) -> Decimal:
        """Fraction of the target already saved (0–1+)."""
        if self.target_amount == 0:
            return Decimal("0")
        return self.current_amount / self.target_amount
