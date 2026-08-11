"""User-defined transaction category."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class CategoryKind(str, Enum):
    """Which transaction types a category applies to."""

    EXPENSE = "expense"
    INCOME = "income"
    BOTH = "both"


class Category(BaseModel):
    """Named category with icon and color for income / expense."""

    model_config = ConfigDict(from_attributes=True, use_enum_values=False)

    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    icon: str = "category"
    color: str = "#00897B"
    kind: CategoryKind = CategoryKind.BOTH
    is_system: bool = False
    is_active: bool = True
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)

    @field_validator("name")
    @classmethod
    def _strip_name(cls, value: str) -> str:
        text = (value or "").strip()
        if not text:
            raise ValueError("Category name is required")
        return text

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def _ensure_utc(cls, value: object) -> datetime:
        if isinstance(value, datetime):
            if value.tzinfo is None:
                return value.replace(tzinfo=timezone.utc)
            return value.astimezone(timezone.utc)
        raise TypeError("Expected datetime")

    def matches_type(self, tx_type: str) -> bool:
        """Return True if this category can be used for ``tx_type``."""
        if self.kind == CategoryKind.BOTH:
            return True
        return self.kind.value == tx_type
