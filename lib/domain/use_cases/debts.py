"""Debt-related use cases."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from pydantic import BaseModel

from lib.domain.entities.debt import Debt, DebtDirection, DebtStatus
from lib.domain.entities.money import quantize_money
from lib.domain.entities.transaction import Transaction, TransactionType
from lib.domain.repositories.account_repository import AccountRepository
from lib.domain.repositories.debt_repository import DebtRepository

if TYPE_CHECKING:
    from lib.domain.use_cases.transactions import AddTransactionUseCase

DEBT_CATEGORY = "Долг"
DEBT_PRINCIPAL_CATEGORY = "Долг (выдача)"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class CreateDebtUseCase:
    """Create a debt and optionally move cash on an account."""

    def __init__(
        self,
        debts: DebtRepository,
        accounts: Optional[AccountRepository] = None,
        add_transaction: Optional["AddTransactionUseCase"] = None,
    ) -> None:
        self._debts = debts
        self._accounts = accounts
        self._add_transaction = add_transaction

    async def execute(
        self,
        debt: Debt,
        *,
        account_id: Optional[str] = None,
    ) -> Debt:
        """Persist a debt; if ``account_id`` is set, record principal cash flow.

        * ``I_OWE`` — money received (income / borrow)
        * ``OWED_TO_ME`` — money given (expense / lend)
        """
        amount = quantize_money(debt.amount)
        created = debt.model_copy(
            update={
                "amount": amount,
                "remaining_amount": amount,
                "status": DebtStatus.ACTIVE,
                "created_at": debt.created_at or _utc_now(),
                "updated_at": _utc_now(),
                "started_at": debt.started_at or _utc_now(),
            }
        )
        created = await self._debts.create(created)

        if account_id and self._accounts is not None and self._add_transaction is not None:
            account = await self._accounts.get_by_id(account_id)
            if account is None:
                raise ValueError(f"Account not found: {account_id}")
            # Principal disbursement is NOT a repayment (no debt_id) so remaining stays full.
            tx_type = (
                TransactionType.INCOME
                if created.direction == DebtDirection.I_OWE
                else TransactionType.EXPENSE
            )
            await self._add_transaction.execute(
                Transaction(
                    account_id=account.id,
                    amount=amount,
                    category=DEBT_PRINCIPAL_CATEGORY,
                    date=_utc_now(),
                    comment=created.counterparty,
                    type=tx_type,
                    currency=account.currency,
                )
            )
        return created


class UpdateDebtUseCase:
    """Update debt metadata (remaining only via repayments)."""

    def __init__(self, debts: DebtRepository) -> None:
        self._debts = debts

    async def execute(self, debt: Debt) -> Debt:
        """Update counterparty / terms; keep ledger-based remaining amount."""
        existing = await self._debts.get_by_id(debt.id)
        if existing is None:
            raise ValueError(f"Debt not found: {debt.id}")

        amount = quantize_money(debt.amount)
        remaining = quantize_money(existing.remaining_amount)
        if amount < remaining:
            # Shrinking principal cannot leave remaining higher than amount.
            remaining = amount
        status = DebtStatus.PAID if remaining <= 0 else existing.status
        if remaining > 0 and status == DebtStatus.PAID:
            status = DebtStatus.ACTIVE
        updated = debt.model_copy(
            update={
                "amount": amount,
                "remaining_amount": remaining,
                "status": status,
                "updated_at": _utc_now(),
                "created_at": existing.created_at,
            }
        )
        return await self._debts.update(updated)


class DeleteDebtUseCase:
    """Delete a debt."""

    def __init__(self, debts: DebtRepository) -> None:
        self._debts = debts

    async def execute(self, debt_id: str) -> bool:
        """Remove a debt by id."""
        return await self._debts.delete(debt_id)


class ListDebtsUseCase:
    """List debts."""

    def __init__(self, debts: DebtRepository) -> None:
        self._debts = debts

    async def execute(
        self,
        *,
        status: Optional[DebtStatus] = None,
        direction: Optional[DebtDirection] = None,
    ) -> list[Debt]:
        """Return debts with optional filters."""
        return await self._debts.list(status=status, direction=direction)


class RepayDebtUseCase:
    """Pay or collect against a debt using an account balance."""

    def __init__(
        self,
        debts: DebtRepository,
        accounts: AccountRepository,
        add_transaction: "AddTransactionUseCase",
    ) -> None:
        self._debts = debts
        self._accounts = accounts
        self._add_transaction = add_transaction

    async def execute(
        self,
        debt_id: str,
        amount: Decimal,
        *,
        account_id: str,
    ) -> Debt:
        """Move money and reduce ``remaining_amount``.

        * ``I_OWE`` — expense from account (you repay)
        * ``OWED_TO_ME`` — income to account (they repay you)
        """
        amount = quantize_money(amount)
        if amount <= 0:
            raise ValueError("Payment amount must be positive")
        if not (account_id or "").strip():
            raise ValueError("Account is required for a debt payment")

        debt = await self._debts.get_by_id(debt_id)
        if debt is None:
            raise ValueError(f"Debt not found: {debt_id}")
        if debt.status == DebtStatus.PAID or debt.remaining_amount <= 0:
            raise ValueError("Debt is already paid")

        account = await self._accounts.get_by_id(account_id)
        if account is None:
            raise ValueError(f"Account not found: {account_id}")

        pay = amount
        if pay > debt.remaining_amount:
            pay = quantize_money(debt.remaining_amount)

        tx_type = (
            TransactionType.EXPENSE
            if debt.direction == DebtDirection.I_OWE
            else TransactionType.INCOME
        )
        await self._add_transaction.execute(
            Transaction(
                account_id=account.id,
                amount=pay,
                category=DEBT_CATEGORY,
                date=_utc_now(),
                comment=debt.counterparty,
                type=tx_type,
                currency=account.currency,
                debt_id=debt.id,
            )
        )
        updated = await self._debts.get_by_id(debt_id)
        if updated is None:
            raise ValueError(f"Debt not found after payment: {debt_id}")
        return updated


class DebtInterestResult(BaseModel):
    """Simple interest accrual result for a debt."""

    debt_id: str
    principal: Decimal
    interest_rate: Decimal
    days: int
    interest_amount: Decimal
    total_with_interest: Decimal


class CalculateDebtInterestUseCase:
    """Calculate simple annual interest accrued since ``started_at`` (or a custom range)."""

    def __init__(self, debts: DebtRepository) -> None:
        self._debts = debts

    async def execute(
        self,
        debt_id: str,
        *,
        as_of: Optional[datetime] = None,
    ) -> DebtInterestResult:
        """Compute simple interest: ``remaining * rate% * days / 365``."""
        debt = await self._debts.get_by_id(debt_id)
        if debt is None:
            raise ValueError(f"Debt not found: {debt_id}")
        if debt.interest_rate is None:
            raise ValueError(f"Debt {debt_id} has no interest_rate")

        as_of = as_of or _utc_now()
        if as_of.tzinfo is None:
            as_of = as_of.replace(tzinfo=timezone.utc)

        start = debt.started_at
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)

        days = max(0, (as_of - start).days)
        rate = Decimal(str(debt.interest_rate))
        principal = quantize_money(debt.remaining_amount)
        interest = quantize_money(
            principal * rate * Decimal(days) / Decimal("365") / Decimal("100")
        )

        return DebtInterestResult(
            debt_id=debt.id,
            principal=principal,
            interest_rate=rate,
            days=days,
            interest_amount=interest,
            total_with_interest=quantize_money(principal + interest),
        )
