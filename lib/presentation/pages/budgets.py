"""Monthly category budgets page."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import TYPE_CHECKING, Optional

import flet as ft

from lib.domain.entities.budget import Budget, BudgetProgress
from lib.domain.entities.transaction import TransactionType
from lib.infrastructure.services.localization import localize_category_name
from lib.presentation.notification_badges import (
    BUDGET_ALERT_KINDS,
    mark_related_read,
    pending_related_ids,
)
from lib.presentation.styles import card_surface, muted_text, page_header, summary_strip
from lib.presentation.money_input import make_amount_field, parse_amount
from lib.presentation.utils import category_icon, format_money, run_async, snack, tr
from lib.presentation.widgets.category_picker import CategoryPicker
from lib.presentation.widgets.confirm_dialog import confirm_dialog
from lib.presentation.widgets.empty_state import EmptyState
from lib.presentation.widgets.fullscreen_form import open_fullscreen_form
from lib.presentation.widgets.loading import loading_indicator

if TYPE_CHECKING:
    from lib.presentation.state.app_state import AppState


def _budget_bar_color(percent: Decimal) -> str:
    if percent > 100:
        return ft.Colors.ERROR
    if percent >= 80:
        return ft.Colors.AMBER
    return ft.Colors.GREEN


class BudgetsPage(ft.Column):
    """Manage monthly spending limits per category."""

    def __init__(self, page: ft.Page, state: "AppState") -> None:
        self._page = page
        self._state = state
        now = datetime.now(timezone.utc)
        self._month = now.month
        self._year = now.year
        self._list = ft.Column(expand=True, scroll=ft.ScrollMode.AUTO, spacing=12)
        self._token = -1
        self._categories_by_name: dict[str, object] = {}
        super().__init__(
            expand=True,
            spacing=0,
            controls=[
                page_header(
                    tr("budgets.title", state.language),
                    leading=ft.IconButton(
                        icon=ft.Icons.ARROW_BACK,
                        on_click=lambda _e: state.close_secondary(),
                    ),
                    actions=[
                        ft.IconButton(
                            icon=ft.Icons.TUNE,
                            tooltip=tr("action.filters", state.language),
                            on_click=lambda _e: self._open_filters(),
                        ),
                        ft.IconButton(
                            icon=ft.Icons.ADD,
                            tooltip=tr("budgets.add", state.language),
                            on_click=lambda _e: self._open_editor(),
                        ),
                    ],
                ),
                ft.Container(
                    expand=True,
                    padding=ft.Padding.symmetric(horizontal=16),
                    content=self._list,
                ),
            ],
        )
        state.subscribe(self._on_state)
        run_async(page, self.reload)

    def _on_state(self, state: "AppState") -> None:
        if state.budgets_token != self._token:
            run_async(self._page, self.reload)

    def _open_filters(self) -> None:
        lang = self._state.language
        years = list(range(self._year - 2, self._year + 3))
        if self._year not in years:
            years.append(self._year)
            years.sort()
        month_dd = ft.Dropdown(
            label=tr("budgets.month", lang),
            dense=True,
            value=str(self._month),
            options=[
                ft.DropdownOption(
                    key=str(i),
                    text=tr(f"budgets.month.{i}", lang),
                )
                for i in range(1, 13)
            ],
        )
        year_dd = ft.Dropdown(
            label=tr("budgets.year", lang),
            dense=True,
            value=str(self._year),
            options=[ft.DropdownOption(key=str(y), text=str(y)) for y in years],
        )

        async def _apply() -> None:
            try:
                self._month = int(month_dd.value or self._month)
                self._year = int(year_dd.value or self._year)
            except (TypeError, ValueError):
                pass
            close()
            await self.reload()

        close = open_fullscreen_form(
            self._page,
            title=tr("action.filters", lang),
            lang=lang,
            overlay_key="budget_filters",
            body=[month_dd, year_dd],
            on_save=_apply,
            save_label=tr("action.apply", lang, default=tr("action.save", lang)),
            save_icon=ft.Icons.CHECK,
        )

    async def reload(self) -> None:
        """Reload budgets for the selected month."""
        self._token = self._state.budgets_token
        lang = self._state.language
        self._list.controls = [loading_indicator()]
        self._list.update()
        alert_ids = pending_related_ids(
            self._state.container,
            self._state.settings,
            BUDGET_ALERT_KINDS,
        )
        for related_id in list(alert_ids):
            mark_related_read(self._state.container, related_id, BUDGET_ALERT_KINDS)
        if alert_ids:
            self._state.bump_refresh("dashboard")
        try:
            items = await self._state.container.get_budgets_for_month.execute(
                self._month, self._year
            )
            categories = await self._state.container.list_categories.execute(
                active_only=False
            )
            self._categories_by_name = {c.name: c for c in categories}
        except Exception as exc:  # noqa: BLE001
            snack(self._page, str(exc), error=True)
            self._list.controls = [EmptyState(tr("error.generic", lang))]
            self._list.update()
            return
        currency = self._state.base_currency
        total_limit = sum((item.limit for item in items), Decimal("0"))
        total_spent = sum((item.spent for item in items), Decimal("0"))
        remaining = total_limit - total_spent
        if remaining < 0:
            remaining = Decimal("0")
        period = (
            f"{tr(f'budgets.month.{self._month}', lang)} {self._year}"
        )
        controls: list[ft.Control] = [
            muted_text(period, size=13),
            summary_strip(
                [
                    (
                        tr("budgets.total_limit", lang),
                        format_money(total_limit, currency),
                        ft.Colors.PRIMARY,
                    ),
                    (
                        tr("budgets.total_spent", lang),
                        format_money(total_spent, currency),
                        ft.Colors.ERROR if total_spent > total_limit else ft.Colors.SECONDARY,
                    ),
                    (
                        tr("budgets.remaining", lang),
                        format_money(remaining, currency),
                        ft.Colors.ERROR if total_spent > total_limit else None,
                    ),
                ]
            ),
        ]
        if not items:
            controls.append(
                EmptyState(
                    tr("budgets.no_budgets", lang),
                    icon=ft.Icons.PIE_CHART,
                    action_label=tr("budgets.add", lang),
                    on_action=lambda _e: self._open_editor(),
                )
            )
        else:
            for progress in items:
                controls.append(self._card(progress, lang))
        self._list.controls = controls
        self._list.update()

    def _card(self, progress: BudgetProgress, lang: str) -> ft.Control:
        budget = progress.budget
        currency = self._state.base_currency
        category = self._categories_by_name.get(progress.category_id)
        icon_name = getattr(category, "icon", None) or "category"
        name = localize_category_name(progress.category_id, lang)
        percent = progress.percent
        bar_value = min(float(percent) / 100.0, 1.0)
        color = _budget_bar_color(percent)
        status = (
            tr("budgets.over_budget", lang)
            if progress.is_over_budget
            else tr("budgets.percent", lang)
        )
        return card_surface(
            ft.Column(
                spacing=8,
                tight=True,
                controls=[
                    ft.Row(
                        spacing=10,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Icon(category_icon(icon_name), size=22),
                            ft.Text(
                                name,
                                expand=True,
                                weight=ft.FontWeight.W_600,
                                overflow=ft.TextOverflow.ELLIPSIS,
                            ),
                            ft.IconButton(
                                icon=ft.Icons.EDIT_OUTLINED,
                                tooltip=tr("budgets.edit", lang),
                                on_click=lambda _e, b=budget: self._open_editor(b),
                            ),
                            ft.IconButton(
                                icon=ft.Icons.DELETE_OUTLINE,
                                tooltip=tr("budgets.delete", lang),
                                on_click=lambda _e, b=budget: self._confirm_delete(b),
                            ),
                        ],
                    ),
                    ft.Text(
                        f"{format_money(progress.spent, currency)} / "
                        f"{format_money(progress.limit, currency)}",
                        size=13,
                    ),
                    ft.ProgressBar(
                        value=bar_value,
                        color=color,
                        bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
                    ),
                    ft.Row(
                        controls=[
                            ft.Text(
                                f"{percent:.0f}% · {status}",
                                size=12,
                                color=color,
                                expand=True,
                            ),
                            muted_text(
                                f"{tr('budgets.remaining', lang)}: "
                                f"{format_money(progress.remaining, currency)}",
                            ),
                        ],
                    ),
                ],
            )
        )

    def _confirm_delete(self, budget: Budget) -> None:
        lang = self._state.language

        async def _do() -> None:
            try:
                await self._state.container.delete_budget.execute(budget.id)
            except Exception as exc:  # noqa: BLE001
                snack(self._page, str(exc), error=True)
                return
            self._state.bump_refresh("dashboard", "budgets")
            snack(self._page, tr("budgets.deleted", lang))

        confirm_dialog(
            self._page,
            title=tr("budgets.delete", lang),
            message=tr("budgets.delete_confirm", lang, category=budget.category_id),
            confirm_text=tr("budgets.delete", lang),
            cancel_text=tr("action.cancel", lang),
            on_confirm=_do,
        )

    def _open_editor(self, budget: Optional[Budget] = None) -> None:
        lang = self._state.language
        picker = CategoryPicker(
            self._page,
            self._state,
            tx_type=TransactionType.EXPENSE.value,
            initial_name=budget.category_id if budget else None,
        )
        run_async(self._page, picker.reload)
        limit_tf = make_amount_field(
            lang,
            label=tr("budgets.limit", lang),
            value=budget.amount_limit if budget else "",
            dense=True,
            border_radius=12,
            filled=True,
            bgcolor=ft.Colors.SURFACE,
        )

        async def _save() -> None:
            name = picker.selected_name
            if not name:
                snack(self._page, tr("budgets.category_required", lang), error=True)
                return
            try:
                limit = parse_amount(limit_tf.value)
            except (InvalidOperation, ValueError):
                snack(self._page, tr("budgets.limit_required", lang), error=True)
                return
            try:
                await self._state.container.set_budget.execute(
                    name, self._month, self._year, limit
                )
            except Exception as exc:  # noqa: BLE001
                snack(self._page, str(exc), error=True)
                return
            close()
            self._state.bump_refresh("dashboard", "budgets")
            snack(self._page, tr("budgets.saved", lang))

        close = open_fullscreen_form(
            self._page,
            title=tr("budgets.edit" if budget else "budgets.add", lang),
            lang=lang,
            overlay_key="budget_form",
            body=[
                picker,
                limit_tf,
            ],
            on_save=_save,
        )
