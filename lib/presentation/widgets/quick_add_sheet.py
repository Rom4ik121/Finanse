"""Quick income / expense fullscreen form."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING, Optional

import flet as ft

from lib.domain.entities.account import Account
from lib.domain.entities.category import CategoryKind
from lib.domain.entities.transaction import Transaction, TransactionType
from lib.presentation.utils import run_async, snack, tr
from lib.presentation.widgets.category_picker import CategoryPicker
from lib.presentation.widgets.fullscreen_form import open_fullscreen_form

if TYPE_CHECKING:
    from lib.presentation.state.app_state import AppState


def open_quick_add(
    page: ft.Page,
    state: "AppState",
    *,
    accounts: Sequence[Account] | None = None,
    default_type: TransactionType = TransactionType.EXPENSE,
    on_saved: Optional[Callable[[], None]] = None,
) -> None:
    """Open a fullscreen form for quickly adding income or expense."""

    async def _open() -> None:
        lang = state.language
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
        if not loaded:
            snack(page, tr("empty.accounts", lang), error=True)
            return
        await _show_form(
            page,
            state,
            accounts=loaded,
            default_type=default_type,
            on_saved=on_saved,
        )

    run_async(page, _open)


async def _show_form(
    page: ft.Page,
    state: "AppState",
    *,
    accounts: Sequence[Account],
    default_type: TransactionType,
    on_saved: Optional[Callable[[], None]],
) -> None:
    lang = state.language
    type_dd = ft.Dropdown(
        label=tr("field.type", lang),
        value=default_type.value,
        options=[
            ft.DropdownOption(
                key=TransactionType.EXPENSE.value,
                text=tr("transaction.expense", lang),
            ),
            ft.DropdownOption(
                key=TransactionType.INCOME.value,
                text=tr("transaction.income", lang),
            ),
        ],
        expand=True,
    )
    amount_tf = ft.TextField(
        label=tr("field.amount", lang),
        keyboard_type=ft.KeyboardType.NUMBER,
        expand=True,
        autofocus=True,
    )
    account_dd = ft.Dropdown(
        label=tr("field.account", lang),
        value=accounts[0].id,
        options=[
            ft.DropdownOption(key=a.id, text=f"{a.name} ({a.currency})")
            for a in accounts
        ],
        expand=True,
    )
    category_picker = CategoryPicker(
        page,
        state,
        tx_type=default_type.value,
    )
    await category_picker.reload()
    if category_picker.is_empty:
        category_picker.prompt_if_empty()

    def _on_type(_e: ft.ControlEvent) -> None:
        category_picker.set_tx_type(type_dd.value or TransactionType.EXPENSE.value)

    type_dd.on_select = _on_type

    comment_tf = ft.TextField(label=tr("field.comment", lang), expand=True)
    tags_tf = ft.TextField(
        label=tr("field.tags", lang),
        hint_text=tr("tags.hint", lang),
        expand=True,
    )

    async def _save() -> None:
        try:
            amount = Decimal(str(amount_tf.value or "").replace(",", ".").strip())
            if amount <= 0:
                raise InvalidOperation
        except (InvalidOperation, ValueError):
            snack(
                page,
                tr("invalid_amount", lang),
                error=True,
            )
            return

        account = next((a for a in accounts if a.id == account_dd.value), accounts[0])
        tags = [
            part.strip().lstrip("#")
            for part in (tags_tf.value or "").split(",")
            if part.strip()
        ]
        tx_type = TransactionType(type_dd.value or TransactionType.EXPENSE.value)
        category_name = category_picker.selected_name
        if not category_name:
            snack(page, tr("field.category", lang), error=True)
            return
        if (
            state.container.find_or_create_category is not None
            and not category_picker.has_category(category_name)
        ):
            await state.container.find_or_create_category.execute(
                category_name,
                kind=(
                    CategoryKind.INCOME
                    if tx_type == TransactionType.INCOME
                    else CategoryKind.EXPENSE
                ),
            )
        tx = Transaction(
            account_id=account.id,
            amount=amount,
            category=category_name,
            tags=tags,
            date=datetime.now(timezone.utc),
            comment=comment_tf.value or "",
            type=tx_type,
            currency=account.currency,
        )
        try:
            await state.container.add_transaction.execute(tx)
        except Exception as exc:  # noqa: BLE001
            snack(page, str(exc), error=True)
            return

        close()
        state.bump_refresh("dashboard", "transactions", "accounts", "budgets")
        snack(page, tr("action.saved", lang))
        if on_saved:
            on_saved()

    close = open_fullscreen_form(
        page,
        title=tr("action.quick_add", lang),
        lang=lang,
        overlay_key="quick_add_editor",
        body=[
            type_dd,
            amount_tf,
            account_dd,
            category_picker,
            comment_tf,
            tags_tf,
        ],
        on_save=_save,
    )
