"""Pure aggregation of one account's transactions for the detail screen."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
from typing import Sequence

from lib.domain.entities.money import quantize_money
from lib.domain.entities.transaction import Transaction, TransactionType
from lib.domain.use_cases.transactions import GetTransactionStatsUseCase, StatsPeriod


@dataclass(frozen=True)
class AccountPeriodStats:
    """Cash-flow and category totals for one account in a period."""

    income: Decimal
    expense: Decimal
    ops_income: Decimal
    ops_expense: Decimal
    transfer_in: Decimal
    transfer_out: Decimal
    tx_count: int
    by_category: list[tuple[str, Decimal]]
    by_period: list[tuple[str, Decimal, Decimal]]


def aggregate_account_period(
    transactions: Sequence[Transaction],
    group_by: StatsPeriod,
) -> AccountPeriodStats:
    """Summarize ``transactions`` already filtered to one account and date range.

    Income/expense totals include transfers (they move the account balance).
    Category pie uses ordinary expenses only, so transfers do not dominate it.
    """
    income = Decimal("0.00")
    expense = Decimal("0.00")
    ops_income = Decimal("0.00")
    ops_expense = Decimal("0.00")
    transfer_in = Decimal("0.00")
    transfer_out = Decimal("0.00")
    period_income: dict[str, Decimal] = defaultdict(lambda: Decimal("0.00"))
    period_expense: dict[str, Decimal] = defaultdict(lambda: Decimal("0.00"))
    category_totals: dict[str, Decimal] = defaultdict(lambda: Decimal("0.00"))

    for tx in transactions:
        amount = quantize_money(tx.amount)
        key = GetTransactionStatsUseCase._period_key(tx.date, group_by)
        is_income = tx.type == TransactionType.INCOME
        if is_income:
            income += amount
            period_income[key] += amount
        else:
            expense += amount
            period_expense[key] += amount
        if tx.transfer_id:
            if is_income:
                transfer_in += amount
            else:
                transfer_out += amount
        elif is_income:
            ops_income += amount
        else:
            ops_expense += amount
            category_totals[tx.category] += amount

    keys = sorted(set(period_income) | set(period_expense))
    by_period = [
        (
            key,
            quantize_money(period_income[key]),
            quantize_money(period_expense[key]),
        )
        for key in keys
    ]
    by_category = [
        (cat, quantize_money(amount))
        for cat, amount in sorted(
            category_totals.items(), key=lambda kv: kv[1], reverse=True
        )
    ]
    return AccountPeriodStats(
        income=quantize_money(income),
        expense=quantize_money(expense),
        ops_income=quantize_money(ops_income),
        ops_expense=quantize_money(ops_expense),
        transfer_in=quantize_money(transfer_in),
        transfer_out=quantize_money(transfer_out),
        tx_count=len(transactions),
        by_category=by_category,
        by_period=by_period,
    )
