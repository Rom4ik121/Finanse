"""Home dashboard — static adaptive layout, clear analytics."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING

import flet as ft

from lib.domain.entities.currency_codes import normalize_currency_code
from lib.domain.entities.transaction import TransactionType
from lib.domain.use_cases.transactions import StatsPeriod
from lib.presentation.styles import (
    card_surface,
    notice_banner,
    page_header,
    section_title,
    shortcut_chip,
)
from lib.presentation.theme import is_dark_mode
from lib.presentation.utils import (
    format_money,
    run_async,
    safe_convert,
    safe_update,
    snack,
    tr,
)
from lib.presentation.widgets.charts import build_line_chart_image, build_pie_chart_image
from lib.presentation.widgets.dual_add_button import dual_add_button
from lib.presentation.widgets.empty_state import EmptyState
from lib.presentation.widgets.loading import loading_indicator
from lib.presentation.widgets.quick_add_sheet import open_quick_add
from lib.presentation.widgets.summary_card import SummaryCard

if TYPE_CHECKING:
    from lib.presentation.state.app_state import AppState


def _content_width(page: ft.Page) -> int:
    """Usable chart width based on current window size."""
    raw = getattr(page, "width", None) or getattr(getattr(page, "window", None), "width", None)
    try:
        width = int(raw) if raw else 390
    except (TypeError, ValueError):
        width = 390
    # padding 12*2 + card padding
    return max(280, min(width - 40, 520))


class DashboardPage(ft.Column):
    """Total balance, month KPIs, shortcuts, analytics."""

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

    async def _totals_in_base(
        self,
        accounts: list,
        month_txs: list,
        base: str,
    ) -> tuple[Decimal, Decimal, Decimal, bool]:
        """Convert balances and month totals into ``base`` currency.

        Returns ``(total_balance, month_income, month_expense, all_converted)``.
        When a rate is missing, falls back to the raw amount only if currencies
        already match; otherwise counts as a failed conversion.
        """
        c = self._state.container
        base = normalize_currency_code(base)
        total = Decimal("0.00")
        income = Decimal("0.00")
        expense = Decimal("0.00")
        ok = True

        for account in accounts:
            src = normalize_currency_code(account.currency)
            converted = await safe_convert(c, account.balance, src, base)
            if converted is not None:
                total += converted
            elif src == base:
                total += account.balance
            else:
                ok = False

        for tx in month_txs:
            src = normalize_currency_code(tx.currency)
            converted = await safe_convert(c, tx.amount, src, base)
            if converted is None:
                if src == base:
                    converted = tx.amount
                else:
                    ok = False
                    continue
            if tx.type == TransactionType.INCOME:
                income += converted
            else:
                expense += converted

        return total, income, expense, ok

    async def reload(self) -> None:
        """Reload dashboard data from use cases."""
        self._token = self._state.dashboard_token
        lang = self._state.language
        self._body.controls = [loading_indicator(message=tr("action.refresh", lang))]
        safe_update(self._body)

        c = self._state.container
        now = datetime.now(timezone.utc)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        dark = is_dark_mode(self._page, self._state.theme_mode)
        chart_w = _content_width(self._page)

        try:
            accounts = await c.list_accounts.execute(active_only=True)
            stats = await c.get_transaction_stats.execute(
                date_from=month_start,
                date_to=now,
                group_by=StatsPeriod.DAY,
            )
            month_txs = await c.list_transactions.execute(
                date_from=month_start,
                date_to=now,
            )
            goals = await c.list_goals.execute(include_completed=False)
            debts = await c.list_debts.execute()
        except Exception as exc:  # noqa: BLE001
            snack(self._page, str(exc), error=True)
            self._body.controls = [
                EmptyState(tr("error.generic", lang), icon=ft.Icons.ERROR_OUTLINE)
            ]
            safe_update(self._body)
            return

        base = normalize_currency_code(self._state.base_currency)
        total, month_income, month_expense, fx_ok = await self._totals_in_base(
            accounts, month_txs, base
        )
        if not fx_ok and c.update_exchange_rates is not None:
            try:
                await c.update_exchange_rates.execute(base=base)
                total, month_income, month_expense, fx_ok = await self._totals_in_base(
                    accounts, month_txs, base
                )
            except Exception:  # noqa: BLE001
                pass
        if not fx_ok:
            snack(self._page, tr("fx.missing_rates", lang), error=True)

        # Prefer FX-aware month totals; fall back to raw stats if empty.
        if month_txs:
            stats_income = month_income
            stats_expense = month_expense
        else:
            stats_income = stats.total_income
            stats_expense = stats.total_expense

        pie = build_pie_chart_image(
            [s.category for s in stats.by_category[:6]],
            [s.amount for s in stats.by_category[:6]],
            title="",
            width=chart_w,
            height=300,
            dark=dark,
            language=lang,
        )
        line = build_line_chart_image(
            [p.period[-5:] for p in stats.by_period[-14:]],
            [p.income for p in stats.by_period[-14:]],
            [p.expense for p in stats.by_period[-14:]],
            title="",
            width=chart_w,
            height=240,
            dark=dark,
            language=lang,
        )

        # Category breakdown list under the donut (easier than tiny legend alone).
        category_rows: list[ft.Control] = []
        palette = [
            "#2DD4BF",
            "#38BDF8",
            "#4ADE80",
            "#FBBF24",
            "#F87171",
            "#A78BFA",
        ]
        expense_total = stats.total_expense or Decimal("0")
        for idx, slice_ in enumerate(stats.by_category[:6]):
            share = (
                (slice_.amount / expense_total * 100) if expense_total > 0 else Decimal("0")
            )
            category_rows.append(
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Row(
                            spacing=8,
                            expand=True,
                            controls=[
                                ft.Container(
                                    width=10,
                                    height=10,
                                    border_radius=5,
                                    bgcolor=palette[idx % len(palette)],
                                ),
                                ft.Text(
                                    slice_.category,
                                    size=12,
                                    expand=True,
                                    overflow=ft.TextOverflow.ELLIPSIS,
                                    max_lines=1,
                                ),
                            ],
                        ),
                        ft.Text(
                            f"{format_money(slice_.amount, base)}  ({share:.0f}%)",
                            size=11,
                            color=ft.Colors.ON_SURFACE_VARIANT,
                            weight=ft.FontWeight.W_600,
                        ),
                    ],
                )
            )

        notice_controls: list[ft.Control] = []
        notifier = getattr(c, "notification_service", None)
        if notifier is not None and self._state.settings.notifications_enabled:
            for note in notifier.list_pending()[:3]:
                notice_controls.append(notice_banner(note.title, note.body))

        self._body.controls = [
            *notice_controls,
            SummaryCard(
                title=tr("dashboard.total_balance", lang),
                value=format_money(total, base),
                icon=ft.Icons.ACCOUNT_BALANCE_WALLET,
                accent=ft.Colors.PRIMARY,
                hero=True,
                expand=True,
            ),
            # Equal-height KPI pair (fixed height inside SummaryCard).
            ft.Row(
                spacing=10,
                vertical_alignment=ft.CrossAxisAlignment.START,
                controls=[
                    SummaryCard(
                        title=tr("dashboard.month_income", lang),
                        value=format_money(stats_income, base),
                        icon=ft.Icons.TRENDING_UP,
                        accent=ft.Colors.SECONDARY,
                        expand=True,
                    ),
                    SummaryCard(
                        title=tr("dashboard.month_expense", lang),
                        value=format_money(stats_expense, base),
                        icon=ft.Icons.TRENDING_DOWN,
                        accent=ft.Colors.ERROR,
                        expand=True,
                    ),
                ],
            ),
            # One long dual button: expense  /  income
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
            section_title(tr("dashboard.shortcuts", lang)),
            # 2×2 static grid that fills width.
            ft.Column(
                spacing=8,
                controls=[
                    ft.Row(
                        spacing=8,
                        controls=[
                            shortcut_chip(
                                tr("nav.goals", lang),
                                ft.Icons.FLAG_OUTLINED,
                                on_click=lambda _e: self._state.open_secondary("goals"),
                            ),
                            shortcut_chip(
                                tr("nav.debts", lang),
                                ft.Icons.CREDIT_SCORE,
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
            ft.Text(
                f"{tr('nav.goals', lang)}: {len(goals)} · "
                f"{tr('nav.debts', lang)}: {len(debts)}",
                size=11,
                color=ft.Colors.ON_SURFACE_VARIANT,
            ),
            section_title(tr("dashboard.charts", lang)),
            # Analytics block 1 — categories
            card_surface(
                ft.Column(
                    spacing=10,
                    tight=True,
                    controls=[
                        ft.Text(
                            tr("dashboard.month_expense", lang),
                            size=14,
                            weight=ft.FontWeight.W_700,
                        ),
                        ft.Text(
                            tr("dashboard.expense_hint", lang),
                            size=11,
                            color=ft.Colors.ON_SURFACE_VARIANT,
                        ),
                        pie,
                        *category_rows,
                    ],
                ),
                padding=12,
            ),
            # Analytics block 2 — dynamics
            card_surface(
                ft.Column(
                    spacing=10,
                    tight=True,
                    controls=[
                        ft.Text(
                            tr("dashboard.dynamics", lang),
                            size=14,
                            weight=ft.FontWeight.W_700,
                        ),
                        ft.Text(
                            tr("dashboard.dynamics_hint", lang),
                            size=11,
                            color=ft.Colors.ON_SURFACE_VARIANT,
                        ),
                        ft.Row(
                            spacing=12,
                            controls=[
                                ft.Row(
                                    spacing=6,
                                    tight=True,
                                    controls=[
                                        ft.Container(
                                            width=10,
                                            height=10,
                                            border_radius=5,
                                            bgcolor=ft.Colors.SECONDARY,
                                        ),
                                        ft.Text(
                                            tr("transaction.income", lang),
                                            size=11,
                                        ),
                                    ],
                                ),
                                ft.Row(
                                    spacing=6,
                                    tight=True,
                                    controls=[
                                        ft.Container(
                                            width=10,
                                            height=10,
                                            border_radius=5,
                                            bgcolor=ft.Colors.ERROR,
                                        ),
                                        ft.Text(
                                            tr("transaction.expense", lang),
                                            size=11,
                                        ),
                                    ],
                                ),
                            ],
                        ),
                        line,
                    ],
                ),
                padding=12,
            ),
            ft.Container(height=10),
        ]
        safe_update(self._body)
