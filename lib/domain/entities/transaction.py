"""Transaction domain entity."""

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


class TransactionType(str, Enum):
    """Direction of a cash-flow transaction."""

    INCOME = "income"
    EXPENSE = "expense"


class Transaction(BaseModel):
    """A single income or expense entry linked to an account."""

    model_config = ConfigDict(from_attributes=True, use_enum_values=False)

    id: str = Field(default_factory=lambda: str(uuid4()))
    account_id: str
    amount: Decimal
    category: str
    tags: list[str] = Field(default_factory=list)
    date: datetime
    comment: str = ""
    type: TransactionType
    currency: str = "RUB"
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)
    goal_id: Optional[str] = None
    debt_id: Optional[str] = None

    @field_validator("amount", mode="before")
    @classmethod
    def _quantize_amount(cls, value: object) -> Decimal:
        return quantize_money(value)  # type: ignore[arg-type]

    @field_validator("date", "created_at", "updated_at", mode="before")
    @classmethod
    def _ensure_utc(cls, value: object) -> datetime:
        if isinstance(value, datetime):
            if value.tzinfo is None:
                return value.replace(tzinfo=timezone.utc)
            return value.astimezone(timezone.utc)
        raise TypeError("Expected datetime")

    @field_validator("amount")
    @classmethod
    def _positive_amount(cls, value: Decimal) -> Decimal:
        if value <= 0:
            raise ValueError("Transaction amount must be positive")
        return value
