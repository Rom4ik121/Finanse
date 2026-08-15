"""Debt domain entity."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

from lib.domain.entities.currency_codes import normalize_currency_code
from lib.domain.entities.money import quantize_money


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class DebtDirection(str, Enum):
    """Who owes whom."""

    I_OWE = "i_owe"
    OWED_TO_ME = "owed_to_me"


class DebtStatus(str, Enum):
    """Lifecycle status of a debt."""

    ACTIVE = "active"
    OVERDUE = "overdue"
    PAID = "paid"
    ARCHIVED = "archived"


def resolve_debt_status(
    *,
    remaining_amount: Decimal,
    due_date: Optional[datetime],
    current: DebtStatus | str | None = None,
    now: Optional[datetime] = None,
) -> DebtStatus:
    """Derive status from remaining balance and due date.

    ``ARCHIVED`` is sticky until the caller changes it explicitly.
    """
    if isinstance(current, str):
        current = DebtStatus(current)
    if current == DebtStatus.ARCHIVED:
        return DebtStatus.ARCHIVED
    remaining = quantize_money(remaining_amount)
    if remaining <= 0:
        return DebtStatus.PAID
    moment = now or _utc_now()
    if due_date is not None:
        due = due_date
        if due.tzinfo is None:
            due = due.replace(tzinfo=timezone.utc)
        if due < moment:
            return DebtStatus.OVERDUE
    return DebtStatus.ACTIVE


class Debt(BaseModel):
    """A personal debt (owed by or to the user)."""

    model_config = ConfigDict(from_attributes=True, use_enum_values=False)

    id: str = Field(default_factory=lambda: str(uuid4()))
    counterparty: str
    amount: Decimal
    remaining_amount: Decimal
    currency: str = "RUB"
    direction: DebtDirection
    status: DebtStatus = DebtStatus.ACTIVE
    interest_rate: Optional[Decimal] = None  # annual percent, e.g. 12.5
    due_date: Optional[datetime] = None
    started_at: datetime = Field(default_factory=_utc_now)
    comment: str = ""
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)

    @field_validator("amount", "remaining_amount", mode="before")
    @classmethod
    def _quantize_money_fields(cls, value: object) -> Decimal:
        return quantize_money(value)  # type: ignore[arg-type]

    @field_validator("currency", mode="before")
    @classmethod
    def _normalize_currency(cls, value: object) -> str:
        return normalize_currency_code(str(value) if value is not None else "RUB")

    @field_validator("status", mode="before")
    @classmethod
    def _parse_status(cls, value: object) -> object:
        if isinstance(value, DebtStatus):
            return value
        if value is None:
            return DebtStatus.ACTIVE
        return DebtStatus(str(value).lower())

    @field_validator("interest_rate", mode="before")
    @classmethod
    def _coerce_rate(cls, value: object) -> object:
        if value is None or value == "":
            return None
        return Decimal(str(value))

    @field_validator(
        "due_date",
        "started_at",
        "created_at",
        "updated_at",
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
