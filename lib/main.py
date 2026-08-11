"""Application bootstrap: logging, DB, DI, background tasks, Flet."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any, Optional

import flet as ft

from lib.core.config import AppConfig, get_default_config
from lib.core.database import init_db
from lib.core.dependencies import Container, build_container
from lib.core.logging_config import setup_logging
from lib.presentation.app import FinanseApp

logger = logging.getLogger("finanse.main")

_rate_task: Optional[asyncio.Future[Any]] = None
_reminder_task: Optional[asyncio.Future[Any]] = None


async def _seed_if_needed(container: Container) -> None:
    """Ensure currencies, settings, and cash account exist (idempotent)."""
    try:
        from pathlib import Path

        currencies_path = (
            Path(__file__).resolve().parents[1] / "assets" / "data" / "currencies.json"
        )
        if (
            container.currency_repository is not None
            and hasattr(container.currency_repository, "seed_from_json")
            and currencies_path.exists()
        ):
            # Upsert on every launch so catalog additions (e.g. top crypto) appear.
            count = await container.currency_repository.seed_from_json(
                currencies_path
            )
            logger.info("Synced %d currencies from JSON", count)
    except Exception:  # noqa: BLE001
        logger.exception("Currency seed failed")

    try:
        if container.get_settings is not None:
            await container.get_settings.execute()
    except Exception:  # noqa: BLE001
        logger.exception("Settings seed/load failed")

    try:
        await _seed_categories(container)
    except Exception:  # noqa: BLE001
        logger.exception("Category seed failed")

    try:
        if container.list_accounts is None or container.create_account is None:
            return
        accounts = await container.list_accounts.execute()
        if accounts:
            # One account still on RUB while settings are UZS (etc.) → retarget.
            from lib.domain.use_cases.align_currencies import (
                align_sole_account_currency,
            )

            if await align_sole_account_currency(container):
                logger.info("Sole account currency aligned with settings")
            return
        from lib.domain.entities.account import Account
        from lib.domain.entities.currency_codes import normalize_currency_code
        from lib.infrastructure.services.localization import t

        currency = container.config.default_currency
        lang = container.config.language
        if container.get_settings is not None:
            settings = await container.get_settings.execute()
            currency = normalize_currency_code(settings.default_currency)
            lang = settings.language

        await container.create_account.execute(
            Account(
                name=t("account.default_cash", lang),
                currency=currency,
                initial_balance=0,
                balance=0,
                icon="wallet",
                color="#2E7D32",
            )
        )
        logger.info("Created default cash account (%s)", currency)
    except Exception:  # noqa: BLE001
        logger.exception("Default account seed failed")


async def _seed_categories(container: Container) -> None:
    """Insert default categories when the catalog is empty."""
    if container.list_categories is None or container.create_category is None:
        return
    existing = await container.list_categories.execute(active_only=False)
    if existing:
        return
    from lib.core.config import DEFAULT_CATEGORY_SEED
    from lib.domain.entities.category import Category, CategoryKind
    from lib.infrastructure.services.localization import localize_category_name

    lang = container.config.language
    if container.get_settings is not None:
        try:
            settings = await container.get_settings.execute()
            if settings is not None:
                lang = settings.language
        except Exception:  # noqa: BLE001
            pass

    for name, kind, icon, color in DEFAULT_CATEGORY_SEED:
        await container.create_category.execute(
            Category(
                name=localize_category_name(name, lang),
                kind=CategoryKind(kind),
                icon=icon,
                color=color,
                is_system=True,
            )
        )
    logger.info("Seeded %d default categories", len(DEFAULT_CATEGORY_SEED))

async def _exchange_rate_loop(container: Container) -> None:
    """Periodically refresh FX rates while the app is running."""
    while True:
        minutes = container.config.exchange_update_interval_minutes
        try:
            settings = (
                await container.get_settings.execute()
                if container.get_settings
                else None
            )
            if settings is not None:
                minutes = settings.exchange_update_interval_minutes
                base = settings.default_currency
            else:
                base = container.config.default_currency
            if container.update_exchange_rates is not None:
                await container.update_exchange_rates.execute(base=base)
                logger.info("Exchange rates updated (base=%s)", base)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001
            logger.warning("Background exchange-rate update failed: %s", exc)
        await asyncio.sleep(max(5, minutes) * 60)


def _parse_hhmm(value: str) -> tuple[int, int]:
    parts = (value or "09:00").split(":")
    return int(parts[0]), int(parts[1])


async def _reminder_loop(container: Container) -> None:
    """Daily in-app reminder sweep for debts and subscriptions."""
    last_run_date: Optional[str] = None
    while True:
        try:
            settings = (
                await container.get_settings.execute()
                if container.get_settings
                else None
            )
            if settings and settings.notifications_enabled:
                hour, minute = _parse_hhmm(settings.reminder_time)
                now_local = datetime.now()
                stamp = now_local.strftime("%Y-%m-%d")
                if (
                    now_local.hour == hour
                    and now_local.minute == minute
                    and last_run_date != stamp
                ):
                    notifier = container.notification_service
                    if notifier is not None:
                        if settings.debt_reminders and container.list_debts:
                            debts = await container.list_debts.execute()
                            notifier.schedule_debt_reminders(debts)
                        if settings.subscription_reminders and container.list_subscriptions:
                            subs = await container.list_subscriptions.execute(
                                active_only=True
                            )
                            notifier.schedule_subscription_reminders(subs)
                        pending = notifier.list_pending()
                        logger.info(
                            "Reminder sweep created/pending=%d", len(pending)
                        )
                    last_run_date = stamp
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001
            logger.exception("Reminder loop failed")
        await asyncio.sleep(30)


async def _flet_main(page: ft.Page) -> None:
    """Async Flet target: wire container, background task, UI."""
    global _rate_task, _reminder_task

    from lib.infrastructure.services.biometric import (
        mobile_runtime,
        set_local_auth_service,
    )

    _local_auth_control = None
    if mobile_runtime():
        try:
            from flet_local_auth import FinanseLocalAuth

            _local_auth_control = FinanseLocalAuth()
            page.add(_local_auth_control)
            set_local_auth_service(_local_auth_control)
            logger.info("Mobile biometric service registered")
        except Exception:  # noqa: BLE001
            logger.exception("Failed to register mobile biometric service")

    config = get_default_config()
    setup_logging(log_dir=config.log_dir)
    init_db(config)
    container = build_container(config, init_database=False)
    await _seed_if_needed(container)

    if _rate_task is None or _rate_task.done():
        _rate_task = page.run_task(_exchange_rate_loop, container)
    if _reminder_task is None or _reminder_task.done():
        _reminder_task = page.run_task(_reminder_loop, container)

    try:
        if container.process_due_subscriptions is not None:
            await container.process_due_subscriptions.execute()
    except Exception:  # noqa: BLE001
        logger.exception("process_due_subscriptions failed")

    # Eager reminder scheduling on startup (not only at reminder_time).
    try:
        settings = await container.get_settings.execute()
        notifier = container.notification_service
        if settings.notifications_enabled and notifier is not None:
            if settings.debt_reminders and container.list_debts:
                notifier.schedule_debt_reminders(await container.list_debts.execute())
            if settings.subscription_reminders and container.list_subscriptions:
                notifier.schedule_subscription_reminders(
                    await container.list_subscriptions.execute(active_only=True)
                )
    except Exception:  # noqa: BLE001
        logger.exception("Startup reminder scheduling failed")

    app = FinanseApp(page, container)
    await app.start()


def run(config: Optional[AppConfig] = None) -> None:
    """Launch the Finanse desktop / mobile Flet application.

    Prefer ``flet run --android|--ios|--web --host 0.0.0.0 --port 8550 main.py``
    for phone testing — the CLI sets ``FLET_*`` env vars that Flet reads.

    Optional manual overrides:

    * ``FLET_VIEW=web|android|ios|desktop``
    * ``FLET_HOST`` / ``FLET_PORT``
    """
    import os

    cfg = config or get_default_config()
    setup_logging(log_dir=cfg.log_dir)
    logger.info("Starting Finanse (data_dir=%s)", cfg.data_dir)

    # Windows/uvicorn cannot bind host="*"; normalize to 0.0.0.0.
    for key in ("FLET_SERVER_IP", "FLET_HOST"):
        value = (os.environ.get(key) or "").strip()
        if value in {"*", "all"}:
            os.environ[key] = "0.0.0.0"

    # When launched via ``flet run --android/--web``, let Flet consume CLI env.
    if os.environ.get("FLET_FORCE_WEB_SERVER", "").lower() in {"1", "true", "yes"}:
        logger.info(
            "Flet mobile/web server mode (host=%s port=%s)",
            os.environ.get("FLET_SERVER_IP"),
            os.environ.get("FLET_SERVER_PORT"),
        )
        ft.run(_flet_main)
        return

    view_raw = (os.environ.get("FLET_VIEW") or "desktop").strip().lower()
    host = os.environ.get("FLET_HOST")
    port_raw = os.environ.get("FLET_PORT", "").strip()
    port = int(port_raw) if port_raw.isdigit() else 0

    kwargs: dict[str, Any] = {}
    if view_raw in {"web", "browser"}:
        kwargs["view"] = ft.AppView.WEB_BROWSER
        kwargs["host"] = host or "0.0.0.0"
        kwargs["port"] = port or 8550
    elif view_raw in {"android", "ios", "mobile"}:
        kwargs["view"] = ft.AppView.WEB_BROWSER
        kwargs["host"] = host or "0.0.0.0"
        kwargs["port"] = port or 8550
    elif view_raw == "hidden":
        kwargs["view"] = ft.AppView.FLET_APP_HIDDEN

    if kwargs.get("host") in {"*", "all"}:
        kwargs["host"] = "0.0.0.0"

    logger.info(
        "Flet launch view=%s host=%s port=%s",
        kwargs.get("view", ft.AppView.FLET_APP),
        kwargs.get("host"),
        kwargs.get("port") or "auto",
    )
    ft.run(_flet_main, **kwargs)
