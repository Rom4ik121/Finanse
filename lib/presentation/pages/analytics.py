"""Dedicated analytics screen — period KPIs and charts."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING

import flet as ft

from lib.domain.entities.currency_codes import normalize_currency_code
from lib.domain.entities.transaction import TransactionType
from lib.domain.services.rate_book import RateBook
from lib.domain.use_cases.transactions import GetTransactionStatsUseCase
from lib.infrastructure.services.localization import localize_category_name
from lib.presentation.analytics_period import (
    ANALYTICS_PERIOD_KEYS,
    DEFAULT_ANALYTICS_PERIOD,
    format_chart_period_label,
    resolve_analytics_period,
)
from lib.presentation.styles import card_surface, page_header, section_title
from lib.presentation.theme import is_dark_mode
from lib.presentation.utils import (
    format_money,
    load_rate_book,
    run_async,
    safe_update,
    snack,
    tr,
)
from lib.presentation.widgets.charts import build_line_chart_image, build_pie_chart_image
from lib.presentation.widgets.empty_state import EmptyState
from lib.presentation.widgets.loading import loading_indicator
from lib.presentation.widgets.summary_card import SummaryCard

if TYPE_CHECKING:
    from lib.presentation.state.app_state import AppState


def _content_width(page: ft.Page) -> int:
    """Usable chart width based on current window size."""
    raw = getattr(page, "width", None) or getattr(
        getattr(page, "window", None), "width", None
    )
    try:
        width = int(raw) if raw else 390
    except (TypeError, ValueError):
        width = 390
    return max(280, min(width - 40, 520))


class AnalyticsPage(ft.Column):
    """Month KPIs, category breakdown, and income/expense dynamics."""

    def __init__(self, page: ft.Page, state: "AppState") -> None:
        self._page = page
        self._state = state
        self._body = ft.Column(expand=True, scroll=ft.ScrollMode.AUTO, spacing=12)
        self._analytics_period = DEFAULT_ANALYTICS_PERIOD
        self._period_button = self._build_period_button(state.language)
        super().__init__(
            expand=True,
            spacing=0,
            controls=[
                page_header(
                    tr("nav.analytics", state.language),
                    leading=ft.IconButton(
                        icon=ft.Icons.ARROW_BACK,
                        on_click=lambda _e: state.close_secondary(),
                    ),
                    actions=[
                        self._period_button,
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
        run_async(page, self.reload)

    def _aggregate_period(
        self,
        accounts: list,
        txs: list,
        base: str,
        group_by,
        book: RateBook,
    ) -> tuple[
        Decimal,
        Decimal,
        Decimal,
        list[tuple[str, Decimal]],
        list[tuple[str, Decimal, Decimal]],
        bool,
    ]:
        """Single-pass KPI + chart aggregation using an in-memory rate book."""
        base = normalize_currency_code(base)
        total = Decimal("0.00")
        income = Decimal("0.00")
        expense = Decimal("0.00")
        ok = True
        category_totals: dict[str, Decimal] = defaultdict(lambda: Decimal("0.00"))
        period_income: dict[str, Decimal] = defaultdict(lambda: Decimal("0.00"))
        period_expense: dict[str, Decimal] = defaultdict(lambda: Decimal("0.00"))

        for account in accounts:
            src = normalize_currency_code(account.currency)
            converted = book.convert(account.balance, src, base)
            if converted is not None:
                total += converted
            elif src == base:
                total += account.balance
            else:
                ok = False

        for tx in txs:
            src = normalize_currency_code(tx.currency)
            converted = book.convert(tx.amount, src, base)
            if converted is None:
                if src == base:
                    converted = tx.amount
                else:
                    ok = False
                    continue
            key = GetTransactionStatsUseCase._period_key(tx.date, group_by)
            if tx.type == TransactionType.INCOME:
                income += converted
                period_income[key] += converted
            else:
                expense += converted
                period_expense[key] += converted
                category_totals[tx.category] += converted

        by_category = sorted(category_totals.items(), key=lambda kv: kv[1], reverse=True)
        keys = sorted(set(period_income) | set(period_expense))
        by_period = [(key, period_income[key], period_expense[key]) for key in keys]
        return total, income, expense, by_category, by_period, ok

    def _build_period_button(self, lang: str) -> ft.PopupMenuButton:
        """Header period picker next to the refresh action."""
        period_key = self._analytics_period
        period_label = tr(f"dashboard.period.{period_key}", lang)

        def on_select(key: str):
            def handler(_e: ft.ControlEvent) -> None:
                if self._analytics_period != key:
                    self._analytics_period = key
                    self._sync_period_button()
                    run_async(self._page, self.reload)

            return handler

        return ft.PopupMenuButton(
            tooltip=f"{tr('dashboard.period_filter', lang)}: {period_label}",
            icon=ft.Icons.DATE_RANGE,
            icon_color=ft.Colors.PRIMARY,
            items=[
                ft.PopupMenuItem(
                    content=ft.Text(tr(f"dashboard.period.{key}", lang)),
                    icon=ft.Icons.CHECK if key == period_key else None,
                    on_click=on_select(key),
                )
                for key in ANALYTICS_PERIOD_KEYS
            ],
        )

    def _sync_period_button(self) -> None:
        """Refresh header period menu labels and checkmarks."""
        lang = self._state.language
        period_key = self._analytics_period
        period_label = tr(f"dashboard.period.{period_key}", lang)

        def on_select(key: str):
            def handler(_e: ft.ControlEvent) -> None:
                if self._analytics_period != key:
                    self._analytics_period = key
                    self._sync_period_button()
                    run_async(self._page, self.reload)

            return handler

        self._period_button.tooltip = (
            f"{tr('dashboard.period_filter', lang)}: {period_label}"
        )
        self._period_button.items = [
            ft.PopupMenuItem(
                content=ft.Text(tr(f"dashboard.period.{key}", lang)),
                icon=ft.Icons.CHECK if key == period_key else None,
                on_click=on_select(key),
            )
            for key in ANALYTICS_PERIOD_KEYS
        ]
        safe_update(self._period_button)

    def _analytics_card_header(
        self,
        *,
        title: str,
        subtitle: str | None = None,
    ) -> ft.Control:
        """Title row for an analytics card."""
        header_controls: list[ft.Control] = [
            ft.Text(title, size=14, weight=ft.FontWeight.W_700),
        ]
        if subtitle:
            header_controls.append(
                ft.Text(subtitle, size=11, color=ft.Colors.ON_SURFACE_VARIANT),
            )
        return ft.Column(
            spacing=4,
            tight=True,
            controls=header_controls,
        )

    async def reload(self) -> None:
        """Reload analytics KPIs and charts."""
        lang = self._state.language
        self._body.controls = [loading_indicator(message=tr("action.refresh", lang))]
        safe_update(self._body)

        c = self._state.container
        now = datetime.now(timezone.utc)
        dark = is_dark_mode(self._page, self._state.theme_mode)
        chart_w = _content_width(self._page)

        try:
            accounts = await c.list_accounts.execute(active_only=True)
            period_cfg = resolve_analytics_period(self._analytics_period, now)
            period_label = tr(f"dashboard.period.{period_cfg.key}", lang)
            period_txs = await c.list_transactions.execute(
                date_from=period_cfg.date_from,
                date_to=period_cfg.date_to,
            )
        except Exception as exc:  # noqa: BLE001
            snack(self._page, str(exc), error=True)
            self._body.controls = [
                EmptyState(tr("error.generic", lang), icon=ft.Icons.ERROR_OUTLINE)
            ]
            safe_update(self._body)
            return

        base = normalize_currency_code(self._state.base_currency)
        book = await load_rate_book(c)
        (
            _total,
            period_income,
            period_expense,
            by_category,
            by_period,
            fx_ok,
        ) = self._aggregate_period(
            accounts, period_txs, base, period_cfg.group_by, book
        )
        if not fx_ok and c.update_exchange_rates is not None:
            try:
                await c.update_exchange_rates.execute(base=base)
                book = await load_rate_book(c)
                (
                    _total,
                    period_income,
                    period_expense,
                    by_category,
                    by_period,
                    fx_ok,
                ) = self._aggregate_period(
                    accounts, period_txs, base, period_cfg.group_by, book
                )
            except Exception:  # noqa: BLE001
                pass
        if not fx_ok:
            snack(self._page, tr("fx.missing_rates", lang), error=True)

        sub_analytics = None
        if getattr(c, "get_subscription_analytics", None) is not None:
            try:
                sub_analytics = await c.get_subscription_analytics.execute(
                    base_currency=base,
                    date_from=period_cfg.date_from,
                    date_to=period_cfg.date_to,
                )
            except Exception:  # noqa: BLE001
                sub_analytics = None

        if not period_txs and sub_analytics is None:
            self._body.controls = [
                EmptyState(
                    tr("empty.transactions", lang),
                    icon=ft.Icons.ANALYTICS_OUTLINED,
                )
            ]
            safe_update(self._body)
            return

        if not period_txs:
            controls: list[ft.Control] = []
            if sub_analytics is not None:
                controls.extend(
                    self._subscription_analytics_controls(sub_analytics, lang, base)
                )
            controls.append(ft.Container(height=10))
            self._body.controls = controls
            safe_update(self._body)
            return

        stats_income = period_income
        stats_expense = period_expense

        net = stats_income - stats_expense
        net_accent = ft.Colors.SECONDARY if net >= 0 else ft.Colors.ERROR

        pie = build_pie_chart_image(
            [localize_category_name(cat, lang) for cat, _amt in by_category[:6]],
            [amt for _cat, amt in by_category[:6]],
            title="",
            width=chart_w,
            height=300,
            dark=dark,
            language=lang,
        )
        series = by_period
        if period_cfg.max_chart_points and len(series) > period_cfg.max_chart_points:
            series = series[-period_cfg.max_chart_points :]
        line = build_line_chart_image(
            [format_chart_period_label(p[0], period_cfg.group_by) for p in series],
            [p[1] for p in series],
            [p[2] for p in series],
            title="",
            width=chart_w,
            height=240,
            dark=dark,
            language=lang,
        )

        palette = [
            "#2DD4BF",
            "#38BDF8",
            "#4ADE80",
            "#FBBF24",
            "#F87171",
            "#A78BFA",
        ]
        category_rows: list[ft.Control] = []
        expense_total = stats_expense or Decimal("0")
        for idx, (cat, amount) in enumerate(by_category[:6]):
            share = (
                (amount / expense_total * 100)
                if expense_total > 0
                else Decimal("0")
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
                                    localize_category_name(cat, lang),
                                    size=12,
                                    expand=True,
                                    overflow=ft.TextOverflow.ELLIPSIS,
                                    max_lines=1,
                                ),
                            ],
                        ),
                        ft.Text(
                            f"{format_money(amount, base)}  ({share:.0f}%)",
                            size=11,
                            color=ft.Colors.ON_SURFACE_VARIANT,
                            weight=ft.FontWeight.W_600,
                        ),
                    ],
                )
            )

        self._body.controls = [
            section_title(tr("dashboard.period_summary", lang, period=period_label)),
            ft.Row(
                spacing=10,
                vertical_alignment=ft.CrossAxisAlignment.START,
                controls=[
                    SummaryCard(
                        title=tr(
                            "dashboard.period_income", lang, period=period_label
                        ),
                        value=format_money(stats_income, base),
                        icon=ft.Icons.TRENDING_UP,
                        accent=ft.Colors.SECONDARY,
                        expand=True,
                    ),
                    SummaryCard(
                        title=tr(
                            "dashboard.period_expense", lang, period=period_label
                        ),
                        value=format_money(stats_expense, base),
                        icon=ft.Icons.TRENDING_DOWN,
                        accent=ft.Colors.ERROR,
                        expand=True,
                    ),
                ],
            ),
            card_surface(
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Row(
                            spacing=10,
                            tight=True,
                            controls=[
                                ft.Container(
                                    width=36,
                                    height=36,
                                    border_radius=11,
                                    bgcolor=ft.Colors.PRIMARY_CONTAINER,
                                    alignment=ft.Alignment.CENTER,
                                    content=ft.Icon(
                                        ft.Icons.ACCOUNT_BALANCE,
                                        size=18,
                                        color=ft.Colors.ON_PRIMARY_CONTAINER,
                                    ),
                                ),
                                ft.Column(
                                    spacing=2,
                                    tight=True,
                                    controls=[
                                        ft.Text(
                                            tr(
                                                "dashboard.period_net",
                                                lang,
                                                period=period_label,
                                            ),
                                            size=12,
                                            color=ft.Colors.ON_SURFACE_VARIANT,
                                        ),
                                        ft.Text(
                                            format_money(net, base),
                                            size=16,
                                            weight=ft.FontWeight.W_700,
                                            color=net_accent,
                                        ),
                                    ],
                                ),
                            ],
                        ),
                    ],
                ),
                padding=14,
            ),
            section_title(tr("dashboard.charts", lang)),
            card_surface(
                ft.Column(
                    spacing=10,
                    tight=True,
                    controls=[
                        self._analytics_card_header(
                            title=tr(
                                "dashboard.expense_for_period",
                                lang,
                                period=period_label,
                            ),
                            subtitle=tr(
                                "dashboard.expense_hint",
                                lang,
                                period=period_label,
                            ),
                        ),
                        pie,
                        *category_rows,
                    ],
                ),
                padding=12,
            ),
            card_surface(
                ft.Column(
                    spacing=10,
                    tight=True,
                    controls=[
                        self._analytics_card_header(
                            title=tr("dashboard.dynamics", lang),
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
            *self._subscription_analytics_controls(sub_analytics, lang, base),
            ft.Container(height=10),
        ]
        safe_update(self._body)

    def _subscription_analytics_controls(
        self,
        analytics,
        lang: str,
        base: str,
    ) -> list[ft.Control]:
        if analytics is None:
            return []
        top_rows: list[ft.Control] = []
        for item in analytics.top_subscriptions[:5]:
            top_rows.append(
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Text(str(item.get("name") or "—"), expand=True),
                        ft.Text(
                            format_money(item.get("amount") or 0, base),
                            weight=ft.FontWeight.W_600,
                        ),
                    ],
                )
            )
        if not top_rows:
            top_rows = [ft.Text("—", color=ft.Colors.ON_SURFACE_VARIANT)]
        return [
            section_title(tr("analytics.subscriptions", lang)),
            ft.Row(
                spacing=10,
                controls=[
                    SummaryCard(
                        title=tr("analytics.subscriptions_spent", lang),
                        value=format_money(analytics.total_spent, base),
                        icon=ft.Icons.SUBSCRIPTIONS_OUTLINED,
                        accent=ft.Colors.PRIMARY,
                        expand=True,
                    ),
                    SummaryCard(
                        title=tr("analytics.subscriptions_monthly_cost", lang),
                        value=format_money(analytics.total_monthly_cost, base),
                        icon=ft.Icons.CALENDAR_MONTH,
                        accent=ft.Colors.SECONDARY,
                        expand=True,
                    ),
                ],
            ),
            card_surface(
                ft.Column(
                    spacing=8,
                    tight=True,
                    controls=[
                        ft.Text(
                            f"{tr('analytics.subscriptions_active', lang)}: "
                            f"{analytics.total_active}",
                            weight=ft.FontWeight.W_600,
                        ),
                        ft.Text(
                            tr("analytics.subscriptions_top", lang),
                            weight=ft.FontWeight.W_700,
                        ),
                        *top_rows,
                    ],
                ),
                padding=14,
            ),
        ]
