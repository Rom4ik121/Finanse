"""Fullscreen form for transferring money between accounts."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from decimal import InvalidOperation
from typing import TYPE_CHECKING, Optional

import flet as ft

from lib.domain.entities.account import Account
from lib.presentation.money_input import attach_grouped_digits, make_amount_field, parse_amount
from lib.presentation.utils import format_money, load_rate_book, run_async, snack, tr
from lib.presentation.widgets.fullscreen_form import open_fullscreen_form

if TYPE_CHECKING:
    from lib.presentation.state.app_state import AppState

_DOMAIN_ERROR_KEYS = {
    "Cannot transfer to the same account": "transfer.same_account",
    "Insufficient funds": "transfer.insufficient",
    "No exchange rate for this currency pair": "transfer.no_rate",
    "Transfer amount must be positive": "invalid_amount",
}


def open_transfer(
    page: ft.Page,
    state: "AppState",
    *,
    accounts: Sequence[Account] | None = None,
    on_saved: Optional[Callable[[], None]] = None,
) -> None:
    """Open a fullscreen form to move money from one account to another."""

    async def _open() -> None:
        lang = state.language
        if state.container.transfer_between_accounts is None:
            snack(page, tr("error.generic", lang), error=True)
            return
        loaded: list[Account]
        try:
            loaded = list(
                await state.container.list_accounts.execute(active_only=True)
            )
        except Exception as exc:  # noqa: BLE001
            snack(page, str(exc), error=True)
            return
        if not loaded and accounts:
            loaded = list(accounts)
        if len(loaded) < 2:
            snack(page, tr("transfer.need_two_accounts", lang), error=True)
            return
        await _show_form(page, state, accounts=loaded, on_saved=on_saved)

    run_async(page, _open)


async def _show_form(
    page: ft.Page,
    state: "AppState",
    *,
    accounts: Sequence[Account],
    on_saved: Optional[Callable[[], None]],
) -> None:
    lang = state.language
    book = await load_rate_book(state.container)
    options = [
        ft.DropdownOption(key=a.id, text=f"{a.name} ({a.currency})") for a in accounts
    ]
    from_dd = ft.Dropdown(
        label=tr("transfer.from", lang),
        value=accounts[0].id,
        options=options,
        expand=True,
    )
    to_dd = ft.Dropdown(
        label=tr("transfer.to", lang),
        value=accounts[1].id,
        options=options,
        expand=True,
    )
    amount_tf = make_amount_field(
        lang,
        label=tr("field.amount", lang),
        expand=True,
        autofocus=True,
    )
    convert_hint = ft.Text("", size=12, color=ft.Colors.ON_SURFACE_VARIANT)
    comment_tf = ft.TextField(label=tr("field.comment", lang), expand=True)

    def _account(account_id: str | None) -> Account:
        return next((a for a in accounts if a.id == account_id), accounts[0])

    def _refresh_hint(_e: ft.ControlEvent | None = None) -> None:
        source = _account(from_dd.value)
        dest = _account(to_dd.value)
        try:
            amount = parse_amount(amount_tf.value)
        except (InvalidOperation, ValueError):
            convert_hint.value = ""
            convert_hint.update()
            return
        if amount <= 0:
            convert_hint.value = ""
            convert_hint.update()
            return
        if source.id == dest.id:
            convert_hint.value = tr("transfer.same_account", lang)
            convert_hint.color = ft.Colors.ERROR
            convert_hint.update()
            return
        if source.currency.upper() == dest.currency.upper():
            convert_hint.value = tr(
                "transfer.will_credit",
                lang,
                amount=format_money(amount, dest.currency),
                account=dest.name,
            )
            convert_hint.color = ft.Colors.ON_SURFACE_VARIANT
            convert_hint.update()
            return
        converted = book.convert(amount, source.currency, dest.currency)
        if converted is None:
            convert_hint.value = tr(
                "transfer.no_rate",
                lang,
                default="Нет курса для этой пары валют",
            )
            convert_hint.color = ft.Colors.ERROR
        else:
            convert_hint.value = tr(
                "transfer.will_credit",
                lang,
                amount=format_money(converted, dest.currency),
                account=dest.name,
            )
            convert_hint.color = ft.Colors.ON_SURFACE_VARIANT
        convert_hint.update()

    attach_grouped_digits(amount_tf, lang, extra_on_change=_refresh_hint)
    from_dd.on_select = _refresh_hint
    to_dd.on_select = _refresh_hint

    async def _save() -> None:
        try:
            amount = parse_amount(amount_tf.value)
            if amount <= 0:
                raise InvalidOperation
        except (InvalidOperation, ValueError):
            snack(page, tr("invalid_amount", lang), error=True)
            return
        source = _account(from_dd.value)
        dest = _account(to_dd.value)
        if source.id == dest.id:
            snack(page, tr("transfer.same_account", lang), error=True)
            return
        try:
            await state.container.transfer_between_accounts.execute(
                from_account_id=source.id,
                to_account_id=dest.id,
                amount=amount,
                comment=comment_tf.value or "",
            )
        except Exception as exc:  # noqa: BLE001
            key = _DOMAIN_ERROR_KEYS.get(str(exc))
            snack(page, tr(key, lang) if key else str(exc), error=True)
            return
        close()
        state.bump_refresh("dashboard", "transactions", "accounts", "budgets")
        snack(page, tr("action.saved", lang))
        if on_saved:
            on_saved()

    close = open_fullscreen_form(
        page,
        title=tr("transfers.title", lang),
        lang=lang,
        overlay_key="transfer_editor",
        body=[from_dd, to_dd, amount_tf, convert_hint, comment_tf],
        on_save=_save,
    )
