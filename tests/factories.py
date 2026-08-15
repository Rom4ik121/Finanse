"""Entity builders for tests."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from lib.domain.entities.account import Account
from lib.domain.entities.category import Category, CategoryKind
from lib.domain.entities.debt import Debt, DebtDirection
from lib.domain.entities.goal import Goal
from lib.domain.entities.subscription import Periodicity, Subscription
from lib.domain.entities.transaction import Transaction, TransactionType


def make_account(
    *,
    name: str = "Cash",
    currency: str = "RUB",
    balance: str | Decimal = "1000",
) -> Account:
    amount = Decimal(str(balance))
    return Account(
        name=name,
        currency=currency,
        initial_balance=amount,
        balance=amount,
    )


def make_transaction(
    account_id: str,
    *,
    amount: str | Decimal = "100",
    category: str = "Еда",
    tx_type: TransactionType = TransactionType.EXPENSE,
    currency: str = "RUB",
    goal_id: str | None = None,
    debt_id: str | None = None,
) -> Transaction:
    return Transaction(
        account_id=account_id,
        amount=Decimal(str(amount)),
        category=category,
        date=datetime.now(timezone.utc),
        type=tx_type,
        currency=currency,
        goal_id=goal_id,
        debt_id=debt_id,
    )


def make_goal(
    *,
    name: str = "Trip",
    target: str | Decimal = "500",
    current: str | Decimal = "0",
    currency: str = "RUB",
) -> Goal:
    return Goal(
        name=name,
        target_amount=Decimal(str(target)),
        current_amount=Decimal(str(current)),
        currency=currency,
    )


def make_debt(
    *,
    counterparty: str = "Bank",
    amount: str | Decimal = "400",
    direction: DebtDirection = DebtDirection.I_OWE,
    currency: str = "RUB",
    interest_rate: Decimal | None = None,
) -> Debt:
    value = Decimal(str(amount))
    return Debt(
        counterparty=counterparty,
        amount=value,
        remaining_amount=value,
        direction=direction,
        currency=currency,
        interest_rate=interest_rate,
    )


def make_subscription(
    account_id: str,
    *,
    name: str = "Netflix",
    amount: str | Decimal = "10",
    periodicity: Periodicity = Periodicity.MONTHLY,
    next_billing: datetime | None = None,
    currency: str = "RUB",
    custom_interval_days: int | None = None,
    max_payments: int | None = None,
) -> Subscription:
    return Subscription(
        name=name,
        amount=Decimal(str(amount)),
        currency=currency,
        account_id=account_id,
        category="Прочее",
        periodicity=periodicity,
        custom_interval_days=custom_interval_days,
        max_payments=max_payments,
        next_billing_date=next_billing or datetime.now(timezone.utc),
        is_active=True,
    )


def make_category(
    *,
    name: str = "Custom",
    kind: CategoryKind = CategoryKind.BOTH,
    is_system: bool = False,
) -> Category:
    return Category(
        name=name,
        kind=kind,
        icon="category",
        color="#00897B",
        is_system=is_system,
    )
