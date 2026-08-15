"""Fill the FinWise SQLite DB with rich multi-year demo data for UI stress tests.

Usage (from project root)::

    python scripts/seed_demo_data.py --wipe
    python scripts/seed_demo_data.py --wipe --scale large
    python scripts/seed_demo_data.py --wipe --currency UZS

Default target is the real user DB
(``%LOCALAPPDATA%\\finanse\\finanse\\finanse.db`` on Windows).
Close the app before wiping/seeding.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import random
import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.core.config import (  # noqa: E402
    DEFAULT_CATEGORY_SEED,
    AppConfig,
    get_default_config,
)
from lib.core.database import get_session_factory, init_db, reset_engine  # noqa: E402
from lib.core.dependencies import build_container  # noqa: E402
from lib.core.logging_config import setup_logging  # noqa: E402
from lib.domain.entities.account import Account  # noqa: E402
from lib.domain.entities.category import Category, CategoryKind  # noqa: E402
from lib.domain.entities.currency import ExchangeRate  # noqa: E402
from lib.domain.entities.debt import Debt, DebtDirection, DebtStatus  # noqa: E402
from lib.domain.entities.goal import Goal  # noqa: E402
from lib.domain.entities.subscription import Periodicity, Subscription  # noqa: E402
from lib.domain.entities.transaction import Transaction, TransactionType  # noqa: E402
from lib.infrastructure.services.data_reset_service import DataResetService  # noqa: E402

logger = logging.getLogger("finanse.seed_demo")

EXPENSE_CATS = [
    "Еда",
    "Транспорт",
    "Жильё",
    "Коммунальные",
    "Здоровье",
    "Развлечения",
    "Одежда",
    "Образование",
    "Подарки",
    "Инвестиции",
    "Прочее",
]
INCOME_CATS = ["Зарплата", "Подарки", "Инвестиции", "Прочее"]

COMMENTS = [
    "Супермаркет",
    "Кафе",
    "Такси",
    "Метро",
    "Аптека",
    "Онлайн",
    "Подписка",
    "Зарплата",
    "Премия",
    "Аренда",
    "Коммуналка",
    "Кино",
    "Спортзал",
    "Одежда",
    "Подарок",
    "Командировка",
    "Ремонт",
    "Топливо",
    "Интернет",
    "Мобильная связь",
    "",
    "",
    "",
]

TAGS_POOL = [
    ["еда"],
    ["работа"],
    ["дом"],
    ["семья"],
    ["отпуск"],
    ["здоровье"],
    ["авто"],
    ["онлайн", "подписка"],
    [],
    [],
    [],
]

# Rough FX for demo rates (quote units per 1 USD).
DEMO_USD_BOOK = {
    "UZS": Decimal("12500"),
    "RUB": Decimal("92"),
    "EUR": Decimal("0.92"),
    "KZT": Decimal("480"),
    "GBP": Decimal("0.79"),
    "BTC": Decimal("0.000015"),  # ~1 BTC = 66666 USD → USD→BTC
}


def _utc(year: int, month: int, day: int, hour: int = 12, minute: int = 0) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=timezone.utc)


def _scale_config(scale: str) -> dict[str, int]:
    if scale == "small":
        return {"days_span": 400, "txs_per_day": 2, "extra_accounts": 1}
    if scale == "large":
        return {"days_span": 1200, "txs_per_day": 6, "extra_accounts": 3}
    return {"days_span": 900, "txs_per_day": 4, "extra_accounts": 2}


async def _seed_currencies(container, root: Path) -> int:
    path = root / "assets" / "data" / "currencies.json"
    if container.currency_repository is None or not path.exists():
        return 0
    return await container.currency_repository.seed_from_json(path)


async def _seed_categories(container) -> int:
    count = 0
    for name, kind, icon, color in DEFAULT_CATEGORY_SEED:
        try:
            await container.create_category.execute(
                Category(
                    name=name,
                    kind=CategoryKind(kind),
                    icon=icon,
                    color=color,
                    is_system=True,
                )
            )
            count += 1
        except Exception:  # noqa: BLE001 - already exists
            pass
    for name, kind, icon, color in (
        ("Долг", "both", "handshake", "#F57C00"),
        ("Долг (выдача)", "expense", "handshake", "#E65100"),
    ):
        try:
            await container.create_category.execute(
                Category(
                    name=name,
                    kind=CategoryKind(kind),
                    icon=icon,
                    color=color,
                    is_system=True,
                )
            )
            count += 1
        except Exception:  # noqa: BLE001
            pass
    return count


async def _seed_settings(container, *, currency: str, language: str = "ru") -> None:
    settings = await container.get_settings.execute()
    await container.update_settings.execute(
        settings.model_copy(
            update={
                "default_currency": currency.upper(),
                "language": language,
                "theme": "dark",
                "notifications_enabled": True,
                "debt_reminders": True,
                "subscription_reminders": True,
                "goal_milestones": True,
                "reminder_time": "09:00",
            }
        )
    )


async def _seed_rates(container, base: str) -> int:
    now = datetime.now(timezone.utc)
    rates: list[ExchangeRate] = []
    # USD book + inverses for converter pivots.
    for quote, units_per_usd in DEMO_USD_BOOK.items():
        rates.append(
            ExchangeRate(
                base="USD",
                quote=quote,
                rate=units_per_usd,
                updated_at=now,
            )
        )
        if units_per_usd > 0:
            rates.append(
                ExchangeRate(
                    base=quote,
                    quote="USD",
                    rate=Decimal("1") / units_per_usd,
                    updated_at=now,
                )
            )
    # Also store base→quote for the app default.
    base = base.upper()
    if base != "USD" and base in DEMO_USD_BOOK:
        base_per_usd = DEMO_USD_BOOK[base]
        for quote, units_per_usd in DEMO_USD_BOOK.items():
            if quote == base:
                continue
            # 1 base = (units_per_usd / base_per_usd) quote
            rate = units_per_usd / base_per_usd
            rates.append(
                ExchangeRate(
                    base=base,
                    quote=quote,
                    rate=rate,
                    updated_at=now,
                )
            )
        rates.append(
            ExchangeRate(
                base=base,
                quote="USD",
                rate=Decimal("1") / base_per_usd,
                updated_at=now,
            )
        )
    saved = await container.update_exchange_rates.execute(rates=rates)
    return len(saved)


def _account_specs(base: str, extra: int) -> list[dict]:
    specs = [
        {
            "name": "Наличные",
            "currency": base,
            "balance": "2500000" if base == "UZS" else "85000",
            "icon": "wallet",
            "color": "#2E7D32",
        },
        {
            "name": "Карта Uzcard",
            "currency": base,
            "balance": "12000000" if base == "UZS" else "320000",
            "icon": "credit_card",
            "color": "#1565C0",
        },
        {
            "name": "USD Wallet",
            "currency": "USD",
            "balance": "1850.50",
            "icon": "payments",
            "color": "#00897B",
        },
        {
            "name": "RUB счёт",
            "currency": "RUB",
            "balance": "145000",
            "icon": "account_balance",
            "color": "#6A1B9A",
        },
    ]
    extras = [
        {
            "name": "Накопления",
            "currency": base,
            "balance": "5000000" if base == "UZS" else "150000",
            "icon": "savings",
            "color": "#00838F",
        },
        {
            "name": "Инвест-счёт",
            "currency": "USD",
            "balance": "4200",
            "icon": "trending_up",
            "color": "#4527A0",
        },
        {
            "name": "Кошелёк EUR",
            "currency": "EUR",
            "balance": "780",
            "icon": "account_balance_wallet",
            "color": "#EF6C00",
        },
    ]
    return specs + extras[: max(0, extra)]


async def _create_accounts(container, specs: list[dict]) -> list[Account]:
    accounts: list[Account] = []
    for spec in specs:
        amount = Decimal(spec["balance"])
        acc = await container.create_account.execute(
            Account(
                name=spec["name"],
                currency=spec["currency"],
                initial_balance=amount,
                balance=amount,
                icon=spec["icon"],
                color=spec["color"],
                is_active=True,
            )
        )
        accounts.append(acc)
        logger.info("Account %s (%s) = %s", acc.name, acc.currency, acc.balance)
    return accounts


def _salary_for(currency: str) -> Decimal:
    if currency == "UZS":
        return Decimal(str(random.randint(8_000_000, 14_000_000)))
    if currency == "USD":
        return Decimal(str(random.randint(2200, 4500)))
    if currency == "EUR":
        return Decimal(str(random.randint(1800, 3200)))
    return Decimal(str(random.randint(80_000, 180_000)))


def _expense_amount(currency: str, category: str) -> Decimal:
    if currency == "UZS":
        ranges = {
            "Еда": (35_000, 450_000),
            "Транспорт": (8_000, 120_000),
            "Жильё": (1_500_000, 4_500_000),
            "Коммунальные": (200_000, 900_000),
            "Здоровье": (40_000, 800_000),
            "Развлечения": (50_000, 600_000),
            "Одежда": (100_000, 1_500_000),
            "Образование": (150_000, 2_000_000),
            "Подарки": (50_000, 1_000_000),
            "Инвестиции": (200_000, 3_000_000),
            "Прочее": (10_000, 350_000),
        }
    elif currency == "USD":
        ranges = {
            "Еда": (5, 90),
            "Транспорт": (2, 40),
            "Жильё": (400, 1400),
            "Коммунальные": (40, 180),
            "Здоровье": (10, 200),
            "Развлечения": (8, 120),
            "Одежда": (20, 250),
            "Образование": (30, 400),
            "Подарки": (10, 150),
            "Инвестиции": (50, 800),
            "Прочее": (3, 80),
        }
    else:
        ranges = {
            "Еда": (200, 4500),
            "Транспорт": (50, 1500),
            "Жильё": (15000, 65000),
            "Коммунальные": (1500, 9000),
            "Здоровье": (300, 8000),
            "Развлечения": (400, 6000),
            "Одежда": (1000, 15000),
            "Образование": (1500, 20000),
            "Подарки": (500, 10000),
            "Инвестиции": (2000, 40000),
            "Прочее": (100, 3000),
        }
    lo, hi = ranges.get(category, (10, 100))
    # Keep 2 decimals for non-UZS; whole sums for UZS look natural.
    if currency == "UZS":
        return Decimal(str(random.randint(lo, hi)))
    cents = random.randint(lo * 100, hi * 100)
    return Decimal(cents) / Decimal("100")


def _build_transactions(
    accounts: list[Account],
    *,
    days_span: int,
    txs_per_day: int,
    end: datetime | None = None,
) -> list[Transaction]:
    end = end or datetime.now(timezone.utc)
    start = end - timedelta(days=days_span)
    rng = random.Random(42)
    txs: list[Transaction] = []

    # Prefer salary-funded wallets for daily noise; keep savings / FX thinner.
    primary = [a for a in accounts if a.name in {"Наличные", "Карта Uzcard", "RUB счёт"}]
    if not primary:
        primary = accounts[:2]
    savings = [a for a in accounts if "Накоп" in a.name or "Инвест" in a.name]
    fx_accounts = [a for a in accounts if a.currency in {"USD", "EUR"}]
    daily_accounts = primary

    day = start
    while day <= end:
        # Monthly salary on the 1st / 5th for primary accounts.
        if day.day in (1, 5):
            for acc in daily_accounts:
                if acc.currency == "RUB" and day.day != 1:
                    continue
                txs.append(
                    Transaction(
                        account_id=acc.id,
                        amount=_salary_for(acc.currency),
                        category="Зарплата",
                        tags=["работа", "доход"],
                        date=day.replace(hour=9, minute=15),
                        comment="Зарплата",
                        type=TransactionType.INCOME,
                        currency=acc.currency,
                    )
                )
        if day.day == 15 and fx_accounts:
            acc = fx_accounts[0]
            txs.append(
                Transaction(
                    account_id=acc.id,
                    amount=_salary_for(acc.currency) / Decimal("2"),
                    category="Зарплата",
                    tags=["фриланс"],
                    date=day.replace(hour=11, minute=0),
                    comment="Фриланс / контракт",
                    type=TransactionType.INCOME,
                    currency=acc.currency,
                )
            )
        # Occasional top-up to savings (not spent daily).
        if day.day == 20 and savings:
            acc = savings[0]
            top = (
                Decimal(str(rng.randint(500_000, 2_000_000)))
                if acc.currency == "UZS"
                else Decimal(str(rng.randint(50, 300)))
            )
            txs.append(
                Transaction(
                    account_id=acc.id,
                    amount=top,
                    category="Накопление",
                    tags=["накопления"],
                    date=day.replace(hour=10, minute=0),
                    comment="Пополнение накоплений",
                    type=TransactionType.INCOME,
                    currency=acc.currency,
                )
            )

        # Daily expenses on primary wallets only.
        if rng.random() > 0.08:
            n = rng.randint(max(1, txs_per_day - 1), txs_per_day + 1)
            for _i in range(n):
                # Weight toward Uzcard / cash.
                acc = rng.choice(daily_accounts)
                if acc.currency == "RUB" and rng.random() < 0.55:
                    continue
                category = rng.choice(EXPENSE_CATS)
                if category in {"Жильё", "Коммунальные"} and day.day not in (2, 3, 28):
                    continue
                amount = _expense_amount(acc.currency, category)
                # Keep RUB spend modest vs salary.
                if acc.currency == "RUB":
                    amount = min(amount, Decimal("3500"))
                txs.append(
                    Transaction(
                        account_id=acc.id,
                        amount=amount,
                        category=category,
                        tags=list(rng.choice(TAGS_POOL)),
                        date=day.replace(
                            hour=rng.randint(7, 22),
                            minute=rng.randint(0, 59),
                            second=rng.randint(0, 59),
                        ),
                        comment=rng.choice(COMMENTS),
                        type=TransactionType.EXPENSE,
                        currency=acc.currency,
                    )
                )

        # Occasional FX spend (less than income).
        if fx_accounts and rng.random() < 0.08:
            acc = rng.choice(fx_accounts)
            category = rng.choice(["Еда", "Развлечения", "Транспорт", "Прочее"])
            txs.append(
                Transaction(
                    account_id=acc.id,
                    amount=_expense_amount(acc.currency, category),
                    category=category,
                    tags=["travel"] if rng.random() < 0.3 else [],
                    date=day.replace(hour=rng.randint(10, 20), minute=rng.randint(0, 59)),
                    comment=rng.choice(COMMENTS),
                    type=TransactionType.EXPENSE,
                    currency=acc.currency,
                )
            )

        day += timedelta(days=1)

    # Yearly bonus spikes for analytics.
    for year in range(start.year, end.year + 1):
        for month, day_n, label in (
            (1, 10, "Новогодний бонус"),
            (3, 8, "Подарок 8 марта"),
            (12, 25, "Премия / 13-я зарплата"),
        ):
            try:
                when = _utc(year, month, day_n, 14, 0)
            except ValueError:
                continue
            if start <= when <= end:
                acc = daily_accounts[0]
                txs.append(
                    Transaction(
                        account_id=acc.id,
                        amount=_salary_for(acc.currency) * Decimal("0.4"),
                        category="Зарплата",
                        tags=["бонус"],
                        date=when,
                        comment=label,
                        type=TransactionType.INCOME,
                        currency=acc.currency,
                    )
                )

    txs.sort(key=lambda t: t.date)
    return txs


async def _bulk_insert_transactions(container, txs: list[Transaction]) -> int:
    repo = container.transaction_repository
    if repo is None:
        raise RuntimeError("transaction_repository missing")
    batch = 200
    for i in range(0, len(txs), batch):
        chunk = txs[i : i + batch]
        for tx in chunk:
            await repo.create(tx)
        logger.info("Transactions inserted: %s / %s", min(i + batch, len(txs)), len(txs))
    return len(txs)


async def _recalc_all(container, accounts: list[Account]) -> None:
    for acc in accounts:
        updated = await container.recalculate_account_balance.execute(acc.id)
        logger.info("Recalculated %s → %s %s", updated.name, updated.balance, updated.currency)


async def _seed_goals(container, funding_account: Account) -> list[Goal]:
    now = datetime.now(timezone.utc)
    base = funding_account.currency
    specs = [
        ("Отпуск в Турции", "25000000" if base == "UZS" else "2500", 120, 5),
        ("Новый ноутбук", "18000000" if base == "UZS" else "1800", 60, 4),
        ("Подушка безопасности", "50000000" if base == "UZS" else "5000", 365, 5),
        ("Ремонт квартиры", "80000000" if base == "UZS" else "8000", 500, 3),
        ("Курсы / обучение", "5000000" if base == "UZS" else "600", 90, 2),
        ("Авто (первоначальный)", "120000000" if base == "UZS" else "12000", 700, 4),
    ]
    goals: list[Goal] = []
    for name, target, days, priority in specs:
        goal = await container.create_goal.execute(
            Goal(
                name=name,
                target_amount=Decimal(target),
                current_amount=Decimal("0"),
                deadline=now + timedelta(days=days),
                priority=priority,
                category_link="Накопление",
            )
        )
        goals.append(goal)

    # Fund some goals via contributions (same currency as account).
    contributions = [
        (0, "800000" if base == "UZS" else "350"),
        (0, "1200000" if base == "UZS" else "200"),
        (1, "4500000" if base == "UZS" else "900"),
        (2, "15000000" if base == "UZS" else "1500"),
        (4, "900000" if base == "UZS" else "150"),
    ]
    for idx, amount in contributions:
        try:
            await container.contribute_to_goal.execute(
                goals[idx].id,
                Decimal(amount),
                account_id=funding_account.id,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Goal contribute skipped: %s", exc)
    return goals


async def _seed_debts(container, account: Account) -> list[Debt]:
    now = datetime.now(timezone.utc)
    cur = account.currency
    debts_spec = [
        (
            "Банк (кредит)",
            "15000000" if cur == "UZS" else "1500",
            DebtDirection.I_OWE,
            Decimal("18.5"),
            45,
            True,
        ),
        (
            "Алишер",
            "2500000" if cur == "UZS" else "250",
            DebtDirection.I_OWE,
            None,
            10,
            True,
        ),
        (
            "Дима",
            "800000" if cur == "UZS" else "120",
            DebtDirection.OWED_TO_ME,
            None,
            20,
            True,
        ),
        (
            "Микрозайм",
            "3000000" if cur == "UZS" else "400",
            DebtDirection.I_OWE,
            Decimal("24"),
            -20,
            False,
        ),
    ]
    created: list[Debt] = []
    for name, amount, direction, rate, due_offset, with_cash in debts_spec:
        debt = Debt(
            counterparty=name,
            amount=Decimal(amount),
            remaining_amount=Decimal(amount),
            currency=cur,
            direction=direction,
            status=DebtStatus.ACTIVE,
            interest_rate=rate,
            due_date=now + timedelta(days=due_offset),
            started_at=now - timedelta(days=abs(due_offset) + 30),
            comment="Demo debt",
        )
        saved = await container.create_debt.execute(
            debt,
            account_id=account.id if with_cash else None,
        )
        created.append(saved)

    # Partial repay on first debt.
    try:
        pay = Decimal("1500000") if cur == "UZS" else Decimal("200")
        await container.repay_debt.execute(
            created[0].id,
            pay,
            account_id=account.id,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Debt repay skipped: %s", exc)
    return created


async def _seed_subscriptions(container, account: Account) -> list[Subscription]:
    now = datetime.now(timezone.utc)
    cur = account.currency
    specs = [
        ("Netflix", "89000" if cur == "UZS" else "12.99", Periodicity.MONTHLY, "Развлечения", 3),
        ("Spotify", "35000" if cur == "UZS" else "5.99", Periodicity.MONTHLY, "Развлечения", 7),
        ("Yandex Plus", "49900" if cur == "UZS" else "6.50", Periodicity.MONTHLY, "Прочее", 12),
        ("iCloud", "29000" if cur == "UZS" else "2.99", Periodicity.MONTHLY, "Прочее", 18),
        ("Adobe CC", "1200000" if cur == "UZS" else "59.99", Periodicity.YEARLY, "Образование", 40),
        ("Gym", "450000" if cur == "UZS" else "40", Periodicity.MONTHLY, "Здоровье", 1),
        ("VPN", "25000" if cur == "UZS" else "4.99", Periodicity.MONTHLY, "Прочее", 25),
    ]
    items: list[Subscription] = []
    for name, amount, period, category, due_in in specs:
        sub = await container.create_subscription.execute(
            Subscription(
                name=name,
                amount=Decimal(amount),
                currency=cur,
                account_id=account.id,
                category=category,
                periodicity=period,
                next_billing_date=now + timedelta(days=due_in),
                is_active=True,
                comment="Demo subscription",
            )
        )
        items.append(sub)
    return items


async def seed(
    *,
    wipe: bool,
    scale: str,
    currency: str,
    language: str,
) -> None:
    reset_engine()
    config = get_default_config()
    init_db(config)
    factory = get_session_factory(config)

    logger.info("Database: %s", config.db_path)
    if wipe:
        logger.warning("Wiping all tables…")
        DataResetService(config).wipe_all(factory)
        reset_engine()
        init_db(config)

    container = build_container(config, init_database=False)
    cfg = _scale_config(scale)

    n_curr = await _seed_currencies(container, ROOT)
    logger.info("Currencies upserted: %s", n_curr)
    await _seed_settings(container, currency=currency, language=language)
    n_cat = await _seed_categories(container)
    logger.info("Categories created: %s", n_cat)
    n_rates = await _seed_rates(container, currency)
    logger.info("Exchange rates: %s", n_rates)

    accounts = await _create_accounts(
        container, _account_specs(currency.upper(), cfg["extra_accounts"])
    )
    funding = next((a for a in accounts if a.currency.upper() == currency.upper()), accounts[0])

    txs = _build_transactions(
        accounts,
        days_span=cfg["days_span"],
        txs_per_day=cfg["txs_per_day"],
    )
    logger.info("Prepared %s transactions spanning ~%s days", len(txs), cfg["days_span"])
    await _bulk_insert_transactions(container, txs)
    await _recalc_all(container, accounts)

    goals = await _seed_goals(container, funding)
    debts = await _seed_debts(container, funding)
    subs = await _seed_subscriptions(container, funding)

    # Refresh balances after goal/debt cash moves.
    await _recalc_all(container, [funding])

    logger.info(
        "Done. accounts=%s txs≈%s goals=%s debts=%s subs=%s base=%s",
        len(accounts),
        len(txs),
        len(goals),
        len(debts),
        len(subs),
        currency.upper(),
    )
    logger.info("Open FinWise and browse Dashboard / Analytics / Transactions.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed FinWise with demo data")
    parser.add_argument(
        "--wipe",
        action="store_true",
        help="Clear all tables before seeding (close the app first)",
    )
    parser.add_argument(
        "--scale",
        choices=("small", "medium", "large"),
        default="medium",
        help="Data volume (default: medium ≈ 2–4k txs)",
    )
    parser.add_argument(
        "--currency",
        default="UZS",
        help="Default / funding currency (default: UZS)",
    )
    parser.add_argument("--language", default="ru", help="UI language code")
    args = parser.parse_args()

    setup_logging()
    asyncio.run(
        seed(
            wipe=args.wipe,
            scale=args.scale,
            currency=args.currency,
            language=args.language,
        )
    )


if __name__ == "__main__":
    main()
