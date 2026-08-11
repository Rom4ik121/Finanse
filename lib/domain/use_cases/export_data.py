"""Data export use case (interface-level helper)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Optional

from lib.domain.repositories.account_repository import AccountRepository
from lib.domain.repositories.currency_repository import CurrencyRepository
from lib.domain.repositories.debt_repository import DebtRepository
from lib.domain.repositories.goal_repository import GoalRepository
from lib.domain.repositories.settings_repository import SettingsRepository
from lib.domain.repositories.subscription_repository import SubscriptionRepository
from lib.domain.repositories.transaction_repository import TransactionRepository


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _json_default(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat()
    raise TypeError(f"Object of type {type(value)!r} is not JSON serializable")


@dataclass(slots=True)
class ExportResult:
    """Result of an export operation."""

    path: Path
    exported_at: datetime
    counts: dict[str, int]


class ExportDataUseCase:
    """Export core domain data to a JSON file for backup / reporting.

    This is an interface-level helper: it aggregates repository reads and
    writes a portable JSON snapshot. Presentation / file-picker UI lives
    outside the domain layer.
    """

    def __init__(
        self,
        accounts: AccountRepository,
        transactions: TransactionRepository,
        goals: GoalRepository,
        debts: DebtRepository,
        subscriptions: SubscriptionRepository,
        currencies: CurrencyRepository,
        settings: SettingsRepository,
    ) -> None:
        self._accounts = accounts
        self._transactions = transactions
        self._goals = goals
        self._debts = debts
        self._subscriptions = subscriptions
        self._currencies = currencies
        self._settings = settings

    async def execute(
        self,
        export_dir: Path,
        *,
        filename: Optional[str] = None,
    ) -> ExportResult:
        """Write a JSON dump of domain data into ``export_dir``.

        Args:
            export_dir: Target directory (created if missing).
            filename: Optional file name; defaults to a UTC timestamped name.

        Returns:
            :class:`ExportResult` with path and entity counts.
        """
        export_dir.mkdir(parents=True, exist_ok=True)
        exported_at = _utc_now()
        if filename is None:
            filename = f"finanse_export_{exported_at.strftime('%Y%m%dT%H%M%SZ')}.json"

        accounts = await self._accounts.list(active_only=False)
        transactions = await self._transactions.list()
        goals = await self._goals.list(include_completed=True)
        debts = await self._debts.list()
        subscriptions = await self._subscriptions.list(active_only=False)
        currencies = await self._currencies.list_currencies(include_crypto=True)
        rates = await self._currencies.list_rates()
        settings = await self._settings.get()

        payload = {
            "exported_at": exported_at.isoformat(),
            "version": 1,
            "accounts": [a.model_dump(mode="json") for a in accounts],
            "transactions": [t.model_dump(mode="json") for t in transactions],
            "goals": [g.model_dump(mode="json") for g in goals],
            "debts": [d.model_dump(mode="json") for d in debts],
            "subscriptions": [s.model_dump(mode="json") for s in subscriptions],
            "currencies": [c.model_dump(mode="json") for c in currencies],
            "exchange_rates": [r.model_dump(mode="json") for r in rates],
            "settings": settings.model_dump(mode="json"),
        }

        path = export_dir / filename
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default),
            encoding="utf-8",
        )

        return ExportResult(
            path=path,
            exported_at=exported_at,
            counts={
                "accounts": len(accounts),
                "transactions": len(transactions),
                "goals": len(goals),
                "debts": len(debts),
                "subscriptions": len(subscriptions),
                "currencies": len(currencies),
                "exchange_rates": len(rates),
            },
        )
