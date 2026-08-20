"""Monthly category budget use cases."""

from __future__ import annotations

from calendar import monthrange
from datetime import datetime, timezone
from decimal import Decimal
from typing import Callable, Optional, Protocol, Sequence

from lib.domain.entities.budget import Budget, BudgetProgress
from lib.domain.entities.category import CategoryKind
from lib.domain.entities.money import quantize_money
from lib.domain.entities.settings import AppSettings
from lib.domain.entities.transaction import TransactionType
from lib.domain.repositories.budget_repository import BudgetRepository
from lib.domain.repositories.category_repository import CategoryRepository
from lib.domain.repositories.transaction_repository import TransactionRepository


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def month_bounds(year: int, month: int) -> tuple[datetime, datetime]:
    """Inclusive UTC range covering ``year``/``month``."""
    start = datetime(year, month, 1, tzinfo=timezone.utc)
    last_day = monthrange(year, month)[1]
    end = datetime(year, month, last_day, 23, 59, 59, 999999, tzinfo=timezone.utc)
    return start, end


class BudgetNotifier(Protocol):
    """Minimal notification port used by budget threshold alerts."""

    def push(
        self,
        title: str,
        body: str,
        *,
        kind: object = None,
        related_id: Optional[str] = None,
    ) -> object: ...


TranslateFn = Callable[..., str]


class SetBudgetUseCase:
    """Create or update a monthly category limit."""

    def __init__(
        self,
        budgets: BudgetRepository,
        categories: CategoryRepository,
        transactions: TransactionRepository,
    ) -> None:
        self._budgets = budgets
        self._categories = categories
        self._transactions = transactions

    async def execute(
        self,
        category_id: str,
        month: int,
        year: int,
        amount_limit: Decimal,
    ) -> Budget:
        name = (category_id or "").strip()
        if not name:
            raise ValueError("Category is required")
        limit = quantize_money(amount_limit)
        if limit <= 0:
            raise ValueError("Budget amount_limit must be positive")

        category = await self._categories.get_by_name(name)
        if category is None:
            raise ValueError(f"Category not found: {name}")
        kind = category.kind
        kind_value = kind.value if isinstance(kind, CategoryKind) else str(kind)
        if kind_value not in (CategoryKind.EXPENSE.value, CategoryKind.BOTH.value):
            raise ValueError("Budget category must be expense or both")

        existing = await self._budgets.get_by_category_and_month(name, month, year)
        spent = await _sum_expenses(self._transactions, name, month, year)
        now = _utc_now()
        if existing is None:
            budget = Budget(
                category_id=name,
                month=month,
                year=year,
                amount_limit=limit,
                spent=spent,
                last_alert_level=0,
                created_at=now,
                updated_at=now,
            )
        else:
            budget = existing.model_copy(
                update={
                    "amount_limit": limit,
                    "spent": spent,
                    "updated_at": now,
                }
            )
        return await self._budgets.save(budget)


class DeleteBudgetUseCase:
    """Remove a budget by id."""

    def __init__(self, budgets: BudgetRepository) -> None:
        self._budgets = budgets

    async def execute(self, budget_id: str) -> bool:
        return await self._budgets.delete(budget_id)


class GetBudgetProgressUseCase:
    """Return progress for one budget."""

    def __init__(self, budgets: BudgetRepository) -> None:
        self._budgets = budgets

    async def execute(
        self,
        *,
        budget_id: Optional[str] = None,
        category_id: Optional[str] = None,
        month: Optional[int] = None,
        year: Optional[int] = None,
    ) -> BudgetProgress:
        budget: Optional[Budget] = None
        if budget_id:
            budget = await self._budgets.get_by_id(budget_id)
        elif category_id and month and year:
            budget = await self._budgets.get_by_category_and_month(
                category_id, month, year
            )
        else:
            raise ValueError("budget_id or category_id+month+year is required")
        if budget is None:
            raise ValueError("Budget not found")
        return BudgetProgress.from_budget(budget)


class GetBudgetsForMonthUseCase:
    """List budgets for a calendar month with progress."""

    def __init__(self, budgets: BudgetRepository) -> None:
        self._budgets = budgets

    async def execute(
        self,
        month: int,
        year: int,
        category_ids: Optional[Sequence[str]] = None,
    ) -> list[BudgetProgress]:
        items = await self._budgets.list_for_month(
            month, year, category_ids=category_ids
        )
        items.sort(key=lambda b: b.percent_used, reverse=True)
        return [BudgetProgress.from_budget(b) for b in items]


