"""Create database tables and seed currencies, settings, and cash account."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

# Allow running as ``python scripts/migrate.py`` from project root.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.core.config import get_default_config  # noqa: E402
from lib.core.database import get_session, init_db  # noqa: E402
from lib.core.logging_config import setup_logging  # noqa: E402
from lib.infrastructure.db_models import (  # noqa: E402
    AccountModel,
    CurrencyModel,
    SettingsModel,
)

logger = logging.getLogger("finanse.migrate")


def _currencies_path() -> Path:
    return ROOT / "assets" / "data" / "currencies.json"


def seed_currencies(session) -> int:
    """Upsert currency definitions from ``assets/data/currencies.json``."""
    path = _currencies_path()
    if not path.exists():
        logger.warning("currencies.json not found at %s", path)
        return 0

    payload = json.loads(path.read_text(encoding="utf-8"))
    count = 0
    for row in payload:
        code = str(row["code"]).upper()
        name_ru = row.get("name_ru") or row.get("name") or code
        name_en = row.get("name_en") or row.get("name") or code
        name = name_ru or name_en
        symbol = row.get("symbol") or code
        is_crypto = bool(row.get("is_crypto", False))
        existing = session.get(CurrencyModel, code)
        if existing is None:
            session.add(
                CurrencyModel(
                    code=code,
                    name=name,
                    name_ru=name_ru,
                    name_en=name_en,
                    symbol=symbol,
                    is_crypto=is_crypto,
                )
            )
        else:
            existing.name = name
            existing.name_ru = name_ru
            existing.name_en = name_en
            existing.symbol = symbol
            existing.is_crypto = is_crypto
        count += 1
    return count


def seed_settings(session, *, default_currency: str = "RUB") -> None:
    """Ensure the default settings row exists."""
    existing = session.get(SettingsModel, "default")
    if existing is not None:
        return
    session.add(
        SettingsModel(
            id="default",
            default_currency=default_currency,
            theme="dark",
            language="ru",
            exchange_update_interval_minutes=60,
            notifications_enabled=True,
            subscription_reminders=True,
            debt_reminders=True,
            goal_milestones=True,
            reminder_time="09:00",
            biometric_enabled=False,
        )
    )


def seed_cash_account(session, *, currency: str = "RUB") -> None:
    """Create a default cash account when none exist."""
    from sqlalchemy import select

    has_any = session.scalar(select(AccountModel.id).limit(1))
    if has_any:
        return

    from uuid import uuid4

    session.add(
        AccountModel(
            id=str(uuid4()),
            name="Наличные",
            currency=currency,
            balance=0,
            initial_balance=0,
            icon="wallet",
            color="#2E7D32",
            is_active=True,
        )
    )


def migrate(*, echo: bool = False) -> None:
    """Initialize schema and seed baseline data."""
    config = get_default_config()
    setup_logging(log_dir=config.log_dir)
    logger.info("Migrating database at %s", config.db_path)

    init_db(config, echo=echo)

    with get_session(config) as session:
        n = seed_currencies(session)
        seed_settings(session, default_currency=config.default_currency)
        seed_cash_account(session, currency=config.default_currency)
        logger.info("Seeded %d currencies, settings, and default account (if needed)", n)

    logger.info("Migration complete")


def main() -> None:
    parser = argparse.ArgumentParser(description="Finanse DB migration / seed")
    parser.add_argument("--echo", action="store_true", help="Echo SQL statements")
    args = parser.parse_args()
    migrate(echo=args.echo)


if __name__ == "__main__":
    main()
