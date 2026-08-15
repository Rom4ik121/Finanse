"""Monthly category budget domain entity."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

from lib.domain.entities.money import quantize_money


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Budget(BaseModel):
    """A monthly spending limit for one expense category (in base currency)."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(default_factory=lambda: str(uuid4()))
    category_id: str
    month: int
    year: int
    amount_limit: Decimal
    spent: Decimal = Decimal("0.00")
    last_alert_level: int = 0
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)

    @field_validator("category_id")
    @classmethod
    def _strip_category(cls, value: str) -> str:
        text = (value or "").strip()
        if not text:
            raise ValueError("Budget category_id is required")
        return text

    @field_validator("month")
    @classmethod
    def _valid_month(cls, value: int) -> int:
        month = int(value)
        if month < 1 or month > 12:
            raise ValueError("Budget month must be between 1 and 12")
        return month

    @field_validator("year")
    @classmethod
    def _valid_year(cls, value: int) -> int:
        year = int(value)
        if year < 1970 or year > 2100:
            raise ValueError("Budget year is out of range")
        return year

    @field_validator("amount_limit", "spent", mode="before")
    @classmethod
    def _quantize_money_fields(cls, value: object) -> Decimal:
        return quantize_money(value)  # type: ignore[arg-type]

    @field_validator("amount_limit")
    @classmethod
    def _positive_limit(cls, value: Decimal) -> Decimal:
        if value <= 0:
            raise ValueError("Budget amount_limit must be positive")
        return value

    @field_validator("spent")
    @classmethod
    def _non_negative_spent(cls, value: Decimal) -> Decimal:
        if value < 0:
            return Decimal("0.00")
        return value

    @field_validator("last_alert_level")
    @classmethod
    def _valid_alert_level(cls, value: int) -> int:
        level = int(value or 0)
        if level not in (0, 80, 100):
            return 0
        return level

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def _ensure_utc(cls, value: object) -> datetime:
        if isinstance(value, datetime):
            if value.tzinfo is None:
                return value.replace(tzinfo=timezone.utc)
            return value.astimezone(timezone.utc)
        raise TypeError("Expected datetime")

    @property
    def percent_used(self) -> Decimal:
        """Usage as a percentage of the limit (0–100+)."""
        if self.amount_limit <= 0:
            return Decimal("0")
        return (self.spent / self.amount_limit) * Decimal("100")

    @property
    def remaining(self) -> Decimal:
        """Unused limit (never negative)."""
        left = self.amount_limit - self.spent
        return quantize_money(left if left > 0 else Decimal("0"))

    @property
    def is_over_budget(self) -> bool:
        return self.spent > self.amount_limit


class BudgetProgress(BaseModel):
    """Budget snapshot with computed progress fields for UI / notifications."""

    budget: Budget
    limit: Decimal
    spent: Decimal
    remaining: Decimal
    percent: Decimal
    is_over_budget: bool
    category_id: str
    month: int
    year: int

    @classmethod
    def from_budget(cls, budget: Budget) -> "BudgetProgress":
        percent = budget.percent_used.quantize(Decimal("0.01"))
        return cls(
            budget=budget,
            limit=budget.amount_limit,
            spent=budget.spent,
            remaining=budget.remaining,
            percent=percent,
            is_over_budget=budget.is_over_budget,
            category_id=budget.category_id,
            month=budget.month,
            year=budget.year,
        )
