"""Small presentation helpers shared across pages and widgets."""

from __future__ import annotations

import asyncio
from datetime import datetime
from decimal import Decimal
from typing import Any, Awaitable, Callable, Optional

import flet as ft

from lib.infrastructure.services.localization import t


def tr(key: str, lang: str = "ru", *, default: str | None = None, **kwargs: Any) -> str:
    """Translate ``key`` for the given language with optional format kwargs."""
    text = t(key, lang, default=default)
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, ValueError):
            return text
    return text


def format_money(
    amount: Decimal | float | int | str,
    currency: str = "RUB",
    *,
    signed: bool = False,
) -> str:
    """Format a monetary amount for display."""
    value = Decimal(str(amount))
    quantized = value.quantize(Decimal("0.01"))
    prefix = ""
    if signed:
        if quantized > 0:
            prefix = "+"
        elif quantized < 0:
            prefix = "−"
            quantized = abs(quantized)
    return f"{prefix}{quantized:,.2f} {currency}".replace(",", " ")


def format_date(dt: datetime | None, *, with_time: bool = False) -> str:
    """Format a UTC datetime for local-friendly display."""
    if dt is None:
        return "—"
    if with_time:
        return dt.strftime("%d.%m.%Y %H:%M")
    return dt.strftime("%d.%m.%Y")


def run_async(
    page: ft.Page,
    handler: Callable[..., Awaitable[Any]],
    *args: Any,
    **kwargs: Any,
) -> None:
    """Schedule an async handler on the page event loop (Flet 0.83+)."""
    if hasattr(page, "run_task"):
        page.run_task(handler, *args, **kwargs)
        return
    asyncio.create_task(handler(*args, **kwargs))


def safe_update(control: ft.Control) -> None:
    """Call ``control.update()`` only when the control is mounted."""
    try:
        if getattr(control, "page", None) is not None:
            control.update()
    except Exception:  # noqa: BLE001
        pass


def snack(
    page: ft.Page,
    message: str,
    *,
    error: bool = False,
) -> None:
    """Show a short SnackBar message."""
    page.show_dialog(
        ft.SnackBar(
            content=ft.Text(
                message,
                color=ft.Colors.ON_ERROR if error else ft.Colors.ON_PRIMARY,
            ),
            bgcolor=ft.Colors.ERROR if error else ft.Colors.PRIMARY,
            behavior=ft.SnackBarBehavior.FLOATING,
            shape=ft.RoundedRectangleBorder(radius=14),
        )
    )


def account_icon(name: str | None) -> ft.IconData:
    """Map stored account icon keys to Flet Icons."""
    from lib.presentation.icon_registry import resolve_icon

    return resolve_icon(name, default="wallet")


def category_icon(name: str | None) -> ft.IconData:
    """Map stored category icon keys to Flet Icons."""
    from lib.presentation.icon_registry import resolve_icon

    return resolve_icon(name, default="category")


async def safe_convert(
    container: Any,
    amount: Decimal,
    from_currency: str,
    to_currency: str,
) -> Optional[Decimal]:
    """Convert via use case when available; return None on failure."""
    uc = getattr(container, "convert_currency", None)
    if uc is None:
        return None
    if from_currency.upper() == to_currency.upper():
        return Decimal(str(amount)).quantize(Decimal("0.01"))
    try:
        return await uc.execute(
            Decimal(str(amount)),
            from_currency=from_currency,
            to_currency=to_currency,
        )
    except Exception:  # noqa: BLE001
        return None
