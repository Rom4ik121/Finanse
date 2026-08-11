"""Transactions list page with search, filters, grouping, and CRUD dialogs."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import TYPE_CHECKING, Optional

import flet as ft

from lib.core.config import SAVINGS_CATEGORIES
from lib.domain.entities.category import CategoryKind
from lib.domain.entities.transaction import Transaction, TransactionType
from lib.domain.use_cases.transactions import StatsPeriod
from lib.presentation.styles import page_header
from lib.presentation.utils import format_date, run_async, safe_update, snack, tr
from lib.presentation.widgets.category_picker import CategoryPicker
from lib.presentation.widgets.confirm_dialog import confirm_dialog
from lib.presentation.widgets.date_time_field import DateTimeField
from lib.presentation.widgets.empty_state import EmptyState
from lib.presentation.widgets.fullscreen_form import open_fullscreen_form
from lib.presentation.widgets.loading import loading_indicator
from lib.presentation.widgets.transaction_tile import TransactionTile

if TYPE_CHECKING:
    from lib.presentation.state.app_state import AppState


def _parse_date(value: str, *, end_of_day: bool = False) -> Optional[datetime]:
    text = (value or "").strip()
    if not text:
        return None
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(text, fmt).replace(tzinfo=timezone.utc)
            if fmt == "%Y-%m-%d" and end_of_day:
                dt = dt.replace(hour=23, minute=59, second=59)
            return dt
        except ValueError:
            continue
    raise ValueError("invalid date")


def _period_key(dt: datetime, group_by: str) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    if group_by == StatsPeriod.WEEK.value:
        iso = dt.isocalendar()
        return f"{iso.year}-W{iso.week:02d}"
    if group_by == StatsPeriod.MONTH.value:
        return dt.strftime("%Y-%m")
    return format_date(dt)


class TransactionsPage(ft.Column):
    """Searchable / filterable transaction list with day/week/month grouping."""

    def __init__(self, page: ft.Page, state: "AppState") -> None:
        self._page = page
        self._state = state
        self._token = -1
        self._accounts: list = []
        self._goals: list = []
        self._category_map: dict[str, object] = {}
        self._list = ft.Column(spacing=6, expand=True, scroll=ft.ScrollMode.AUTO)
        lang = state.language
        self._search = ft.TextField(
            label=tr("field.search", lang),
            prefix_icon=ft.Icons.SEARCH,
            on_change=lambda _e: run_async(page, self.reload),
            dense=True,
            border_radius=12,
            filled=True,
            bgcolor=ft.Colors.SURFACE_CONTAINER,
        )
        # Filter values (controls are created fresh inside the dialog).
        self._type_value = "all"
        self._category_value = "all"
        self._date_from_value = ""
        self._date_to_value = ""
        self._group_by_value = StatsPeriod.DAY.value
        self._filter_summary = ft.Text(
            "",
            size=12,
            color=ft.Colors.ON_SURFACE_VARIANT,
            overflow=ft.TextOverflow.ELLIPSIS,
            max_lines=1,
            expand=True,
        )
        super().__init__(
            expand=True,
            spacing=6,
            controls=[
                page_header(
                    tr("nav.transactions", lang),
                    actions=[
                        ft.IconButton(
                            icon=ft.Icons.REFRESH,
                            icon_color=ft.Colors.PRIMARY,
                            tooltip=tr("action.refresh", lang),
                            on_click=lambda _e: run_async(page, self.reload),
                        ),
                        ft.IconButton(
                            icon=ft.Icons.ADD,
                            icon_color=ft.Colors.PRIMARY,
                            tooltip=tr("action.add", lang),
                            on_click=lambda _e: run_async(page, self._open_editor_async),
                        ),
                    ],
                ),
                ft.Container(
                    padding=ft.padding.symmetric(horizontal=12),
                    content=ft.Column(
                        spacing=8,
                        tight=True,
                        controls=[
                            self._search,
                            ft.Row(
                                spacing=8,
                                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                controls=[
                                    ft.OutlinedButton(
                                        tr("action.filters", lang),
                                        icon=ft.Icons.TUNE,
                                        style=ft.ButtonStyle(
                                            shape=ft.RoundedRectangleBorder(radius=12),
                                            padding=ft.padding.symmetric(
                                                horizontal=14, vertical=12
                                            ),
                                        ),
                                        on_click=lambda _e: self._open_filters(),
                                    ),
                                    self._filter_summary,
                                ],
                            ),
                        ],
                    ),
                ),
                ft.Container(
                    expand=True,
                    padding=ft.padding.symmetric(horizontal=10),
                    content=self._list,
                ),
            ],
        )
        state.subscribe(self._on_state)
        run_async(page, self.reload)

    def _on_state(self, state: "AppState") -> None:
        if state.transactions_token != self._token:
            run_async(self._page, self.reload)

    def _filter_summary_text(self) -> str:
        lang = self._state.language
        parts: list[str] = []
        if self._type_value not in (None, "all"):
            key = (
                "transaction.income"
                if self._type_value == TransactionType.INCOME.value
                else "transaction.expense"
            )
            parts.append(tr(key, lang))
        if self._category_value not in (None, "all"):
            parts.append(str(self._category_value))
        if self._date_from_value.strip() or self._date_to_value.strip():
            parts.append(
                f"{self._date_from_value.strip() or '…'} – "
                f"{self._date_to_value.strip() or '…'}"
            )
        group_label = {
            StatsPeriod.DAY.value: tr("filter.group.day", lang),
            StatsPeriod.WEEK.value: tr("filter.group.week", lang),
            StatsPeriod.MONTH.value: tr("filter.group.month", lang),
        }.get(self._group_by_value, self._group_by_value)
        parts.append(group_label)
        return " · ".join(parts)

    def _open_filters(self) -> None:
        run_async(self._page, self._open_filters_async)

    async def _open_filters_async(self) -> None:
        lang = self._state.language
        type_dd = ft.Dropdown(
            label=tr("field.type", lang),
            value=self._type_value,
            options=[
                ft.DropdownOption(key="all", text=tr("filter.all", lang)),
                ft.DropdownOption(
                    key=TransactionType.INCOME.value,
                    text=tr("transaction.income", lang),
                ),
                ft.DropdownOption(
                    key=TransactionType.EXPENSE.value,
                    text=tr("transaction.expense", lang),
                ),
            ],
            dense=True,
            expand=True,
        )
        cat_names: list[str] = []
        if self._state.container.list_categories is not None:
            cats = await self._state.container.list_categories.execute()
            cat_names = [c.name for c in cats]
        category_dd = ft.Dropdown(
            label=tr("field.category", lang),
            value=self._category_value,
            options=[ft.DropdownOption(key="all", text=tr("filter.all", lang))]
            + [ft.DropdownOption(key=c, text=c) for c in cat_names],
            dense=True,
            expand=True,
        )
        group_dd = ft.Dropdown(
            label=tr("filter.group_by", lang),
            value=self._group_by_value,
            options=[
                ft.DropdownOption(
                    key=StatsPeriod.DAY.value, text=tr("filter.group.day", lang)
                ),
                ft.DropdownOption(
                    key=StatsPeriod.WEEK.value, text=tr("filter.group.week", lang)
                ),
                ft.DropdownOption(
                    key=StatsPeriod.MONTH.value, text=tr("filter.group.month", lang)
                ),
            ],
            dense=True,
            expand=True,
        )
        date_from = DateTimeField(
            self._page,
            lang=lang,
            label=tr("filter.date_from", lang),
            value=_parse_date(self._date_from_value),
            allow_clear=True,
        )
        date_to = DateTimeField(
            self._page,
            lang=lang,
            label=tr("filter.date_to", lang),
            value=_parse_date(self._date_to_value),
            allow_clear=True,
        )

        def _apply(_e: ft.ControlEvent) -> None:
            self._type_value = type_dd.value or "all"
            self._category_value = category_dd.value or "all"
            self._group_by_value = group_dd.value or StatsPeriod.DAY.value
            self._date_from_value = date_from.date_text
            self._date_to_value = date_to.date_text
            self._page.pop_dialog()
            self._filter_summary.value = self._filter_summary_text()
            safe_update(self._filter_summary)
            run_async(self._page, self.reload)

        def _reset(_e: ft.ControlEvent) -> None:
            self._type_value = "all"
            self._category_value = "all"
            self._date_from_value = ""
            self._date_to_value = ""
            self._group_by_value = StatsPeriod.DAY.value
            self._page.pop_dialog()
            self._filter_summary.value = self._filter_summary_text()
            safe_update(self._filter_summary)
            run_async(self._page, self.reload)

        self._page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title=ft.Text(tr("action.filters", lang)),
                content=ft.Container(
                    width=360,
                    content=ft.Column(
                        tight=True,
                        spacing=12,
                        scroll=ft.ScrollMode.AUTO,
                        controls=[
                            type_dd,
                            category_dd,
                            group_dd,
                            date_from,
                            date_to,
                        ],
                    ),
                ),
                actions=[
                    ft.TextButton(tr("action.reset", lang), on_click=_reset),
                    ft.TextButton(
                        tr("action.cancel", lang),
                        on_click=lambda _e: self._page.pop_dialog(),
                    ),
                    ft.FilledButton(
                        tr("action.apply", lang),
                        icon=ft.Icons.CHECK,
                        on_click=_apply,
                    ),
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )
        )

    async def reload(self) -> None:
        """Reload filtered transactions."""
        self._token = self._state.transactions_token
        lang = self._state.language
        self._filter_summary.value = self._filter_summary_text()
        self._list.controls = [loading_indicator()]
        safe_update(self._list)
        safe_update(self._filter_summary)

        c = self._state.container
        tx_type = None
        if self._type_value not in (None, "all"):
            tx_type = TransactionType(self._type_value)
        category = None
        if self._category_value not in (None, "all"):
            category = self._category_value

        try:
            date_from = _parse_date(self._date_from_value)
            date_to = _parse_date(self._date_to_value, end_of_day=True)
        except ValueError:
            snack(self._page, tr("invalid_date", lang), error=True)
            return

        try:
            self._accounts = await c.list_accounts.execute(active_only=True)
            self._goals = await c.list_goals.execute(include_completed=False)
            if c.list_categories is not None:
                cats = await c.list_categories.execute(active_only=False)
                self._category_map = {cat.name: cat for cat in cats}
            items = await c.list_transactions.execute(
                category=category,
                transaction_type=tx_type,
                date_from=date_from,
                date_to=date_to,
            )
        except Exception as exc:  # noqa: BLE001
            snack(self._page, str(exc), error=True)
            self._list.controls = [EmptyState(tr("error.generic", lang))]
            safe_update(self._list)
            return

        query = (self._search.value or "").strip().lower()
        if query:
            items = [
                tx
                for tx in items
                if query in tx.category.lower()
                or query in (tx.comment or "").lower()
                or any(query in tag.lower() for tag in tx.tags)
            ]

        if not items:
            self._list.controls = [
                EmptyState(
                    tr("empty.transactions", lang),
                    action_label=tr("action.add", lang),
                    on_action=lambda _e: run_async(
                        self._page, self._open_editor_async
                    ),
                )
            ]
            safe_update(self._list)
            return

        group_mode = self._group_by_value or StatsPeriod.DAY.value
        grouped: dict[str, list[Transaction]] = defaultdict(list)
        for tx in sorted(items, key=lambda t: t.date, reverse=True):
            grouped[_period_key(tx.date, group_mode)].append(tx)

        controls: list[ft.Control] = []
        for period, period_items in grouped.items():
            controls.append(
                ft.Text(
                    period,
                    weight=ft.FontWeight.W_700,
                    size=13,
                    color=ft.Colors.PRIMARY,
                )
            )
            for tx in period_items:
                controls.append(
                    TransactionTile(
                        tx,
                        category=self._category_map.get(tx.category),  # type: ignore[arg-type]
                        language=lang,
                        on_edit=lambda t: run_async(
                            self._page, self._open_editor_async, t
                        ),
                        on_delete=self._confirm_delete,
                    )
                )
        self._list.controls = controls
        safe_update(self._list)

    def _confirm_delete(self, tx: Transaction) -> None:
        lang = self._state.language

        async def _do() -> None:
            await self._state.container.delete_transaction.execute(tx.id)
            self._state.bump_refresh("dashboard", "transactions", "accounts")
            snack(self._page, tr("action.saved", lang))

        confirm_dialog(
            self._page,
            title=tr("action.confirm_delete", lang),
            message=f"{tx.category} · {tx.amount}",
            confirm_text=tr("action.delete", lang),
            cancel_text=tr("action.cancel", lang),
            on_confirm=_do,
        )

    async def _open_editor_async(self, tx: Optional[Transaction] = None) -> None:
        """Always refresh accounts/goals, then open the editor."""
        lang = self._state.language
        try:
            self._accounts = await self._state.container.list_accounts.execute(
                active_only=True
            )
            self._goals = await self._state.container.list_goals.execute(
                include_completed=False
            )
        except Exception as exc:  # noqa: BLE001
            snack(self._page, str(exc), error=True)
            return

        accounts = self._accounts
        if not accounts:
            snack(self._page, tr("empty.accounts", lang), error=True)
            return

        type_dd = ft.Dropdown(
            label=tr("field.type", lang),
            value=(tx.type.value if tx else TransactionType.EXPENSE.value),
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
        )
        amount_tf = ft.TextField(
            label=tr("field.amount", lang),
            value=str(tx.amount) if tx else "",
            keyboard_type=ft.KeyboardType.NUMBER,
        )
        account_dd = ft.Dropdown(
            label=tr("field.account", lang),
            value=tx.account_id if tx else accounts[0].id,
            options=[
                ft.DropdownOption(key=a.id, text=f"{a.name} ({a.currency})")
                for a in accounts
            ],
        )
        category_picker = CategoryPicker(
            self._page,
            self._state,
            tx_type=(tx.type.value if tx else TransactionType.EXPENSE.value),
            initial_name=tx.category if tx else None,
        )
        await category_picker.reload()
        type_dd.on_select = lambda _e: category_picker.set_tx_type(
            type_dd.value or TransactionType.EXPENSE.value
        )
        goal_options = [
            ft.DropdownOption(key="", text=tr("none", lang)),
        ] + [
            ft.DropdownOption(key=g.id, text=g.name) for g in self._goals
        ]
        goal_dd = ft.Dropdown(
            label=tr("field.goal", lang),
            value=tx.goal_id if tx and tx.goal_id else "",
            options=goal_options,
        )
        comment_tf = ft.TextField(
            label=tr("field.comment", lang),
            value=tx.comment if tx else "",
        )
        tags_tf = ft.TextField(
            label=tr("field.tags", lang),
            value=", ".join(tx.tags) if tx else "",
        )
        date_field = DateTimeField(
            self._page,
            lang=lang,
            label=tr("field.date", lang),
            value=tx.date if tx else datetime.now(timezone.utc),
            with_time=True,
        )

        async def _save() -> None:
            try:
                amount = Decimal(str(amount_tf.value or "").replace(",", "."))
                if amount <= 0:
                    raise InvalidOperation
            except (InvalidOperation, ValueError):
                snack(self._page, tr("invalid_amount", lang), error=True)
                return
            occurred = date_field.value
            if occurred is None:
                snack(self._page, tr("invalid_date", lang), error=True)
                return

            account = next(
                (a for a in accounts if a.id == account_dd.value), accounts[0]
            )
            tags = [
                p.strip().lstrip("#")
                for p in (tags_tf.value or "").split(",")
                if p.strip()
            ]
            category = category_picker.selected_name
            if not category:
                snack(self._page, tr("field.category", lang), error=True)
                return
            tx_type = TransactionType(type_dd.value or TransactionType.EXPENSE.value)
            if (
                self._state.container.find_or_create_category is not None
                and not category_picker.has_category(category)
            ):
                await self._state.container.find_or_create_category.execute(
                    category,
                    kind=(
                        CategoryKind.INCOME
                        if tx_type == TransactionType.INCOME
                        else CategoryKind.EXPENSE
                    ),
                )
            goal_id = goal_dd.value or None
            if goal_id == "":
                goal_id = None
            if goal_id and category not in SAVINGS_CATEGORIES:
                category = tr("category.savings", lang)
            entity = Transaction(
                id=tx.id if tx else Transaction(
                    account_id=account.id,
                    amount=Decimal("1"),
                    category="x",
                    date=datetime.now(timezone.utc),
                    type=TransactionType.EXPENSE,
                ).id,
                account_id=account.id,
                amount=amount,
                category=category,
                tags=tags,
                date=occurred,
                comment=comment_tf.value or "",
                type=tx_type,
                currency=account.currency,
                created_at=tx.created_at if tx else datetime.now(timezone.utc),
                goal_id=goal_id,
            )
            try:
                if tx:
                    await self._state.container.update_transaction.execute(entity)
                else:
                    saved = await self._state.container.add_transaction.execute(entity)
                    await self._maybe_notify_goal(saved.goal_id)
            except Exception as exc:  # noqa: BLE001
                snack(self._page, str(exc), error=True)
                return
            close()
            self._state.bump_refresh("dashboard", "transactions", "accounts")
            snack(self._page, tr("action.saved", lang))

        close = open_fullscreen_form(
            self._page,
            title=tr("action.edit", lang) if tx else tr("action.add", lang),
            lang=lang,
            overlay_key="transaction_editor",
            body=[
                type_dd,
                amount_tf,
                account_dd,
                category_picker,
                goal_dd,
                date_field,
                comment_tf,
                tags_tf,
            ],
            on_save=_save,
        )

    async def _maybe_notify_goal(self, goal_id: Optional[str]) -> None:
        if not goal_id or not self._state.settings.goal_milestones:
            return
        goal = await self._state.container.goal_repository.get_by_id(goal_id)
        if goal and goal.is_completed:
            msg = f"{tr('notify.goal_reached', self._state.language)} {goal.name}"
            self._state.push_notification(msg)
            notifier = getattr(self._state.container, "notification_service", None)
            if notifier is not None:
                notifier.push(
                    title=tr("notify.goal_reached", self._state.language),
                    body=goal.name,
                )