class RecalculateBudgetSpentUseCase:
    """Recompute ``spent`` from expense transactions."""

    def __init__(
        self,
        budgets: BudgetRepository,
        transactions: TransactionRepository,
    ) -> None:
        self._budgets = budgets
        self._transactions = transactions

    async def execute(
        self,
        *,
        month: int,
        year: int,
        budget_id: Optional[str] = None,
        category_id: Optional[str] = None,
    ) -> list[Budget]:
        if budget_id:
            budget = await self._budgets.get_by_id(budget_id)
            targets = [budget] if budget is not None else []
        elif category_id:
            budget = await self._budgets.get_by_category_and_month(
                category_id, month, year
            )
            targets = [budget] if budget is not None else []
        else:
            targets = await self._budgets.list_for_month(month, year)

        updated: list[Budget] = []
        now = _utc_now()
        for budget in targets:
            spent = await _sum_expenses(
                self._transactions, budget.category_id, budget.month, budget.year
            )
            saved = await self._budgets.save(
                budget.model_copy(update={"spent": spent, "updated_at": now})
            )
            updated.append(saved)
        return updated


async def apply_expense_delta(
    budgets: BudgetRepository,
    *,
    category: str,
    when: datetime,
    amount: Decimal,
    sign: int,
    settings: Optional[AppSettings] = None,
    notifications: Optional[BudgetNotifier] = None,
    translate: Optional[TranslateFn] = None,
    currency: str = "RUB",
    language: str = "ru",
) -> Optional[Budget]:
    """Adjust ``spent`` for the matching monthly budget and emit alerts.

    ``sign`` is ``+1`` when an expense is added and ``-1`` when reversed.
    Non-expense callers should not invoke this helper.
    """
    name = (category or "").strip()
    if not name or amount <= 0:
        return None
    moment = when if when.tzinfo else when.replace(tzinfo=timezone.utc)
    budget = await budgets.get_by_category_and_month(name, moment.month, moment.year)
    if budget is None:
        return None
    delta = quantize_money(amount) * Decimal(sign)
    new_spent = quantize_money(max(Decimal("0"), budget.spent + delta))
    updated = await budgets.save(
        budget.model_copy(update={"spent": new_spent, "updated_at": _utc_now()})
    )
    await _maybe_notify(
        budgets,
        updated,
        settings=settings,
        notifications=notifications,
        translate=translate,
        currency=currency,
        language=language,
    )
    return updated


async def _maybe_notify(
    budgets: BudgetRepository,
    budget: Budget,
    *,
    settings: Optional[AppSettings],
    notifications: Optional[BudgetNotifier],
    translate: Optional[TranslateFn],
    currency: str,
    language: str,
) -> None:
    if notifications is None:
        return
    if settings is not None:
        if not getattr(settings, "notifications_enabled", True):
            return
        if not getattr(settings, "budget_alerts", True):
            return
    percent = budget.percent_used
    level = 0
    if percent >= 100:
        level = 100
    elif percent >= 80:
        level = 80
    if level == 0:
        if budget.last_alert_level != 0:
            await budgets.save(
                budget.model_copy(
                    update={"last_alert_level": 0, "updated_at": _utc_now()}
                )
            )
        return
    if level <= budget.last_alert_level:
        return

    tr = translate
    if tr is None:
        def tr(key: str, lang: str = "ru", **kwargs: object) -> str:
            try:
                from lib.infrastructure.services.localization import t

                text = t(str(key), lang)
                return text.format(**kwargs) if kwargs else text
            except Exception:  # noqa: BLE001
                return str(key)
    if level == 80:
        body = tr(
            "notifications.budget_80",
            language,
            category=budget.category_id,
            remaining=str(budget.remaining),
            currency=currency,
        )
        title = tr("notify.budget_80_title", language)
    else:
        body = tr(
            "notifications.budget_100",
            language,
            category=budget.category_id,
            spent=str(budget.spent),
            limit=str(budget.amount_limit),
            currency=currency,
        )
        title = tr("notify.budget_100_title", language)

    kind = None
    try:
        from lib.infrastructure.services.notification_service import NotificationKind

        kind = (
            NotificationKind.BUDGET_OVER
            if level == 100
            else NotificationKind.BUDGET_WARNING
        )
    except Exception:  # noqa: BLE001
        kind = None
    notifications.push(
        title,
        body,
        kind=kind,
        related_id=budget.id,
    )
    await budgets.save(
        budget.model_copy(update={"last_alert_level": level, "updated_at": _utc_now()})
    )


async def _sum_expenses(
    transactions: TransactionRepository,
    category: str,
    month: int,
    year: int,
) -> Decimal:
    start, end = month_bounds(year, month)
    rows = await transactions.list(
        category=category,
        transaction_type=TransactionType.EXPENSE,
        date_from=start,
        date_to=end,
    )
    total = sum((tx.amount for tx in rows if not tx.transfer_id), Decimal("0"))
    return quantize_money(total)
