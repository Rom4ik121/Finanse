"""Account-related use cases."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from lib.domain.entities.account import Account
from lib.domain.entities.money import quantize_money
from lib.domain.entities.transaction import TransactionType
from lib.domain.repositories.account_repository import AccountRepository
from lib.domain.repositories.transaction_repository import TransactionRepository


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class CreateAccountUseCase:
    """Create a new account with an initial balance."""

    def __init__(self, accounts: AccountRepository) -> None:
        self._accounts = accounts

    async def execute(self, account: Account) -> Account:
        """Persist a new account; balance starts at ``initial_balance``."""
        initial = quantize_money(account.initial_balance)
        created = account.model_copy(
            update={
                "initial_balance": initial,
                "balance": initial,
                "created_at": account.created_at or _utc_now(),
            }
        )
        return await self._accounts.create(created)


class UpdateAccountUseCase:
    """Update account metadata (name, icon, color, currency, active flag)."""

    def __init__(self, accounts: AccountRepository) -> None:
        self._accounts = accounts

    async def execute(self, account: Account) -> Account:
        """Update an existing account."""
        existing = await self._accounts.get_by_id(account.id)
        if existing is None:
            raise ValueError(f"Account not found: {account.id}")
        # Preserve balance unless caller explicitly recalculates elsewhere.
        updated = account.model_copy(
            update={
                "balance": quantize_money(account.balance),
                "initial_balance": quantize_money(account.initial_balance),
            }
        )
        return await self._accounts.update(updated)


class DeleteAccountUseCase:
    """Delete an account."""

    def __init__(self, accounts: AccountRepository) -> None:
        self._accounts = accounts

    async def execute(self, account_id: str) -> bool:
        """Remove an account by id."""
        return await self._accounts.delete(account_id)


class ListAccountsUseCase:
    """List accounts."""

    def __init__(self, accounts: AccountRepository) -> None:
        self._accounts = accounts

    async def execute(self, *, active_only: bool = False) -> list[Account]:
        """Return accounts, optionally active-only."""
        return await self._accounts.list(active_only=active_only)


class RecalculateAccountBalanceUseCase:
    """Recompute an account balance from initial balance + transactions."""

    def __init__(
        self,
        accounts: AccountRepository,
        transactions: TransactionRepository,
    ) -> None:
        self._accounts = accounts
        self._transactions = transactions

    async def execute(self, account_id: str) -> Account:
        """Set balance = initial_balance + incomes − expenses."""
        account = await self._accounts.get_by_id(account_id)
        if account is None:
            raise ValueError(f"Account not found: {account_id}")

        txs = await self._transactions.list_by_account(account_id)
        balance = quantize_money(account.initial_balance)
        for tx in txs:
            if tx.type == TransactionType.INCOME:
                balance += tx.amount
            else:
                balance -= tx.amount

        account.balance = quantize_money(balance)
        return await self._accounts.update(account)
