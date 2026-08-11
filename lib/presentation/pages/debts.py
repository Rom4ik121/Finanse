"""Debts CRUD page with interest and reminders banner."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from typing import TYPE_CHECKING, Optional

import flet as ft

from lib.domain.entities.debt import Debt, DebtDirection, DebtStatus
from lib.presentation.styles import page_header, summary_strip
from lib.presentation.utils import format_money, run_async, safe_convert, snack, tr
from lib.presentation.widgets.confirm_dialog import confirm_dialog
from lib.presentation.widgets.date_time_field import DateTimeField
from lib.presentation.widgets.debt_card import DebtCard
from lib.presentation.widgets.empty_state import EmptyState
from lib.presentation.widgets.loading import loading_indicator

if TYPE_CHECKING:
    from lib.presentation.state.app_state import AppState


class DebtsPage(ft.Column):
    """Manage personal debts and loans."""

    def __init__(self, page: ft.Page, state: "AppState") -> None:
        self._page = page
        self._state = state
        self._banner = ft.Container(visible=False)
        self._list = ft.Column(expand=True, scroll=ft.ScrollMode.AUTO, spacing=12)
        super().__init__(
            expand=True,
            spacing=0,
            controls=[
                page_header(
                    tr("nav.debts", state.language),
                    leading=ft.IconButton(
                        icon=ft.Icons.ARROW_BACK,
                        on_click=lambda _e: state.close_secondary(),
                    ),
                    actions=[
                        ft.IconButton(
                            icon=ft.Icons.ADD,
                            on_click=lambda _e: self._open_editor(),
                        ),
                    ],
                ),
                ft.Container(
                    padding=ft.padding.symmetric(horizontal=16),
                    content=self._banner,
                ),
                ft.Container(
                    expand=True,
                    padding=ft.padding.symmetric(horizontal=16),
                    content=self._list,
                ),
            ],
        )
        run_async(page, self.reload)

    async def reload(self) -> None:
        """Reload debts and interest estimates."""
        lang = self._state.language
        self._list.controls = [loading_indicator()]
        self._list.update()
        try:
            debts = await self._state.container.list_debts.execute()
        except Exception as exc:  # noqa: BLE001
            snack(self._page, str(exc), error=True)
            self._list.controls = [EmptyState(tr("error.generic", lang))]
            self._list.update()
            return

        soon = datetime.now(timezone.utc) + timedelta(days=7)
        due_soon = [
            d
            for d in debts
            if d.status == DebtStatus.ACTIVE
            and d.due_date
            and d.due_date <= soon
        ]
        if due_soon and self._state.settings.debt_reminders:
            names = ", ".join(d.counterparty for d in due_soon[:3])
            self._banner.visible = True
            self._banner.content = ft.Container(
                padding=12,
                border_radius=12,
                bgcolor=ft.Colors.AMBER_100,
                content=ft.Row(
                    spacing=10,
                    controls=[
                        ft.Icon(ft.Icons.NOTIFICATIONS_ACTIVE, color=ft.Colors.AMBER_900),
                        ft.Text(
                            f"{tr('debts.reminders', lang)}: {names}",
                            color=ft.Colors.AMBER_900,
                            expand=True,
                        ),
                    ],
                ),
            )
        else:
            self._banner.visible = False
            self._banner.content = None
        self._banner.update()

        if not debts:
            self._list.controls = [
                EmptyState(
                    tr("empty.debts", lang),
                    action_label=tr("action.add", lang),
                    on_action=lambda _e: self._open_editor(),
                )
            ]
            self._list.update()
            return

        base = self._state.base_currency
        i_owe = Decimal("0")
        owed_to_me = Decimal("0")
        for debt in debts:
            if debt.status != DebtStatus.ACTIVE:
                continue
            converted = await safe_convert(
                self._state.container,
                debt.remaining_amount,
                debt.currency,
                base,
            )
            amount = (
                converted
                if converted is not None
                else (
                    debt.remaining_amount
                    if debt.currency.upper() == base.upper()
                    else Decimal("0")
                )
            )
            if debt.direction == DebtDirection.I_OWE:
                i_owe += amount
            else:
                owed_to_me += amount

        cards: list[ft.Control] = [
            summary_strip(
                [
                    (
                        tr("debts.total_i_owe", lang),
                        format_money(i_owe, base),
                        ft.Colors.ERROR,
                    ),
                    (
                        tr("debts.total_owed_to_me", lang),
                        format_money(owed_to_me, base),
                        ft.Colors.SECONDARY,
                    ),
                ]
            )
        ]
        for debt in debts:
            interest = None
            if debt.interest_rate is not None:
                try:
                    result = await self._state.container.calculate_debt_interest.execute(
                        debt.id
                    )
                    interest = result.interest_amount
                except Exception:  # noqa: BLE001
                    interest = None
            cards.append(
                DebtCard(
                    debt,
                    language=lang,
                    interest_amount=interest,
                    on_edit=self._open_editor,
                    on_delete=self._confirm_delete,
                    on_repay=self._repay,
                )
            )
        self._list.controls = cards
        self._list.update()

    def _confirm_delete(self, debt: Debt) -> None:
        lang = self._state.language

        async def _do() -> None:
            await self._state.container.delete_debt.execute(debt.id)
            self._state.bump_refresh("dashboard")
            await self.reload()

        confirm_dialog(
            self._page,
            title=tr("action.confirm_delete", lang),
            message=debt.counterparty,
            confirm_text=tr("action.delete", lang),
            cancel_text=tr("action.cancel", lang),
            on_confirm=_do,
        )

    def _repay(self, debt: Debt) -> None:
        lang = self._state.language
        i_owe = debt.direction == DebtDirection.I_OWE

        async def _open() -> None:
            try:
                accounts = await self._state.container.list_accounts.execute(
                    active_only=True
                )
            except Exception as exc:  # noqa: BLE001
                snack(self._page, str(exc), error=True)
                return
            if not accounts:
                snack(self._page, tr("error.no_accounts", lang), error=True)
                return

            amount_tf = ft.TextField(
                label=tr("field.amount", lang),
                value=str(debt.remaining_amount),
                keyboard_type=ft.KeyboardType.NUMBER,
                autofocus=True,
            )
            account_dd = ft.Dropdown(
                label=tr("field.account", lang),
                value=accounts[0].id,
                options=[
                    ft.DropdownOption(
                        key=a.id,
                        text=f"{a.name} · {format_money(a.balance, a.currency)}",
                    )
                    for a in accounts
                ],
            )

            async def _save(_e: ft.ControlEvent) -> None:
                try:
                    amount = Decimal(str(amount_tf.value or "").replace(",", "."))
                    if amount <= 0:
                        raise InvalidOperation
                except (InvalidOperation, ValueError):
                    snack(self._page, tr("invalid_amount", lang), error=True)
                    return
                account_id = account_dd.value or accounts[0].id
                account = next((a for a in accounts if a.id == account_id), accounts[0])
                if i_owe and amount > account.balance:
                    snack(self._page, tr("error.insufficient_funds", lang), error=True)
                    return
                try:
                    await self._state.container.repay_debt.execute(
                        debt.id,
                        amount,
                        account_id=account_id,
                    )
                except Exception as exc:  # noqa: BLE001
                    snack(self._page, str(exc), error=True)
                    return
                self._page.pop_dialog()
                self._state.bump_refresh("dashboard")
                self._state.bump_refresh("accounts")
                self._state.bump_refresh("transactions")
                await self.reload()
                snack(self._page, tr("action.saved", lang))

            self._page.show_dialog(
                ft.AlertDialog(
                    modal=True,
                    title=ft.Text(
                        f"{tr('debt.repay' if i_owe else 'debt.receive', lang)}"
                        f" · {debt.counterparty}"
                    ),
                    content=ft.Column(
                        tight=True,
                        spacing=10,
                        controls=[account_dd, amount_tf],
                    ),
                    actions=[
                        ft.TextButton(
                            tr("action.cancel", lang),
                            on_click=lambda _e: self._page.pop_dialog(),
                        ),
                        ft.FilledButton(
                            tr("debt.repay" if i_owe else "debt.receive", lang),
                            on_click=lambda e: run_async(self._page, _save, e),
                        ),
                    ],
                )
            )

        run_async(self._page, _open)

    def _open_editor(self, debt: Optional[Debt] = None) -> None:
        lang = self._state.language

        async def _open() -> None:
            accounts: list = []
            try:
                accounts = await self._state.container.list_accounts.execute(
                    active_only=True
                )
            except Exception:  # noqa: BLE001
                accounts = []

            name_tf = ft.TextField(
                label=tr("field.name", lang),
                value=debt.counterparty if debt else "",
            )
            amount_tf = ft.TextField(
                label=tr("field.amount", lang),
                value=str(debt.amount) if debt else "",
                keyboard_type=ft.KeyboardType.NUMBER,
            )
            currency_tf = ft.TextField(
                label=tr("field.currency", lang),
                value=debt.currency if debt else self._state.base_currency,
            )
            direction_dd = ft.Dropdown(
                label=tr("field.direction", lang),
                value=(
                    debt.direction.value
                    if debt
                    else DebtDirection.I_OWE.value
                ),
                options=[
                    ft.DropdownOption(
                        key=DebtDirection.I_OWE.value,
                        text=tr("debt.i_owe", lang),
                    ),
                    ft.DropdownOption(
                        key=DebtDirection.OWED_TO_ME.value,
                        text=tr("debt.owed_to_me", lang),
                    ),
                ],
            )
            rate_tf = ft.TextField(
                label=tr("field.interest", lang),
                value=str(debt.interest_rate)
                if debt and debt.interest_rate is not None
                else "",
                keyboard_type=ft.KeyboardType.NUMBER,
            )
            due_field = DateTimeField(
                self._page,
                lang=lang,
                label=tr("field.date", lang),
                value=debt.due_date if debt and debt.due_date else None,
                allow_clear=True,
            )
            comment_tf = ft.TextField(
                label=tr("field.comment", lang),
                value=debt.comment if debt else "",
            )

            controls: list[ft.Control] = [
                name_tf,
                amount_tf,
                currency_tf,
                direction_dd,
            ]
            account_dd: Optional[ft.Dropdown] = None
            record_cash = ft.Checkbox(
                label=tr("debt.record_cash", lang),
                value=True,
            )
            if debt is None and accounts:
                account_dd = ft.Dropdown(
                    label=tr("field.account", lang),
                    value=accounts[0].id,
                    options=[
                        ft.DropdownOption(
                            key=a.id,
                            text=f"{a.name} · {format_money(a.balance, a.currency)}",
                        )
                        for a in accounts
                    ],
                )
                controls.extend([record_cash, account_dd])
            elif debt is not None:
                controls.append(
                    ft.Text(
                        f"{tr('field.remaining', lang)}: "
                        f"{format_money(debt.remaining_amount, debt.currency)}",
                        size=13,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                    )
                )
            controls.extend([rate_tf, due_field, comment_tf])

            async def _save(_e: ft.ControlEvent) -> None:
                try:
                    amount = Decimal(str(amount_tf.value or "").replace(",", "."))
                    if amount <= 0:
                        raise InvalidOperation
                except (InvalidOperation, ValueError):
                    snack(self._page, tr("invalid_amount", lang), error=True)
                    return
                rate = None
                if (rate_tf.value or "").strip():
                    rate = Decimal(str(rate_tf.value).replace(",", "."))
                due = due_field.value
                entity = Debt(
                    id=debt.id
                    if debt
                    else Debt(
                        counterparty="tmp",
                        amount=1,
                        remaining_amount=1,
                        direction=DebtDirection.I_OWE,
                    ).id,
                    counterparty=(name_tf.value or "").strip() or "—",
                    amount=amount,
                    remaining_amount=debt.remaining_amount if debt else amount,
                    currency=(currency_tf.value or "RUB").upper(),
                    direction=DebtDirection(direction_dd.value),
                    status=debt.status if debt else DebtStatus.ACTIVE,
                    interest_rate=rate,
                    due_date=due,
                    started_at=debt.started_at if debt else datetime.now(timezone.utc),
                    comment=comment_tf.value or "",
                    created_at=debt.created_at if debt else datetime.now(timezone.utc),
                )
                try:
                    if debt:
                        await self._state.container.update_debt.execute(entity)
                    else:
                        account_id = None
                        if (
                            record_cash.value
                            and account_dd is not None
                            and account_dd.value
                        ):
                            account_id = account_dd.value
                            account = next(
                                (a for a in accounts if a.id == account_id), None
                            )
                            if (
                                account is not None
                                and entity.direction == DebtDirection.OWED_TO_ME
                                and amount > account.balance
                            ):
                                snack(
                                    self._page,
                                    tr("error.insufficient_funds", lang),
                                    error=True,
                                )
                                return
                        await self._state.container.create_debt.execute(
                            entity,
                            account_id=account_id,
                        )
                except Exception as exc:  # noqa: BLE001
                    snack(self._page, str(exc), error=True)
                    return
                self._page.pop_dialog()
                self._state.bump_refresh("dashboard")
                self._state.bump_refresh("accounts")
                self._state.bump_refresh("transactions")
                await self.reload()
                snack(self._page, tr("action.saved", lang))

            self._page.show_dialog(
                ft.AlertDialog(
                    modal=True,
                    title=ft.Text(
                        tr("action.edit", lang) if debt else tr("action.add", lang)
                    ),
                    content=ft.Container(
                        width=420,
                        content=ft.Column(
                            tight=True,
                            spacing=10,
                            scroll=ft.ScrollMode.AUTO,
                            controls=controls,
                        ),
                    ),
                    actions=[
                        ft.TextButton(
                            tr("action.cancel", lang),
                            on_click=lambda _e: self._page.pop_dialog(),
                        ),
                        ft.FilledButton(
                            tr("action.save", lang),
                            on_click=lambda e: run_async(self._page, _save, e),
                        ),
                    ],
                )
            )

        run_async(self._page, _open)
