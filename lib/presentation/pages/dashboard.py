"""Home dashboard — balance, quick add, analytics entry, shortcuts."""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

import flet as ft

from lib.domain.entities.currency_codes import normalize_currency_code
from lib.domain.entities.transaction import TransactionType
from lib.presentation.notification_badges import (
    DEBT_ALERT_KINDS,
    GOAL_ALERT_KINDS,
    SUBSCRIPTION_ALERT_KINDS,
    pending_count,
)
from lib.presentation.styles import (
    page_header,
    section_title,
    shortcut_chip,
)
from lib.presentation.utils import (
    format_money,
    load_rate_book,
    run_async,
    safe_update,
    snack,
    tr,
)
from lib.presentation.widgets.dual_add_button import dual_add_button
from lib.presentation.widgets.empty_state import EmptyState
from lib.presentation.widgets.loading import loading_indicator
from lib.presentation.widgets.quick_add_sheet import open_quick_add
from lib.presentation.widgets.summary_card import SummaryCard

if TYPE_CHECKING:
    from lib.presentation.state.app_state import AppState


class DashboardPage(ft.Column):
    """Total balance, quick actions, and section shortcuts."""

    def __init__(self, page: ft.Page, state: "AppState") -> None:
        self._page = page
        self._state = state
        self._body = ft.Column(expand=True, scroll=ft.ScrollMode.AUTO, spacing=12)
        self._token = -1
        super().__init__(
            expand=True,
            spacing=0,
            controls=[
                page_header(
                    tr("nav.home", state.language),
                    actions=[
                        ft.IconButton(
                            icon=ft.Icons.REFRESH,
                            icon_color=ft.Colors.PRIMARY,
                            tooltip=tr("action.refresh", state.language),
                            on_click=lambda _e: run_async(page, self.reload),
                        ),
                    ],
                ),
                ft.Container(
                    expand=True,
                    padding=ft.Padding.symmetric(horizontal=12),
                    content=self._body,
                ),
            ],
        )
        state.subscribe(self._on_state)
        run_async(page, self.reload)

    def _on_state(self, state: "AppState") -> None:
        if state.dashboard_token != self._token:
            run_async(self._page, self.reload)
    async def _total_in_base(self, accounts: list, base: str) -> tuple[Decimal, bool]:
        """Convert account balances into ``base`` currency."""
        base = normalize_currency_code(base)
        book = await load_rate_book(self._state.container)
        total = Decimal("0.00")
        ok = True
        for account in accounts:
            src = normalize_currency_code(account.currency)
            converted = book.convert(account.balance, src, base)
            if converted is not None:
                total += converted
            elif src == base:
                total += account.balance
            else:
                ok = False
        return total, ok

    def _analytics_button(self, lang: str) -> ft.Container:
        """Full-width entry to the analytics secondary screen."""
        return ft.Container(
            height=52,
            border_radius=16,
            clip_behavior=ft.ClipBehavior.HARD_EDGE,
            border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGH,
            shadow=ft.BoxShadow(
                blur_radius=14,
                color="#00000033",
                offset=ft.Offset(0, 4),
            ),
            ink=True,
            on_click=lambda _e: self._state.open_secondary("analytics"),
            padding=ft.Padding.symmetric(horizontal=16, vertical=12),
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Row(
                        spacing=10,
                        tight=True,
                        controls=[
                            ft.Container(
                                width=32,
                                height=32,
                                border_radius=10,
                                bgcolor=ft.Colors.PRIMARY_CONTAINER,
                                alignment=ft.Alignment.CENTER,
                                content=ft.Icon(
                                    ft.Icons.INSIGHTS,
                                    size=18,
                                    color=ft.Colors.ON_PRIMARY_CONTAINER,
                                ),
                            ),
                            ft.Text(
                                tr("nav.analytics", lang),
                                size=14,
                                weight=ft.FontWeight.W_700,
                                color=ft.Colors.ON_SURFACE,
                            ),
                        ],
                    ),
                    ft.Icon(
                        ft.Icons.CHEVRON_RIGHT,
                        size=22,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                    ),
                ],
            ),
        )
    async def reload(self) -> None:
        """Reload dashboard data from use cases."""
        self._token = self._state.dashboard_token
        lang = self._state.language
        self._body.controls = [loading_indicator(message=tr("action.refresh", lang))]
        safe_update(self._body)
        c = self._state.container
        try:
            accounts = await c.list_accounts.execute(active_only=True)
        except Exception as exc:  # noqa: BLE001
            snack(self._page, str(exc), error=True)
            self._body.controls = [
                EmptyState(tr("error.generic", lang), icon=ft.Icons.ERROR_OUTLINE)
            ]
            safe_update(self._body)
            return
        base = normalize_currency_code(self._state.base_currency)
        total, fx_ok = await self._total_in_base(accounts, base)
        if not fx_ok and c.update_exchange_rates is not None:
            try:
                await c.update_exchange_rates.execute(base=base)
                from lib.presentation.utils import invalidate_rate_book_cache

                invalidate_rate_book_cache()
                total, fx_ok = await self._total_in_base(accounts, base)
            except Exception:  # noqa: BLE001
                pass
        if not fx_ok:
            snack(self._page, tr("fx.missing_rates", lang), error=True)
        settings = self._state.settings
        goals_badge = pending_count(c, settings, GOAL_ALERT_KINDS)
        debts_badge = pending_count(c, settings, DEBT_ALERT_KINDS)
        subs_badge = pending_count(c, settings, SUBSCRIPTION_ALERT_KINDS)
        self._body.controls = [
            SummaryCard(
                title=tr("dashboard.total_balance", lang),
                value=format_money(total, base),
                icon=ft.Icons.ACCOUNT_BALANCE_WALLET,
                accent=ft.Colors.PRIMARY,
                hero=True,
                expand=True,
            ),
            dual_add_button(
                lang,
                on_expense=lambda: open_quick_add(
                    self._page,
                    self._state,
                    accounts=accounts,
                    default_type=TransactionType.EXPENSE,
                ),
                on_income=lambda: open_quick_add(
                    self._page,
                    self._state,
                    accounts=accounts,
                    default_type=TransactionType.INCOME,
                ),
            ),
            self._analytics_button(lang),
            section_title(tr("dashboard.shortcuts", lang)),
            ft.Column(
                spacing=8,
                controls=[
                    ft.Row(
                        spacing=8,
                        controls=[
                            shortcut_chip(
                                tr("nav.goals", lang),
                                ft.Icons.FLAG_OUTLINED,
                                badge=goals_badge,
                                on_click=lambda _e: self._state.open_secondary("goals"),
                            ),
                            shortcut_chip(
                                tr("nav.debts", lang),
                                ft.Icons.CREDIT_SCORE,
                                badge=debts_badge,
                                on_click=lambda _e: self._state.open_secondary("debts"),
                            ),
                        ],
                    ),
                    ft.Row(
                        spacing=8,
                        controls=[
                            shortcut_chip(
                                tr("nav.subscriptions", lang),
                                ft.Icons.EVENT_REPEAT,
                                badge=subs_badge,
                                on_click=lambda _e: self._state.open_secondary(
                                    "subscriptions"
                                ),
                            ),
                            shortcut_chip(
                                tr("nav.currencies", lang),
                                ft.Icons.CURRENCY_EXCHANGE,
                                on_click=lambda _e: self._state.open_secondary(
                                    "currencies"
                                ),
                            ),
                        ],
                    ),
                ],
            ),
            ft.Container(height=10),
        ]
        safe_update(self._body)
