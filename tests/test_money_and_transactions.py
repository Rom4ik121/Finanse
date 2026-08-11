"""Core money / transaction use-case tests."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from lib.domain.entities import (
    Account,
    Goal,
    Transaction,
    TransactionType,
)
from lib.infrastructure.services.encryption_service import EncryptionService
from tests.conftest import run_async


def test_expense_updates_balance(container) -> None:
    async def _run() -> None:
        acc = await container.create_account.execute(
            Account(
                name="Cash",
                currency="RUB",
                initial_balance=Decimal("1000.00"),
            )
        )
        await container.add_transaction.execute(
            Transaction(
                account_id=acc.id,
                amount=Decimal("123.456"),
                category="Еда",
                date=datetime.now(timezone.utc),
                type=TransactionType.EXPENSE,
            )
        )
        updated = await container.account_repository.get_by_id(acc.id)
        assert updated is not None
        assert updated.balance == Decimal("876.54")

    run_async(_run())


def test_savings_contributes_to_goal(container) -> None:
    async def _run() -> None:
        acc = await container.create_account.execute(
            Account(name="Cash", currency="RUB", initial_balance=Decimal("500"))
        )
        goal = await container.create_goal.execute(
            Goal(name="Trip", target_amount=Decimal("200"), current_amount=Decimal("0"))
        )
        await container.add_transaction.execute(
            Transaction(
                account_id=acc.id,
                amount=Decimal("200"),
                category="Накопление",
                date=datetime.now(timezone.utc),
                type=TransactionType.EXPENSE,
                goal_id=goal.id,
            )
        )
        updated = await container.goal_repository.get_by_id(goal.id)
        assert updated is not None
        assert updated.current_amount == Decimal("200.00")
        assert updated.is_completed is True
        account = await container.account_repository.get_by_id(acc.id)
        assert account is not None
        assert account.balance == Decimal("300.00")

    run_async(_run())


def test_contribute_to_goal_debits_account(container) -> None:
    async def _run() -> None:
        acc = await container.create_account.execute(
            Account(name="Cash", currency="RUB", initial_balance=Decimal("1000"))
        )
        goal = await container.create_goal.execute(
            Goal(name="Phone", target_amount=Decimal("500"), current_amount=Decimal("99"))
        )
        # Create ignores seeded current_amount — progress starts at 0.
        assert (await container.goal_repository.get_by_id(goal.id)).current_amount == Decimal(
            "0.00"
        )
        updated = await container.contribute_to_goal.execute(
            goal.id, Decimal("150"), account_id=acc.id
        )
        assert updated.current_amount == Decimal("150.00")
        account = await container.account_repository.get_by_id(acc.id)
        assert account is not None
        assert account.balance == Decimal("850.00")

    run_async(_run())


def test_repay_debt_i_owe_debits_account(container) -> None:
    from lib.domain.entities.debt import Debt, DebtDirection

    async def _run() -> None:
        acc = await container.create_account.execute(
            Account(name="Cash", currency="RUB", initial_balance=Decimal("1000"))
        )
        debt = await container.create_debt.execute(
            Debt(
                counterparty="Bank",
                amount=Decimal("400"),
                remaining_amount=Decimal("400"),
                direction=DebtDirection.I_OWE,
                currency="RUB",
            ),
            account_id=acc.id,
        )
        # Borrowed money credited to account.
        account = await container.account_repository.get_by_id(acc.id)
        assert account is not None
        assert account.balance == Decimal("1400.00")
        assert debt.remaining_amount == Decimal("400.00")

        paid = await container.repay_debt.execute(
            debt.id, Decimal("100"), account_id=acc.id
        )
        assert paid.remaining_amount == Decimal("300.00")
        account = await container.account_repository.get_by_id(acc.id)
        assert account is not None
        assert account.balance == Decimal("1300.00")

    run_async(_run())


def test_lend_and_receive_debt_payment(container) -> None:
    from lib.domain.entities.debt import Debt, DebtDirection, DebtStatus

    async def _run() -> None:
        acc = await container.create_account.execute(
            Account(name="Cash", currency="RUB", initial_balance=Decimal("1000"))
        )
        debt = await container.create_debt.execute(
            Debt(
                counterparty="Friend",
                amount=Decimal("200"),
                remaining_amount=Decimal("200"),
                direction=DebtDirection.OWED_TO_ME,
                currency="RUB",
            ),
            account_id=acc.id,
        )
        account = await container.account_repository.get_by_id(acc.id)
        assert account is not None
        assert account.balance == Decimal("800.00")

        paid = await container.repay_debt.execute(
            debt.id, Decimal("200"), account_id=acc.id
        )
        assert paid.remaining_amount == Decimal("0.00")
        assert paid.status == DebtStatus.PAID
        account = await container.account_repository.get_by_id(acc.id)
        assert account is not None
        assert account.balance == Decimal("1000.00")

    run_async(_run())


def test_pin_hash_roundtrip() -> None:
    service = EncryptionService()
    creds = service.hash_pin("1234")
    assert service.verify_pin("1234", creds.pin_hash, creds.pin_salt)
    assert not service.verify_pin("0000", creds.pin_hash, creds.pin_salt)


def test_biometric_env_override(monkeypatch) -> None:
    from lib.infrastructure.services.biometric import (
        BiometricResult,
        BiometricStatus,
        probe_biometric_status,
        request_biometric_verification,
    )

    monkeypatch.setenv("FINANCE_BIOMETRIC_OK", "1")

    async def _run() -> None:
        assert await probe_biometric_status() is BiometricStatus.AVAILABLE
        assert await request_biometric_verification("test") is BiometricResult.VERIFIED
        service = EncryptionService()
        assert await service.authenticate_biometric() is BiometricResult.VERIFIED

    run_async(_run())


def test_settings_reminder_time(container) -> None:
    async def _run() -> None:
        settings = await container.get_settings.execute()
        settings.reminder_time = "21:30"
        settings.biometric_enabled = True
        saved = await container.update_settings.execute(settings)
        assert saved.reminder_time == "21:30"
        assert saved.biometric_enabled is True

    run_async(_run())
