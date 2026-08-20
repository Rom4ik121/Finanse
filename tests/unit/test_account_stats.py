"""Account period stats aggregation."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from lib.domain.entities.transaction import Transaction, TransactionType
from lib.domain.use_cases.transactions import StatsPeriod
from lib.presentation.account_stats import aggregate_account_period


def _tx(
    *,
    amount: str,
    tx_type: TransactionType,
    category: str = "Еда",
    transfer: bool = False,
    day: int = 1,
) -> Transaction:
    return Transaction(
        account_id="a1",
        amount=Decimal(amount),
        category=category,
        date=datetime(2026, 8, day, tzinfo=timezone.utc),
        type=tx_type,
        currency="UZS",
        transfer_id="t1" if transfer else None,
        transfer_peer_account_id="a2" if transfer else None,
    )


def test_account_stats_separates_transfers_from_spend() -> None:
    stats = aggregate_account_period(
        [
            _tx(amount="100", tx_type=TransactionType.EXPENSE, category="Еда"),
            _tx(amount="40", tx_type=TransactionType.EXPENSE, category="Еда"),
            _tx(amount="200", tx_type=TransactionType.INCOME, category="Зарплата"),
            _tx(
                amount="50",
                tx_type=TransactionType.EXPENSE,
                category="Перевод",
                transfer=True,
            ),
            _tx(
                amount="10",
                tx_type=TransactionType.INCOME,
                category="Перевод",
                transfer=True,
                day=2,
            ),
        ],
        StatsPeriod.DAY,
    )
    assert stats.income == Decimal("210.00")
    assert stats.expense == Decimal("190.00")
    assert stats.ops_expense == Decimal("140.00")
    assert stats.ops_income == Decimal("200.00")
    assert stats.transfer_out == Decimal("50.00")
    assert stats.transfer_in == Decimal("10.00")
    assert stats.by_category == [("Еда", Decimal("140.00"))]
    assert stats.tx_count == 5
    assert len(stats.by_period) == 2
