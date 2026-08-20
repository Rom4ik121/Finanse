"""Dedicated analytics screen — compact KPIs and sectioned charts."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

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
from lib.presentation.styles import card_surface, muted_text, page_header, summary_strip
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

if TYPE_CHECKING:
    from lib.presentation.state.app_state import AppState

_PALETTE = (
    "#2DD4BF",
    "#38BDF8",
    "#4ADE80",
    "#FBBF24",
    "#F87171",
    "#A78BFA",
)


def _content_width(page: ft.Page) -> int:
    """Usable chart width based on current window size."""
    raw = getattr(page, "width", None) or getattr(
        getattr(page, "window", None), "width", None
    )
    try:
        width = int(raw) if raw else 390
    except (TypeError, ValueError):
        width = 390
    return max(260, min(width - 32, 640))


def _window_height(page: ft.Page) -> int:
    raw = getattr(page, "height", None) or getattr(
        getattr(page, "window", None), "height", None
    )
    try:
        return int(raw) if raw else 720
    except (TypeError, ValueError):
        return 720


class AnalyticsPage(ft.Column):
    """Period KPIs, category breakdown, and income/expense dynamics."""

    def __init__(self, page: ft.Page, state: "AppState") -> None:
        self._page = page
        self._state = state
        self._analytics_period = DEFAULT_ANALYTICS_PERIOD
        self._section = "spend"
        self._token = -1
        self._period_row = ft.Row(
            spacing=8,
            run_spacing=8,
            wrap=True,
        )
        self._kpi_host = ft.Column(spacing=8, tight=True)
        self._segments_host = ft.Container(content=self._segment_bar(state.language))
        self._section_host = ft.Container(expand=True)
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
                    padding=ft.Padding.only(left=12, right=12, bottom=8),
                    content=ft.Column(
                        expand=True,
                        spacing=8,
                        controls=[
                            self._period_row,
                            self._kpi_host,
                            self._segments_host,
                            self._section_host,
                        ],
                    ),
                ),
            ],
        )
        state.subscribe(self._on_state)
        run_async(page, self.reload)

    def _on_state(self, state: "AppState") -> None:
        token = state.analytics_token + state.transactions_token
        if token != self._token:
            run_async(self._page, self.reload)

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
            if getattr(tx, "transfer_id", None):
                continue
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

    def _period_chip(self, key: str, lang: str) -> ft.Control:
        selected = key == self._analytics_period
        return ft.Container(
            padding=ft.Padding.symmetric(horizontal=10, vertical=6),
            border_radius=14,
            bgcolor=(
                ft.Colors.PRIMARY_CONTAINER if selected else ft.Colors.SURFACE_CONTAINER
            ),
            border=ft.Border.all(
                1,
                ft.Colors.PRIMARY if selected else ft.Colors.OUTLINE_VARIANT,
            ),
            ink=True,
            on_click=lambda _e, k=key: self._set_period(k),
            content=ft.Text(
                tr(f"dashboard.period.{key}", lang),
                size=12,
                weight=ft.FontWeight.W_600,
                color=(
                    ft.Colors.ON_PRIMARY_CONTAINER
                    if selected
                    else ft.Colors.ON_SURFACE
                ),
            ),
        )

    def _set_period(self, key: str) -> None:
        if self._analytics_period == key:
            return
        self._analytics_period = key
        run_async(self._page, self.reload)

    def _rebuild_period_row(self, lang: str) -> None:
        self._period_row.controls = [
            self._period_chip(key, lang) for key in ANALYTICS_PERIOD_KEYS
        ]
        safe_update(self._period_row)

    def _segment_bar(self, lang: str) -> ft.Control:
        def cell(key: str, label: str) -> ft.Control:
            selected = self._section == key
            return ft.Container(
                expand=True,
                bgcolor=(
                    ft.Colors.PRIMARY_CONTAINER
                    if selected
                    else ft.Colors.TRANSPARENT
                ),
                ink=True,
                on_click=lambda _e, k=key: self._set_section(k),
                padding=ft.Padding.symmetric(vertical=8),
                content=ft.Text(
                    label,
                    size=12,
                    weight=ft.FontWeight.W_700,
                    text_align=ft.TextAlign.CENTER,
                    color=(
                        ft.Colors.ON_PRIMARY_CONTAINER
                        if selected
                        else ft.Colors.ON_SURFACE_VARIANT
                    ),
                ),
            )

        bar = ft.Container(
            height=38,
            border_radius=12,
            clip_behavior=ft.ClipBehavior.HARD_EDGE,
            bgcolor=ft.Colors.SURFACE_CONTAINER,
            border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
            content=ft.Row(
                spacing=0,
                expand=True,
                controls=[
                    cell("spend", tr("analytics.tab.spend", lang)),
                    cell("trend", tr("analytics.tab.trend", lang)),
                    cell("more", tr("analytics.tab.more", lang)),
                ],
            ),
        )
        return bar

    def _set_section(self, key: str) -> None:
        if self._section == key:
            return
        self._section = key
        self._refresh_segments()
        self._show_section()

    def _refresh_segments(self) -> None:
        self._segments_host.content = self._segment_bar(self._state.language)
        safe_update(self._segments_host)

    def _show_section(self) -> None:
        view = {
            "spend": getattr(self, "_spend_view", None),
            "trend": getattr(self, "_trend_view", None),
            "more": getattr(self, "_more_view", None),
        }.get(self._section)
        self._section_host.content = view or ft.Container()
        safe_update(self._section_host)

    def _metric_cell(
        self,
        label: str,
        value: str,
        *,
        color: Optional[str] = None,
    ) -> ft.Control:
        return ft.Container(
            expand=True,
            content=ft.Column(
                spacing=2,
                tight=True,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Text(
                        label,
                        size=11,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                        text_align=ft.TextAlign.CENTER,
                        max_lines=1,
                        overflow=ft.TextOverflow.ELLIPSIS,
                    ),
                    ft.Text(
                        value,
                        size=13,
                        weight=ft.FontWeight.W_700,
                        color=color or ft.Colors.ON_SURFACE,
                        text_align=ft.TextAlign.CENTER,
                        max_lines=2,
                        overflow=ft.TextOverflow.ELLIPSIS,
                    ),
                ],
            ),
        )

    def _metrics_card(self, cells: list[ft.Control]) -> ft.Control:
        return card_surface(
            ft.Row(
                spacing=4,
                vertical_alignment=ft.CrossAxisAlignment.START,
                controls=cells,
            ),
            padding=10,
        )

    async def reload(self) -> None:
        """Reload analytics KPIs and charts."""
        self._token = (
            self._state.analytics_token + self._state.transactions_token
        )
        lang = self._state.language
        self._rebuild_period_row(lang)
        self._kpi_host.controls = [loading_indicator(message=tr("action.refresh", lang))]
        self._section_host.content = ft.Container()
        safe_update(self._kpi_host)
        safe_update(self._section_host)

        c = self._state.container
        now = datetime.now(timezone.utc)
        dark = is_dark_mode(self._page, self._state.theme_mode)
        chart_w = _content_width(self._page)
        chart_h = max(150, min(240, _window_height(self._page) - 380))

        try:
            accounts = await c.list_accounts.execute(active_only=True)
            period_cfg = resolve_analytics_period(self._analytics_period, now)
            period_txs = await c.list_transactions.execute(
                date_from=period_cfg.date_from,
                date_to=period_cfg.date_to,
            )
        except Exception as exc:  # noqa: BLE001
            snack(self._page, str(exc), error=True)
            self._kpi_host.controls = [
                EmptyState(tr("error.generic", lang), icon=ft.Icons.ERROR_OUTLINE)
            ]
            safe_update(self._kpi_host)
            return

        base = normalize_currency_code(self._state.base_currency)
        book = await load_rate_book(c)
        (
            total_balance,
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
                    total_balance,
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

        net = period_income - period_expense
        net_color = ft.Colors.SECONDARY if net >= 0 else ft.Colors.ERROR
        ops_count = sum(
            1 for tx in period_txs if not getattr(tx, "transfer_id", None)
        )
        if period_cfg.date_from is None:
            days = 365
        else:
            days = max(
                1,
                (period_cfg.date_to.date() - period_cfg.date_from.date()).days,
            )
        avg_day = (period_expense / Decimal(days)) if days else period_expense
        savings = (
            f"{((net / period_income) * 100):.0f}%"
            if period_income > 0
            else "—"
        )

        self._kpi_host.controls = [
            self._metrics_card(
                [
                    self._metric_cell(
                        tr("analytics.income", lang),
                        format_money(period_income, base),
                        color=ft.Colors.SECONDARY,
                    ),
                    self._metric_cell(
                        tr("analytics.expense", lang),
                        format_money(period_expense, base),
                        color=ft.Colors.ERROR,
                    ),
                    self._metric_cell(
                        tr("analytics.net", lang),
                        format_money(net, base),
                        color=net_color,
                    ),
                ]
            ),
        ]
        safe_update(self._kpi_host)

        pie_cats = by_category[:6]
        pie = build_pie_chart_image(
            [localize_category_name(cat, lang) for cat, _amt in pie_cats],
            [amt for _cat, amt in pie_cats],
            title="",
            width=chart_w,
            height=chart_h,
            dark=dark,
            language=lang,
        )
        category_rows: list[ft.Control] = []
        expense_total = period_expense or Decimal("0")
        for idx, (cat, amount) in enumerate(pie_cats):
            share = (
                (amount / expense_total * 100) if expense_total > 0 else Decimal("0")
            )
            category_rows.append(
                ft.Row(
                    spacing=8,
                    controls=[
                        ft.Container(
                            width=8,
                            height=8,
                            border_radius=4,
                            bgcolor=_PALETTE[idx % len(_PALETTE)],
                        ),
                        ft.Text(
                            localize_category_name(cat, lang),
                            size=12,
                            expand=True,
                            overflow=ft.TextOverflow.ELLIPSIS,
                            max_lines=1,
                        ),
                        ft.Text(
                            f"{format_money(amount, base)}  {share:.0f}%",
                            size=11,
                            weight=ft.FontWeight.W_600,
                            color=ft.Colors.ON_SURFACE_VARIANT,
                        ),
                    ],
                )
            )
        if not pie_cats:
            category_rows = [
                muted_text(tr("empty.transactions", lang), size=12),
            ]

        self._spend_view = ft.Column(
            expand=True,
            scroll=ft.ScrollMode.AUTO,
            spacing=8,
            controls=[
                card_surface(
                    ft.Column(spacing=8, tight=True, controls=[pie, *category_rows]),
                    padding=10,
                )
            ],
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
            height=max(chart_h, 180),
            dark=dark,
            language=lang,
        )
        self._trend_view = ft.Column(
            expand=True,
            scroll=ft.ScrollMode.AUTO,
            spacing=8,
            controls=[
                card_surface(
                    ft.Column(
                        spacing=8,
                        tight=True,
                        controls=[
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
                                                tr("transaction.income", lang), size=11
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
                                                tr("transaction.expense", lang), size=11
                                            ),
                                        ],
                                    ),
                                ],
                            ),
                            line,
                        ],
                    ),
                    padding=10,
                )
            ],
        )

        more_controls: list[ft.Control] = [
            self._metrics_card(
                [
                    self._metric_cell(
                        tr("analytics.balance", lang),
                        format_money(total_balance, base),
                    ),
                    self._metric_cell(tr("analytics.savings", lang), savings),
                ]
            ),
            self._metrics_card(
                [
                    self._metric_cell(
                        tr("analytics.avg_day", lang),
                        format_money(avg_day, base),
                        color=ft.Colors.ERROR,
                    ),
                    self._metric_cell(tr("analytics.ops", lang), str(ops_count)),
                ]
            ),
        ]
        more_controls.extend(
            self._subscription_analytics_controls(sub_analytics, lang, base)
        )
        self._more_view = ft.Column(
            expand=True,
            scroll=ft.ScrollMode.AUTO,
            spacing=8,
            controls=more_controls,
        )
        self._refresh_segments()
        self._show_section()

    def _subscription_analytics_controls(
        self,
        analytics,
        lang: str,
        base: str,
    ) -> list[ft.Control]:
        if analytics is None:
            return [
                card_surface(
                    muted_text(tr("analytics.no_subs", lang)),
                    padding=12,
                )
            ]
        top_rows: list[ft.Control] = []
        for item in analytics.top_subscriptions[:5]:
            top_rows.append(
                ft.Row(
                    spacing=8,
                    controls=[
                        ft.Text(
                            str(item.get("name") or "—"),
                            expand=True,
                            size=12,
                            overflow=ft.TextOverflow.ELLIPSIS,
                            max_lines=1,
                        ),
                        ft.Text(
                            format_money(item.get("amount") or 0, base),
                            weight=ft.FontWeight.W_600,
                            size=12,
                        ),
                    ],
                )
            )
        if not top_rows:
            top_rows = [muted_text("—")]
        return [
            self._metrics_card(
                [
                    self._metric_cell(
                        tr("analytics.subscriptions_spent", lang),
                        format_money(analytics.total_spent, base),
                    ),
                    self._metric_cell(
                        tr("analytics.subscriptions_monthly_cost", lang),
                        format_money(analytics.total_monthly_cost, base),
                    ),
                    self._metric_cell(
                        tr("analytics.subscriptions_active", lang),
                        str(analytics.total_active),
                    ),
                ]
            ),
            card_surface(
                ft.Column(
                    spacing=6,
                    tight=True,
                    controls=[
                        ft.Text(
                            tr("analytics.subscriptions_top", lang),
                            size=13,
                            weight=ft.FontWeight.W_700,
                        ),
                        *top_rows,
                    ],
                ),
                padding=12,
            ),
        ]
