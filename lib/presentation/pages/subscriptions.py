"""Subscriptions page with upcoming charges calendar."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import TYPE_CHECKING, Optional

import flet as ft

from lib.domain.entities.subscription import Periodicity, Subscription
from lib.presentation.styles import page_header, summary_strip
from lib.presentation.utils import (
    format_date,
    format_money,
    run_async,
    safe_convert,
    snack,
    tr,
)
from lib.presentation.widgets.confirm_dialog import confirm_dialog
from lib.presentation.widgets.date_time_field import DateTimeField
from lib.presentation.widgets.empty_state import EmptyState
from lib.presentation.widgets.loading import loading_indicator
from lib.presentation.widgets.subscription_card import SubscriptionCard

if TYPE_CHECKING:
    from lib.presentation.state.app_state import AppState


class SubscriptionsPage(ft.Column):
    """List subscriptions and upcoming billing dates."""

    def __init__(self, page: ft.Page, state: "AppState") -> None:
        self._page = page
        self._state = state
        self._accounts: list = []
        self._calendar = ft.Column(spacing=6)
        self._list = ft.Column(expand=True, scroll=ft.ScrollMode.AUTO, spacing=12)
        super().__init__(
            expand=True,
            spacing=0,
            controls=[
                page_header(
                    tr("nav.subscriptions", state.language),
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
                    padding=ft.Padding.symmetric(horizontal=16),
                    content=ft.Column(
                        spacing=8,
                        controls=[
                            ft.Text(
                                tr("subscriptions.calendar", state.language),
                                weight=ft.FontWeight.W_600,
                            ),
                            self._calendar,
                        ],
                    ),
                ),
                ft.Container(
                    expand=True,
                    padding=ft.Padding.symmetric(horizontal=16),
                    content=self._list,
                ),
            ],
        )
        run_async(page, self.reload)

    async def reload(self) -> None:
        """Reload subscriptions and build upcoming calendar."""
        lang = self._state.language
        self._list.controls = [loading_indicator()]
        self._list.update()
        try:
            self._accounts = await self._state.container.list_accounts.execute(
                active_only=True
            )
            items = await self._state.container.list_subscriptions.execute()
        except Exception as exc:  # noqa: BLE001
            snack(self._page, str(exc), error=True)
            self._list.controls = [EmptyState(tr("error.generic", lang))]
            self._list.update()
            return

        upcoming = sorted(
            [s for s in items if s.is_active],
            key=lambda s: s.next_billing_date,
        )[:8]
        if upcoming:
            self._calendar.controls = [
                ft.ListTile(
                    leading=ft.Icon(ft.Icons.EVENT, color=ft.Colors.TEAL_700),
                    title=ft.Text(s.name),
                    subtitle=ft.Text(format_date(s.next_billing_date)),
                    trailing=ft.Text(
                        format_money(s.amount, s.currency),
                        weight=ft.FontWeight.W_600,
                    ),
                )
                for s in upcoming
            ]
        else:
            self._calendar.controls = [
                ft.Text(
                    "—",
                    color=ft.Colors.ON_SURFACE_VARIANT,
                )
            ]
        self._calendar.update()

        if not items:
            self._list.controls = [
                EmptyState(
                    tr("empty.subscriptions", lang),
                    action_label=tr("action.add", lang),
                    on_action=lambda _e: self._open_editor(),
                )
            ]
            self._list.update()
            return

        base = self._state.base_currency
        monthly = Decimal("0")
        yearly = Decimal("0")
        for sub in items:
            if not sub.is_active:
                continue
            converted = await safe_convert(
                self._state.container, sub.amount, sub.currency, base
            )
            amount = (
                converted
                if converted is not None
                else (
                    sub.amount
                    if sub.currency.upper() == base.upper()
                    else Decimal("0")
                )
            )
            if sub.periodicity == Periodicity.YEARLY:
                yearly += amount
                monthly += amount / Decimal("12")
            else:
                monthly += amount
                yearly += amount * Decimal("12")

        self._list.controls = [
            summary_strip(
                [
                    (
                        tr("subscriptions.monthly_total", lang),
                        format_money(monthly, base),
                        ft.Colors.PRIMARY,
                    ),
                    (
                        tr("subscriptions.yearly_total", lang),
                        format_money(yearly, base),
                        ft.Colors.SECONDARY,
                    ),
                ]
            ),
            *[
                SubscriptionCard(
                    s,
                    language=lang,
                    on_edit=self._open_editor,
                    on_delete=self._confirm_delete,
                )
                for s in items
            ],
        ]
        self._list.update()

    def _confirm_delete(self, sub: Subscription) -> None:
        lang = self._state.language

        async def _do() -> None:
            await self._state.container.delete_subscription.execute(sub.id)
            self._state.bump_refresh("dashboard")
            await self.reload()

        confirm_dialog(
            self._page,
            title=tr("action.confirm_delete", lang),
            message=sub.name,
            confirm_text=tr("action.delete", lang),
            cancel_text=tr("action.cancel", lang),
            on_confirm=_do,
        )

    def _open_editor(self, sub: Optional[Subscription] = None) -> None:
        run_async(self._page, self._open_editor_async, sub)

    async def _open_editor_async(self, sub: Optional[Subscription] = None) -> None:
        lang = self._state.language
        if not self._accounts:
            try:
                self._accounts = await self._state.container.list_accounts.execute(
                    active_only=True
                )
            except Exception as exc:  # noqa: BLE001
                snack(self._page, str(exc), error=True)
                return
        if not self._accounts:
            snack(self._page, tr("empty.accounts", lang), error=True)
            return

        cat_names: list[str] = [tr("category.other", lang)]
        if self._state.container.list_categories is not None:
            cats = await self._state.container.list_categories.execute()
            if cats:
                cat_names = [c.name for c in cats]

        name_tf = ft.TextField(
            label=tr("field.name", lang), value=sub.name if sub else ""
        )
        amount_tf = ft.TextField(
            label=tr("field.amount", lang),
            value=str(sub.amount) if sub else "",
            keyboard_type=ft.KeyboardType.NUMBER,
        )
        account_dd = ft.Dropdown(
            label=tr("field.account", lang),
            value=sub.account_id if sub else self._accounts[0].id,
            options=[
                ft.DropdownOption(key=a.id, text=a.name) for a in self._accounts
            ],
        )
        category_dd = ft.Dropdown(
            label=tr("field.category", lang),
            value=sub.category if sub else cat_names[0],
            options=[ft.DropdownOption(key=c, text=c) for c in cat_names],
        )
        period_dd = ft.Dropdown(
            label=tr("field.period", lang),
            value=(
                sub.periodicity.value if sub else Periodicity.MONTHLY.value
            ),
            options=[
                ft.DropdownOption(
                    key=Periodicity.MONTHLY.value,
                    text=tr("subscription.monthly", lang),
                ),
                ft.DropdownOption(
                    key=Periodicity.YEARLY.value,
                    text=tr("subscription.yearly", lang),
                ),
            ],
        )
        next_field = DateTimeField(
            self._page,
            lang=lang,
            label=tr("field.date", lang),
            value=(
                sub.next_billing_date
                if sub
                else datetime.now(timezone.utc)
            ),
        )
        active_sw = ft.Switch(
            label=tr("field.active", lang),
            value=sub.is_active if sub else True,
        )

        async def _save(_e: ft.ControlEvent) -> None:
            try:
                amount = Decimal(str(amount_tf.value or "").replace(",", "."))
                if amount <= 0:
                    raise InvalidOperation
            except (InvalidOperation, ValueError):
                snack(self._page, tr("invalid_amount", lang), error=True)
                return
            next_date = next_field.value
            if next_date is None:
                snack(self._page, tr("invalid_date", lang), error=True)
                return
            account = next(
                (a for a in self._accounts if a.id == account_dd.value),
                self._accounts[0],
            )
            entity = Subscription(
                id=sub.id if sub else Subscription(
                    name="tmp",
                    amount=1,
                    account_id=account.id,
                    next_billing_date=next_date,
                ).id,
                name=(name_tf.value or "").strip() or "Subscription",
                amount=amount,
                currency=account.currency,
                account_id=account.id,
                category=category_dd.value or cat_names[0],
                periodicity=Periodicity(period_dd.value),
                next_billing_date=next_date,
                is_active=bool(active_sw.value),
                last_charged_at=sub.last_charged_at if sub else None,
                comment=sub.comment if sub else "",
                created_at=sub.created_at if sub else datetime.now(timezone.utc),
            )
            if sub:
                await self._state.container.update_subscription.execute(entity)
            else:
                await self._state.container.create_subscription.execute(entity)
            self._page.pop_dialog()
            self._state.bump_refresh("dashboard")
            await self.reload()
            snack(self._page, tr("action.saved", lang))

        self._page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title=ft.Text(
                    tr("action.edit", lang) if sub else tr("action.add", lang)
                ),
                content=ft.Container(
                    width=420,
                    content=ft.Column(
                        tight=True,
                        spacing=10,
                        scroll=ft.ScrollMode.AUTO,
                        controls=[
                            name_tf,
                            amount_tf,
                            account_dd,
                            category_dd,
                            period_dd,
                            next_field,
                            active_sw,
                        ],
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
