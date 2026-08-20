"""SQLAlchemy 2.0 ORM models for the Finanse application."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from lib.core.database import Base


def _utc_now() -> datetime:
    from datetime import timezone

    return datetime.now(timezone.utc)


def _utc_today() -> date:
    return _utc_now().date()


class AccountModel(Base):
    """Persisted wallet / bank account."""

    __tablename__ = "accounts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    currency: Mapped[str] = mapped_column(String(16), nullable=False, default="RUB")
    balance: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0.00"))
    initial_balance: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False, default=Decimal("0.00")
    )
    icon: Mapped[str] = mapped_column(String(64), nullable=False, default="wallet")
    color: Mapped[str] = mapped_column(String(16), nullable=False, default="#2E7D32")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now
    )

    transactions: Mapped[list["TransactionModel"]] = relationship(
        back_populates="account",
        cascade="all, delete-orphan",
    )
    subscriptions: Mapped[list["SubscriptionModel"]] = relationship(
        back_populates="account",
        cascade="all, delete-orphan",
    )


class TransactionModel(Base):
    """Persisted income / expense transaction."""

    __tablename__ = "transactions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    account_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    category: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    tags: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    comment: Mapped[str] = mapped_column(Text, nullable=False, default="")
    type: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    currency: Mapped[str] = mapped_column(String(16), nullable=False, default="RUB")
    goal_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("goals.id", ondelete="SET NULL"), nullable=True, index=True
    )
    debt_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("debts.id", ondelete="SET NULL"), nullable=True, index=True
    )
    goal_credit_amount: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(18, 2), nullable=True
    )
    debt_credit_amount: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(18, 2), nullable=True
    )
    subscription_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("subscriptions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    transfer_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    transfer_peer_account_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utc_now,
        onupdate=_utc_now,
    )

    account: Mapped["AccountModel"] = relationship(back_populates="transactions")
    goal: Mapped[Optional["GoalModel"]] = relationship(back_populates="transactions")
    debt: Mapped[Optional["DebtModel"]] = relationship(back_populates="transactions")


class GoalModel(Base):
    """Persisted savings goal."""

    __tablename__ = "goals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    target_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    current_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False, default=Decimal("0.00")
    )
    currency: Mapped[str] = mapped_column(String(16), nullable=False, default="RUB")
    deadline: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    category_link: Mapped[str] = mapped_column(String(128), nullable=False, default="Накопление")
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="active", index=True
    )
    is_completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    cached_projection: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now
    )

    transactions: Mapped[list["TransactionModel"]] = relationship(back_populates="goal")


class DebtModel(Base):
    """Persisted personal debt."""

    __tablename__ = "debts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    counterparty: Mapped[str] = mapped_column(String(256), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    remaining_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(16), nullable=False, default="RUB")
    direction: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active", index=True)
    interest_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4), nullable=True)
    due_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now
    )
    comment: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utc_now,
        onupdate=_utc_now,
    )

    transactions: Mapped[list["TransactionModel"]] = relationship(back_populates="debt")


class SubscriptionModel(Base):
    """Persisted recurring subscription."""

    __tablename__ = "subscriptions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(16), nullable=False, default="RUB")
    account_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    category: Mapped[str] = mapped_column(String(128), nullable=False, default="Прочее")
    periodicity: Mapped[str] = mapped_column(String(16), nullable=False, default="monthly")
    custom_interval_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    start_date: Mapped[date] = mapped_column(
        Date, nullable=False, index=True, default=_utc_today
    )
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    max_payments: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    payments_made: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    next_billing_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="active", index=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    auto_charge: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_charged_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_skip_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    comment: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utc_now,
        onupdate=_utc_now,
    )

    account: Mapped["AccountModel"] = relationship(back_populates="subscriptions")


class CurrencyModel(Base):
    """Persisted fiat / crypto currency definition."""

    __tablename__ = "currencies"

    code: Mapped[str] = mapped_column(String(16), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    name_ru: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    name_en: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    symbol: Mapped[str] = mapped_column(String(16), nullable=False)
    is_crypto: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class ExchangeRateModel(Base):
    """Persisted exchange rate quote."""

    __tablename__ = "exchange_rates"
    __table_args__ = (UniqueConstraint("base", "quote", name="uq_exchange_base_quote"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    base: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    quote: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    rate: Mapped[Decimal] = mapped_column(Numeric(24, 12), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utc_now,
        server_default=func.now(),
    )


class CategoryModel(Base):
    """Persisted user / system transaction category."""

    __tablename__ = "categories"
    __table_args__ = (UniqueConstraint("name", name="uq_categories_name"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    icon: Mapped[str] = mapped_column(String(64), nullable=False, default="category")
    color: Mapped[str] = mapped_column(String(16), nullable=False, default="#00897B")
    kind: Mapped[str] = mapped_column(String(16), nullable=False, default="both", index=True)
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utc_now,
        onupdate=_utc_now,
    )


class SettingsModel(Base):
    """Persisted application settings (singleton)."""

    __tablename__ = "settings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default="default")
    default_currency: Mapped[str] = mapped_column(String(16), nullable=False, default="RUB")
    theme: Mapped[str] = mapped_column(String(32), nullable=False, default="dark")
    language: Mapped[str] = mapped_column(String(8), nullable=False, default="ru")
    exchange_update_interval_minutes: Mapped[int] = mapped_column(
        Integer, nullable=False, default=60
    )
    notifications_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    subscription_reminders: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    debt_reminders: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    goal_milestones: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    low_balance_threshold: Mapped[Optional[float]] = mapped_column(Numeric(18, 2), nullable=True)
    reminder_time: Mapped[str] = mapped_column(String(8), nullable=False, default="09:00")
    reminder_days: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    check_balance_before_subscription: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    pin_hash: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    pin_salt: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    biometric_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    budget_alerts: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utc_now,
        onupdate=_utc_now,
    )


class BudgetModel(Base):
    """Persisted monthly spending limit per category."""

    __tablename__ = "budgets"
    __table_args__ = (
        UniqueConstraint(
            "category_id", "month", "year", name="uq_budgets_category_month"
        ),
        Index("ix_budgets_month_year", "month", "year"),
        Index("ix_budgets_category_month", "category_id", "month", "year"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    category_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("categories.name", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        index=True,
    )
    month: Mapped[int] = mapped_column(Integer, nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    amount_limit: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    spent: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False, default=Decimal("0.00")
    )
    last_alert_level: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utc_now,
        onupdate=_utc_now,
    )
