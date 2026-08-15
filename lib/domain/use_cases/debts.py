"""Debt-related use cases."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from pydantic import BaseModel

from lib.domain.entities.debt import (
    Debt,
    DebtDirection,
    DebtStatus,
    resolve_debt_status,
)
from lib.domain.entities.money import quantize_money
from lib.domain.entities.transaction import Transaction, TransactionType
from lib.domain.repositories.account_repository import AccountRepository
from lib.domain.repositories.currency_repository import CurrencyRepository
from lib.domain.repositories.debt_repository import DebtRepository
from lib.domain.repositories.transaction_repository import TransactionRepository
from lib.domain.services.rate_book import RateBook

if TYPE_CHECKING:
    from lib.domain.use_cases.transactions import (
        AddTransactionUseCase,
        DeleteTransactionUseCase,
    )

DEBT_CATEGORY = "Долг"
DEBT_PRINCIPAL_CATEGORY = "Долг (выдача)"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _months_between(start: datetime, end: datetime) -> float:
    if end <= start:
        return 0.0
    return max((end - start).total_seconds() / 86400.0 / 30.4375, 0.0)


def _add_months(dt: datetime, months: float) -> datetime:
    return dt + timedelta(days=months * 30.4375)


def debt_credit_amount(transaction: Transaction) -> Decimal:
    """Amount applied to debt remaining (debt currency)."""
    if transaction.debt_credit_amount is not None:
        return quantize_money(transaction.debt_credit_amount)
    return quantize_money(transaction.amount)


class DebtProjection(BaseModel):
    """Payoff pace / recommended payment metrics for a debt."""

    debt_id: str
    recommended_monthly_payment: Optional[Decimal] = None
    projected_payoff_date: Optional[datetime] = None
    is_on_track: Optional[bool] = None
    average_monthly_payment: Decimal = Decimal("0.00")
    remaining_amount: Decimal = Decimal("0.00")
    lookback_months: int = 3


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
        """Persist a debt; if ``account_id`` is set, record principal cash flow."""
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
            remaining = amount
        requested = debt.status if isinstance(debt.status, DebtStatus) else DebtStatus(debt.status)
        if requested == DebtStatus.ARCHIVED:
            status = DebtStatus.ARCHIVED
        else:
            status = resolve_debt_status(
                remaining_amount=remaining,
                due_date=debt.due_date,
                current=requested,
            )
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
        return await self._debts.delete(debt_id)


class ListDebtsUseCase:
    """List debts."""

    def __init__(self, debts: DebtRepository) -> None:
        self._debts = debts

    async def execute(
        self,
        *,
        status: DebtStatus | str | None = None,
        direction: DebtDirection | str | None = None,
        currency: str | None = None,
        sort_by: str = "due_date",
    ) -> list[Debt]:
        return await self._debts.list(
            status=status,
            direction=direction,
            currency=currency,
            sort_by=sort_by,
        )


class ArchiveDebtUseCase:
    """Move a paid (or closed) debt to archived status."""

    def __init__(self, debts: DebtRepository) -> None:
        self._debts = debts

    async def execute(self, debt_id: str) -> Debt:
        debt = await self._debts.get_by_id(debt_id)
        if debt is None:
            raise ValueError(f"Debt not found: {debt_id}")
        if debt.status == DebtStatus.ARCHIVED:
            return debt
        if debt.status != DebtStatus.PAID:
            raise ValueError("Only paid debts can be archived")
        updated = debt.model_copy(
            update={"status": DebtStatus.ARCHIVED, "updated_at": _utc_now()}
        )
        return await self._debts.update(updated)


class MarkOverdueDebtsUseCase:
    """Flip active debts past due_date to overdue status."""

    def __init__(self, debts: DebtRepository) -> None:
        self._debts = debts

    async def execute(self, *, now: Optional[datetime] = None) -> list[Debt]:
        moment = now or _utc_now()
        changed: list[Debt] = []
        for debt in await self._debts.list(status=DebtStatus.ACTIVE):
            status = resolve_debt_status(
                remaining_amount=debt.remaining_amount,
                due_date=debt.due_date,
                current=debt.status,
                now=moment,
            )
            if status != DebtStatus.OVERDUE:
                continue
            updated = debt.model_copy(
                update={"status": DebtStatus.OVERDUE, "updated_at": moment}
            )
            changed.append(await self._debts.update(updated))
        return changed


class RepayDebtUseCase:
    """Pay or collect against a debt using an account balance (FX-aware)."""

    def __init__(
        self,
        debts: DebtRepository,
        accounts: AccountRepository,
        add_transaction: "AddTransactionUseCase",
        currencies: CurrencyRepository,
    ) -> None:
        self._debts = debts
        self._accounts = accounts
        self._add_transaction = add_transaction
        self._currencies = currencies

    async def execute(
        self,
        debt_id: str,
        amount: Decimal,
        *,
        account_id: str,
        interest_amount: Optional[Decimal] = None,
    ) -> Debt:
        """Move money and reduce ``remaining_amount``.

        ``amount`` is in the **account** currency (total cash movement).
        Optional ``interest_amount`` is in the **debt** currency and is recorded
        in the comment only — it does not reduce remaining. The principal
        portion applied to remaining is ``converted(amount) - interest``.
        """
        amount = quantize_money(amount)
        if amount <= 0:
            raise ValueError("Payment amount must be positive")
        if not (account_id or "").strip():
            raise ValueError("Account is required for a debt payment")

        debt = await self._debts.get_by_id(debt_id)
        if debt is None:
            raise ValueError(f"Debt not found: {debt_id}")
        if debt.status in (DebtStatus.PAID, DebtStatus.ARCHIVED) or debt.remaining_amount <= 0:
            raise ValueError("Debt is already paid")

        account = await self._accounts.get_by_id(account_id)
        if account is None:
            raise ValueError(f"Account not found: {account_id}")

        rates = await self._currencies.list_rates()
        book = RateBook(rates)
        converted = book.convert(amount, account.currency, debt.currency)
        if converted is None:
            raise ValueError(
                f"No exchange rate for {account.currency}/{debt.currency}"
            )
        converted = quantize_money(converted)

        interest = Decimal("0.00")
        if interest_amount is not None:
            interest = quantize_money(interest_amount)
            if interest < 0:
                raise ValueError("Interest amount cannot be negative")
            if interest > converted:
                raise ValueError("Interest cannot exceed payment amount")

        principal_credit = quantize_money(converted - interest)
        if principal_credit > debt.remaining_amount:
            # Clamp principal; keep interest as entered.
            principal_credit = quantize_money(debt.remaining_amount)
            # Recalculate account amount from clamped principal + interest.
            debt_total = quantize_money(principal_credit + interest)
            account_amount = book.convert(debt_total, debt.currency, account.currency)
            if account_amount is None:
                raise ValueError(
                    f"No exchange rate for {debt.currency}/{account.currency}"
                )
            amount = quantize_money(account_amount)
        elif principal_credit <= 0 and interest <= 0:
            raise ValueError("Payment amount must be positive")

        comment = debt.counterparty
        if interest > 0:
            comment = f"{debt.counterparty} · interest {interest} {debt.currency}"

        tx_type = (
            TransactionType.EXPENSE
            if debt.direction == DebtDirection.I_OWE
            else TransactionType.INCOME
        )
        await self._add_transaction.execute(
            Transaction(
                account_id=account.id,
                amount=amount,
                category=DEBT_CATEGORY,
                date=_utc_now(),
                comment=comment,
                type=tx_type,
                currency=account.currency,
                debt_id=debt.id,
                debt_credit_amount=principal_credit,
            )
        )
        updated = await self._debts.get_by_id(debt_id)
        if updated is None:
            raise ValueError(f"Debt not found after payment: {debt_id}")
        return updated


class GetDebtProjectionUseCase:
    """Compute payoff pace, recommended monthly payment, and on-track status."""

    def __init__(
        self,
        debts: DebtRepository,
        transactions: TransactionRepository,
        *,
        lookback_months: int = 3,
    ) -> None:
        self._debts = debts
        self._transactions = transactions
        self._lookback_months = max(1, int(lookback_months))

    async def execute(self, debt_id: str) -> DebtProjection:
        debt = await self._debts.get_by_id(debt_id)
        if debt is None:
            raise ValueError(f"Debt not found: {debt_id}")

        now = _utc_now()
        remaining = quantize_money(max(Decimal("0"), debt.remaining_amount))
        projection = DebtProjection(
            debt_id=debt.id,
            remaining_amount=remaining,
            lookback_months=self._lookback_months,
        )
        if remaining <= 0:
            projection.recommended_monthly_payment = Decimal("0.00")
            projection.projected_payoff_date = now
            projection.is_on_track = True
            return projection

        if debt.due_date is not None:
            months_left = _months_between(now, debt.due_date)
            if months_left <= 0:
                projection.recommended_monthly_payment = remaining
                projection.is_on_track = False
            else:
                projection.recommended_monthly_payment = quantize_money(
                    remaining / Decimal(str(months_left))
                )

        lookback_start = now - timedelta(days=int(self._lookback_months * 30.4375))
        txs = await self._transactions.list(debt_id=debt.id, date_from=lookback_start)
        total_paid = sum((debt_credit_amount(tx) for tx in txs), Decimal("0"))
        avg = quantize_money(
            total_paid / Decimal(str(self._lookback_months))
            if self._lookback_months
            else Decimal("0")
        )
        projection.average_monthly_payment = avg

        if avg > 0:
            months_needed = float(remaining / avg)
            projection.projected_payoff_date = _add_months(now, months_needed)
        elif debt.due_date is not None:
            projection.projected_payoff_date = debt.due_date
        else:
            projection.projected_payoff_date = None

        if debt.due_date is not None:
            if projection.projected_payoff_date is None:
                projection.is_on_track = False
            else:
                projection.is_on_track = (
                    projection.projected_payoff_date <= debt.due_date
                )
            created = debt.started_at or debt.created_at or now
            total_span = _months_between(created, debt.due_date)
            elapsed = _months_between(created, now)
            if total_span > 0:
                expected_paid = quantize_money(
                    debt.amount * (Decimal(str(elapsed)) / Decimal(str(total_span)))
                )
                paid_so_far = quantize_money(debt.amount - remaining)
                if paid_so_far + Decimal("0.01") < expected_paid:
                    projection.is_on_track = False

        return projection


class DeleteDebtPaymentUseCase:
    """Delete a debt payment transaction and restore remaining amount."""

    def __init__(
        self,
        transactions: TransactionRepository,
        delete_transaction: "DeleteTransactionUseCase",
    ) -> None:
        self._transactions = transactions
        self._delete_transaction = delete_transaction

    async def execute(self, transaction_id: str, *, debt_id: str) -> bool:
        tx = await self._transactions.get_by_id(transaction_id)
        if tx is None:
            return False
        if tx.debt_id != debt_id:
            raise ValueError("Transaction is not linked to this debt")
        return await self._delete_transaction.execute(transaction_id)


class DebtInterestResult(BaseModel):
    """Simple interest accrual result for a debt."""

    debt_id: str
    principal: Decimal
    interest_rate: Decimal
    days: int
    interest_amount: Decimal
    total_with_interest: Decimal


class CalculateDebtInterestUseCase:
    """Calculate simple annual interest accrued since ``started_at``."""

    def __init__(self, debts: DebtRepository) -> None:
        self._debts = debts

    async def execute(
        self,
        debt_id: str,
        *,
        as_of: Optional[datetime] = None,
        debt: Optional[Debt] = None,
    ) -> DebtInterestResult:
        entity = debt
        if entity is None:
            entity = await self._debts.get_by_id(debt_id)
        if entity is None:
            raise ValueError(f"Debt not found: {debt_id}")
        return compute_debt_interest(entity, as_of=as_of)


def compute_debt_interest(
    debt: Debt,
    *,
    as_of: Optional[datetime] = None,
) -> DebtInterestResult:
    """Pure interest calculation from an already-loaded debt entity."""
    if debt.interest_rate is None:
        raise ValueError(f"Debt {debt.id} has no interest_rate")

    moment = as_of or _utc_now()
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)

    start = debt.started_at
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)

    days = max(0, (moment - start).days)
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
