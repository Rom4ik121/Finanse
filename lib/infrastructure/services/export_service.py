"""Export finances to JSON, CSV, and PDF summary reports."""

from __future__ import annotations

import csv
import json
import logging
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterable, Optional, Sequence

from lib.core.config import AppConfig, get_default_config
from lib.domain.entities.account import Account
from lib.domain.entities.debt import Debt
from lib.domain.entities.goal import Goal
from lib.domain.entities.subscription import Subscription
from lib.domain.entities.transaction import Transaction

logger = logging.getLogger("finanse.infrastructure.services.export")


def _json_default(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if hasattr(value, "value"):
        return value.value
    raise TypeError(f"Object of type {type(value)!r} is not JSON serializable")


class ExportService:
    """Serialize domain data to JSON / CSV / PDF under the export directory."""

    def __init__(self, config: Optional[AppConfig] = None) -> None:
        self._config = config or get_default_config()
        self._config.ensure_directories()

    @property
    def export_dir(self) -> Path:
        return self._config.export_dir

    def export_json(
        self,
        data: dict[str, Any] | Sequence[Any],
        filename: str = "export.json",
    ) -> Path:
        """Write ``data`` as pretty JSON and return the file path."""
        path = self._resolve(filename)
        try:
            path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2, default=_json_default),
                encoding="utf-8",
            )
            logger.info("Exported JSON to %s", path)
            return path
        except OSError:
            logger.exception("Failed to write JSON export %s", path)
            raise

    def export_transactions_csv(
        self,
        transactions: Iterable[Transaction],
        filename: str = "transactions.csv",
    ) -> Path:
        """Export transactions to CSV."""
        path = self._resolve(filename)
        fieldnames = [
            "id",
            "account_id",
            "amount",
            "category",
            "tags",
            "date",
            "comment",
            "type",
            "currency",
            "goal_id",
            "debt_id",
            "created_at",
            "updated_at",
        ]
        try:
            with path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fieldnames)
                writer.writeheader()
                for tx in transactions:
                    writer.writerow(
                        {
                            "id": tx.id,
                            "account_id": tx.account_id,
                            "amount": str(tx.amount),
                            "category": tx.category,
                            "tags": "|".join(tx.tags),
                            "date": tx.date.isoformat(),
                            "comment": tx.comment,
                            "type": tx.type.value if hasattr(tx.type, "value") else tx.type,
                            "currency": tx.currency,
                            "goal_id": tx.goal_id or "",
                            "debt_id": getattr(tx, "debt_id", None) or "",
                            "created_at": tx.created_at.isoformat(),
                            "updated_at": tx.updated_at.isoformat(),
                        }
                    )
            logger.info("Exported transactions CSV to %s", path)
            return path
        except OSError:
            logger.exception("Failed to write CSV export %s", path)
            raise

    def export_full_json(
        self,
        *,
        accounts: Sequence[Account] = (),
        transactions: Sequence[Transaction] = (),
        goals: Sequence[Goal] = (),
        debts: Sequence[Debt] = (),
        subscriptions: Sequence[Subscription] = (),
        filename: str = "finanse_backup_data.json",
    ) -> Path:
        """Export a structured JSON dump of core entities."""
        payload = {
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "accounts": [a.model_dump(mode="json") for a in accounts],
            "transactions": [t.model_dump(mode="json") for t in transactions],
            "goals": [g.model_dump(mode="json") for g in goals],
            "debts": [d.model_dump(mode="json") for d in debts],
            "subscriptions": [s.model_dump(mode="json") for s in subscriptions],
        }
        return self.export_json(payload, filename=filename)

    def export_summary_pdf(
        self,
        *,
        accounts: Sequence[Account] = (),
        transactions: Sequence[Transaction] = (),
        goals: Sequence[Goal] = (),
        debts: Sequence[Debt] = (),
        subscriptions: Sequence[Subscription] = (),
        filename: str = "summary_report.pdf",
        title: str = "Finanse Summary Report",
    ) -> Path:
        """Generate a simple PDF summary using reportlab."""
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.units import cm
            from reportlab.pdfgen import canvas
        except ImportError as exc:
            logger.error("reportlab is required for PDF export")
            raise RuntimeError(
                "reportlab is not installed; add it to dependencies for PDF export"
            ) from exc

        path = self._resolve(filename)
        income = sum(
            (t.amount for t in transactions if str(getattr(t.type, "value", t.type)) == "income"),
            Decimal("0"),
        )
        expense = sum(
            (t.amount for t in transactions if str(getattr(t.type, "value", t.type)) == "expense"),
            Decimal("0"),
        )
        total_balance = sum((a.balance for a in accounts), Decimal("0"))
        active_debts = [d for d in debts if str(getattr(d.status, "value", d.status)) == "active"]
        debt_remaining = sum((d.remaining_amount for d in active_debts), Decimal("0"))
        active_subs = [s for s in subscriptions if s.is_active]
        open_goals = [g for g in goals if not g.is_completed]

        try:
            c = canvas.Canvas(str(path), pagesize=A4)
            width, height = A4
            y = height - 2 * cm

            c.setFont("Helvetica-Bold", 16)
            c.drawString(2 * cm, y, title)
            y -= 1 * cm
            c.setFont("Helvetica", 10)
            c.drawString(
                2 * cm,
                y,
                f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
            )
            y -= 1.2 * cm

            lines = [
                f"Accounts: {len(accounts)}  |  Total balance: {total_balance}",
                f"Transactions: {len(transactions)}  |  Income: {income}  |  Expense: {expense}",
                f"Net (income - expense): {income - expense}",
                f"Active goals: {len(open_goals)} / {len(goals)}",
                f"Active debts: {len(active_debts)}  |  Remaining: {debt_remaining}",
                f"Active subscriptions: {len(active_subs)}",
            ]
            c.setFont("Helvetica", 11)
            for line in lines:
                c.drawString(2 * cm, y, line)
                y -= 0.7 * cm

            y -= 0.5 * cm
            c.setFont("Helvetica-Bold", 12)
            c.drawString(2 * cm, y, "Accounts")
            y -= 0.6 * cm
            c.setFont("Helvetica", 10)
            for account in accounts[:20]:
                if y < 2 * cm:
                    c.showPage()
                    y = height - 2 * cm
                    c.setFont("Helvetica", 10)
                c.drawString(
                    2 * cm,
                    y,
                    f"- {account.name}: {account.balance} {account.currency}",
                )
                y -= 0.5 * cm

            if open_goals:
                y -= 0.4 * cm
                c.setFont("Helvetica-Bold", 12)
                c.drawString(2 * cm, y, "Goals")
                y -= 0.6 * cm
                c.setFont("Helvetica", 10)
                for goal in open_goals[:15]:
                    if y < 2 * cm:
                        c.showPage()
                        y = height - 2 * cm
                        c.setFont("Helvetica", 10)
                    ratio = goal.progress_ratio
                    c.drawString(
                        2 * cm,
                        y,
                        f"- {goal.name}: {goal.current_amount}/{goal.target_amount} ({ratio:.0%})",
                    )
                    y -= 0.5 * cm

            c.save()
            logger.info("Exported PDF summary to %s", path)
            return path
        except Exception:
            logger.exception("Failed to write PDF export %s", path)
            raise

    def _resolve(self, filename: str) -> Path:
        path = Path(filename)
        if not path.is_absolute():
            path = self.export_dir / path.name
        path.parent.mkdir(parents=True, exist_ok=True)
        return path
