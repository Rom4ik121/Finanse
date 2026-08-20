"""Per-account statistics: KPIs, charts, recent activity."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING

import flet as ft

from lib.infrastructure.services.localization import localize_category_name
from lib.presentation.account_icons import account_icon_control
from lib.presentation.account_stats import aggregate_account_period
from lib.presentation.analytics_period import (
    ANALYTICS_PERIOD_KEYS,
    DEFAULT_ANALYTICS_PERIOD,
    format_chart_period_label,
    resolve_analytics_period,
)
from lib.presentation.styles import card_surface, muted_text, page_header, section_title
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
from lib.presentation.widgets.transaction_tile import TransactionTile

if TYPE_CHECKING:
    from lib.presentation.state.app_state import AppState


def _content_width(page: ft.Page) -> int:
    raw = getattr(page, "width", None) or getattr(
        getattr(page, "window", None), "width", None
    )
    try:
        width = int(raw) if raw else 390
    except (TypeError, ValueError):
        width = 390
    return max(280, min(width - 40, 520))


class AccountDetailPage(ft.Column):
    """Statistics for a single account opened from the accounts list."""

    def __init__(self, page: ft.Page, state: "AppState", account_id: str) -> None:
        self._page = page
        self._state = state
        self._account_id = account_id
        self._body = ft.Column(expand=True, scroll=ft.ScrollMode.AUTO, spacing=12)
        self._period = DEFAULT_ANALYTICS_PERIOD
        self._token = -1
        self._period_button = self._build_period_button(state.language)
        super().__init__(
            expand=True,
            spacing=0,
            controls=[
                page_header(
                    tr("account.stats.title", state.language),
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
        state.subscribe(self._on_state)
        run_async(page, self.reload)

    def _on_state(self, state: "AppState") -> None:
        token = state.accounts_token + state.transactions_token
        if token != self._token:
            run_async(self._page, self.reload)

    def _build_period_button(self, lang: str) -> ft.PopupMenuButton:
        period_label = tr(f"dashboard.period.{self._period}", lang)

        def on_select(key: str):
            def handler(_e: ft.ControlEvent) -> None:
                if self._period != key:
                    self._period = key
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
                    icon=ft.Icons.CHECK if key == self._period else None,
                    on_click=on_select(key),
                )
                for key in ANALYTICS_PERIOD_KEYS
            ],
        )

    def _sync_period_button(self) -> None:
        lang = self._state.language
        period_label = tr(f"dashboard.period.{self._period}", lang)

        def on_select(key: str):
            def handler(_e: ft.ControlEvent) -> None:
                if self._period != key:
                    self._period = key
                    self._sync_period_button()
                    run_async(self._page, self.reload)

            return handler

        self._period_button.tooltip = (
            f"{tr('dashboard.period_filter', lang)}: {period_label}"
        )
        self._period_button.items = [
            ft.PopupMenuItem(
                content=ft.Text(tr(f"dashboard.period.{key}", lang)),
                icon=ft.Icons.CHECK if key == self._period else None,
                on_click=on_select(key),
            )
            for key in ANALYTICS_PERIOD_KEYS
        ]
        safe_update(self._period_button)

    def _hero(
        self,
        *,
        name: str,
        currency: str,
        color: str,
        icon: str,
        balance: Decimal,
        base_line: str | None,
        lang: str,
    ) -> ft.Control:
        return card_surface(
            ft.Column(
                spacing=10,
                tight=True,
                controls=[
                    ft.Row(
                        spacing=12,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Container(
                                width=48,
                                height=48,
                                border_radius=14,
                                bgcolor=color,
                                alignment=ft.Alignment.CENTER,
                                content=account_icon_control(
                                    icon, size=24, color=ft.Colors.WHITE
                                ),
                            ),
                            ft.Column(
                                spacing=2,
                                tight=True,
                                expand=True,
                                controls=[
                                    ft.Text(
                                        name,
                                        size=18,
                                        weight=ft.FontWeight.W_700,
                                        max_lines=1,
                                        overflow=ft.TextOverflow.ELLIPSIS,
                                    ),
                                    muted_text(currency, size=12),
                                ],
                            ),
                        ],
                    ),
                    ft.Text(
                        format_money(balance, currency),
                        size=26,
                        weight=ft.FontWeight.W_700,
                    ),
                    *([muted_text(base_line)] if base_line else []),
                ],
            ),
            accent=color,
            padding=16,
        )

    async def reload(self) -> None:
        """Load the account and rebuild KPIs / charts."""
        self._token = (
            self._state.accounts_token + self._state.transactions_token
        )
        lang = self._state.language
        self._body.controls = [loading_indicator(message=tr("action.refresh", lang))]
        safe_update(self._body)

        c = self._state.container
        now = datetime.now(timezone.utc)
        dark = is_dark_mode(self._page, self._state.theme_mode)
        chart_w = _content_width(self._page)
        period_cfg = resolve_analytics_period(self._period, now)
        period_label = tr(f"dashboard.period.{period_cfg.key}", lang)

        try:
            account = await c.account_repository.get_by_id(self._account_id)
            if account is None:
                self._body.controls = [
                    EmptyState(
                        tr("account.stats.missing", lang),
                        icon=ft.Icons.ACCOUNT_BALANCE_WALLET_OUTLINED,
                    )
                ]
                safe_update(self._body)
                return
            txs = await c.list_transactions.execute(
                account_id=account.id,
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

        currency = account.currency
        base = self._state.base_currency
        base_line = None
        if currency.upper() != base.upper():
            book = await load_rate_book(c)
            converted = book.convert(account.balance, currency, base)
            if converted is not None:
                base_line = f"≈ {format_money(converted, base)}"

        stats = aggregate_account_period(txs, period_cfg.group_by)
        net = stats.income - stats.expense
        net_accent = ft.Colors.SECONDARY if net >= 0 else ft.Colors.ERROR

        controls: list[ft.Control] = [
            self._hero(
                name=account.name,
                currency=currency,
                color=account.color or ft.Colors.PRIMARY,
                icon=account.icon,
                balance=account.balance,
                base_line=base_line,
                lang=lang,
            ),
            section_title(tr("dashboard.period_summary", lang, period=period_label)),
            ft.Row(
                spacing=10,
                controls=[
                    SummaryCard(
                        title=tr("dashboard.period_income", lang, period=period_label),
                        value=format_money(stats.income, currency),
                        icon=ft.Icons.TRENDING_UP,
                        accent=ft.Colors.SECONDARY,
                        expand=True,
                    ),
                    SummaryCard(
                        title=tr("dashboard.period_expense", lang, period=period_label),
                        value=format_money(stats.expense, currency),
                        icon=ft.Icons.TRENDING_DOWN,
                        accent=ft.Colors.ERROR,
                        expand=True,
                    ),
                ],
            ),
            card_surface(
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Column(
                            spacing=2,
                            tight=True,
                            controls=[
                                muted_text(
                                    tr(
                                        "dashboard.period_net",
                                        lang,
                                        period=period_label,
                                    ),
                                    size=12,
                                ),
                                ft.Text(
                                    format_money(net, currency),
                                    size=16,
                                    weight=ft.FontWeight.W_700,
                                    color=net_accent,
                                ),
                            ],
                        ),
                        muted_text(
                            tr(
                                "account.stats.count",
                                lang,
                                count=stats.tx_count,
                            ),
                            size=12,
                        ),
                    ],
                ),
                padding=14,
            ),
        ]

        if stats.transfer_in > 0 or stats.transfer_out > 0:
            controls.append(
                card_surface(
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Column(
                                spacing=2,
                                tight=True,
                                controls=[
                                    muted_text(tr("account.stats.transfer_in", lang)),
                                    ft.Text(
                                        format_money(stats.transfer_in, currency),
                                        weight=ft.FontWeight.W_700,
                                        color=ft.Colors.SECONDARY,
                                    ),
                                ],
                            ),
                            ft.Column(
                                spacing=2,
                                tight=True,
                                horizontal_alignment=ft.CrossAxisAlignment.END,
                                controls=[
                                    muted_text(tr("account.stats.transfer_out", lang)),
                                    ft.Text(
                                        format_money(stats.transfer_out, currency),
                                        weight=ft.FontWeight.W_700,
                                        color=ft.Colors.ERROR,
                                    ),
                                ],
                            ),
                        ],
                    ),
                    padding=14,
                )
            )

        if not txs:
            controls.append(
                EmptyState(
                    tr("account.stats.empty", lang),
                    icon=ft.Icons.ANALYTICS_OUTLINED,
                )
            )
            self._body.controls = controls
            safe_update(self._body)
            return

        pie_cats = stats.by_category[:6]
        pie = build_pie_chart_image(
            [localize_category_name(cat, lang) for cat, _amt in pie_cats],
            [amt for _cat, amt in pie_cats],
            title="",
            width=chart_w,
            height=260,
            dark=dark,
            language=lang,
        )
        series = stats.by_period
        if period_cfg.max_chart_points and len(series) > period_cfg.max_chart_points:
            series = series[-period_cfg.max_chart_points :]
        line = build_line_chart_image(
            [format_chart_period_label(p[0], period_cfg.group_by) for p in series],
            [p[1] for p in series],
            [p[2] for p in series],
            title="",
            width=chart_w,
            height=220,
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
        spend_total = stats.ops_expense or Decimal("0")
        for idx, (cat, amount) in enumerate(pie_cats):
            share = (amount / spend_total * 100) if spend_total > 0 else Decimal("0")
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
                            f"{format_money(amount, currency)}  ({share:.0f}%)",
                            size=11,
                            color=ft.Colors.ON_SURFACE_VARIANT,
                            weight=ft.FontWeight.W_600,
                        ),
                    ],
                )
            )

        controls.extend(
            [
                section_title(tr("dashboard.charts", lang)),
                card_surface(
                    ft.Column(
                        spacing=10,
                        tight=True,
                        controls=[
                            ft.Text(
                                tr("account.stats.spend_chart", lang),
                                size=14,
                                weight=ft.FontWeight.W_700,
                            ),
                            muted_text(tr("account.stats.spend_hint", lang), size=11),
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
                            ft.Text(
                                tr("dashboard.dynamics", lang),
                                size=14,
                                weight=ft.FontWeight.W_700,
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
                section_title(tr("account.stats.recent", lang)),
            ]
        )
        for tx in txs[:10]:
            controls.append(TransactionTile(tx, language=lang))
        self._body.controls = controls
        safe_update(self._body)
