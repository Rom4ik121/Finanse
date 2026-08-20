"""Goals CRUD page with progress, projection, and contribution history."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import TYPE_CHECKING, Optional

import flet as ft

from lib.domain.entities.goal import Goal, GoalStatus
from lib.presentation.notification_badges import (
    GOAL_ALERT_KINDS,
    mark_related_read,
    pending_related_ids,
)
from lib.presentation.styles import (
    card_surface,
    muted_text,
    page_header,
    section_title,
    summary_strip,
)
from lib.presentation.money_input import attach_grouped_digits, make_amount_field, parse_amount
from lib.presentation.utils import (
    format_date,
    format_money,
    load_rate_book,
    run_async,
    snack,
    tr,
)
from lib.presentation.widgets.confirm_dialog import confirm_dialog
from lib.presentation.widgets.currency_ticker_picker import CurrencyTickerPicker
from lib.presentation.widgets.date_time_field import DateTimeField
from lib.presentation.widgets.empty_state import EmptyState
from lib.presentation.widgets.fullscreen_form import open_fullscreen_form
from lib.presentation.widgets.goal_progress import GoalProgress
from lib.presentation.widgets.loading import loading_indicator

if TYPE_CHECKING:
    from lib.presentation.state.app_state import AppState

_CONTRIB_PAGE = 40
_SORT_KEYS = ("priority", "deadline", "progress", "created_at")
_STATUS_FILTERS = ("active", "completed", "archived")


class GoalsPage(ft.Column):
    """Manage savings goals."""

    def __init__(self, page: ft.Page, state: "AppState") -> None:
        self._page = page
        self._state = state
        self._list = ft.Column(expand=True, scroll=ft.ScrollMode.AUTO, spacing=14)
        self._status_filter = "active"
        self._sort_by = "priority"
        self._group_by_category = False
        self._alert_ids: set[str] = set()
        self._token = -1
        super().__init__(
            expand=True,
            spacing=0,
            controls=[
                page_header(
                    tr("nav.goals", state.language),
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
                            tooltip=tr("action.add", state.language),
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
        if state.goals_token != self._token:
            run_async(self._page, self.reload)

    def _open_filters(self) -> None:
        lang = self._state.language
        status_dd = ft.Dropdown(
            label=tr("goal.filter_status", lang),
            dense=True,
            value=self._status_filter,
            options=[
                ft.DropdownOption(
                    key=key,
                    text=tr(f"goal.status.{key}", lang),
                )
                for key in _STATUS_FILTERS
            ],
        )
        sort_dd = ft.Dropdown(
            label=tr("goal.filter_sort", lang),
            dense=True,
            value=self._sort_by,
            options=[
                ft.DropdownOption(
                    key=key,
                    text=tr(f"goal.sort.{key}", lang),
                )
                for key in _SORT_KEYS
            ],
        )
        group_sw = ft.Switch(
            label=tr("goal.group_by_category", lang),
            value=self._group_by_category,
        )

        async def _apply() -> None:
            self._status_filter = str(status_dd.value or "active")
            self._sort_by = str(sort_dd.value or "priority")
            self._group_by_category = bool(group_sw.value)
            close()
            await self.reload()

        close = open_fullscreen_form(
            self._page,
            title=tr("action.filters", lang),
            lang=lang,
            overlay_key="goal_filters",
            body=[
                status_dd,
                sort_dd,
                ft.Container(height=4),
                group_sw,
            ],
            on_save=_apply,
            save_label=tr("action.apply", lang, default=tr("action.save", lang)),
            save_icon=ft.Icons.CHECK,
        )

    async def reload(self) -> None:
        """Reload goals list."""
        self._token = self._state.goals_token
        lang = self._state.language
        self._list.controls = [loading_indicator()]
        self._list.update()
        self._alert_ids = pending_related_ids(
            self._state.container,
            self._state.settings,
            GOAL_ALERT_KINDS,
        )
        for related_id in list(self._alert_ids):
            mark_related_read(
                self._state.container, related_id, GOAL_ALERT_KINDS
            )
        if self._alert_ids:
            self._state.bump_refresh("dashboard")
        try:
            goals = await self._state.container.list_goals.execute(
                status=self._status_filter,
                sort_by=self._sort_by,
            )
        except Exception as exc:  # noqa: BLE001
            snack(self._page, str(exc), error=True)
            self._list.controls = [EmptyState(tr("error.generic", lang))]
            self._list.update()
            return
        if not goals:
            self._list.controls = [
                EmptyState(
                    tr("empty.goals", lang),
                    action_label=tr("action.add", lang),
                    on_action=lambda _e: self._open_editor(),
                )
            ]
            self._list.update()
            return

        base = self._state.base_currency
        total_target = sum((g.target_amount for g in goals), Decimal("0"))
        total_saved = sum((g.current_amount for g in goals), Decimal("0"))
        total_remaining = sum(
            (g.remaining_amount for g in goals if g.status == GoalStatus.ACTIVE),
            Decimal("0"),
        )
        cards: list[ft.Control] = [
            summary_strip(
                [
                    (
                        tr("goals.total_target", lang),
                        format_money(total_target, base),
                        ft.Colors.PRIMARY,
                    ),
                    (
                        tr("goals.total_saved", lang),
                        format_money(total_saved, base),
                        ft.Colors.SECONDARY,
                    ),
                    (
                        tr("goals.total_remaining", lang),
                        format_money(total_remaining, base),
                        ft.Colors.ERROR,
                    ),
                ]
            ),
            ft.Container(height=2),
        ]
        if self._group_by_category:
            grouped: dict[str, list[Goal]] = defaultdict(list)
            for g in goals:
                key = (g.category_link or "").strip() or tr("goal.uncategorized", lang)
                grouped[key].append(g)
            for category, items in sorted(grouped.items(), key=lambda kv: kv[0].lower()):
                cards.append(section_title(category))
                cards.extend(self._goal_card(g) for g in items)
        else:
            cards.extend(self._goal_card(g) for g in goals)

        self._list.controls = cards
        self._list.update()

    def _goal_card(self, goal: Goal) -> ft.Control:
        return GoalProgress(
            goal,
            currency=goal.currency or self._state.base_currency,
            language=self._state.language,
            alert=goal.id in self._alert_ids,
            on_click=self._open_detail,
            on_contribute=self._contribute
            if goal.status == GoalStatus.ACTIVE
            else None,
        )

    def _contribute(self, goal: Goal) -> None:
        lang = self._state.language

        async def _open() -> None:
            try:
                accounts = await self._state.container.list_accounts.execute(
                    active_only=True
                )
                book = await load_rate_book(self._state.container)
            except Exception as exc:  # noqa: BLE001
                snack(self._page, str(exc), error=True)
                return
            if not accounts:
                snack(self._page, tr("error.no_accounts", lang), error=True)
                return

            amount_tf = make_amount_field(
                lang,
                label=tr("field.amount", lang),
                autofocus=True,
            )
            convert_hint = ft.Text("", size=12, color=ft.Colors.ON_SURFACE_VARIANT)
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

            def _refresh_conversion(_e: ft.ControlEvent | None = None) -> None:
                account = next(
                    (a for a in accounts if a.id == account_dd.value), accounts[0]
                )
                try:
                    amount = parse_amount(amount_tf.value)
                except (InvalidOperation, ValueError):
                    convert_hint.value = ""
                    convert_hint.update()
                    return
                if amount <= 0:
                    convert_hint.value = ""
                    convert_hint.update()
                    return
                converted = book.convert(amount, account.currency, goal.currency)
                if converted is None:
                    convert_hint.value = tr(
                        "goal.no_rate",
                        lang,
                        pair=f"{account.currency}/{goal.currency}",
                    )
                    convert_hint.color = ft.Colors.ERROR
                else:
                    convert_hint.value = tr(
                        "goal.converted_amount",
                        lang,
                        amount=format_money(converted, goal.currency),
                    )
                    convert_hint.color = ft.Colors.ON_SURFACE_VARIANT
                convert_hint.update()

            attach_grouped_digits(
                amount_tf, lang, extra_on_change=_refresh_conversion
            )
            account_dd.on_select = _refresh_conversion

            async def _save() -> None:
                try:
                    amount = parse_amount(amount_tf.value)
                    if amount <= 0:
                        raise InvalidOperation
                except (InvalidOperation, ValueError):
                    snack(self._page, tr("invalid_amount", lang), error=True)
                    return
                account_id = account_dd.value or accounts[0].id
                account = next((a for a in accounts if a.id == account_id), accounts[0])
                if amount > account.balance:
                    snack(self._page, tr("error.insufficient_funds", lang), error=True)
                    return
                converted = book.convert(amount, account.currency, goal.currency)
                if converted is None:
                    snack(
                        self._page,
                        tr(
                            "goal.no_rate",
                            lang,
                            pair=f"{account.currency}/{goal.currency}",
                        ),
                        error=True,
                    )
                    return
                try:
                    updated = await self._state.container.contribute_to_goal.execute(
                        goal.id,
                        amount,
                        account_id=account_id,
                    )
                except Exception as exc:  # noqa: BLE001
                    snack(self._page, str(exc), error=True)
                    return
                close()
                self._state.bump_refresh("dashboard", "accounts", "transactions", "goals")
                await self.reload()
                if (
                    updated.is_completed
                    and self._state.settings.notifications_enabled
                    and self._state.settings.goal_milestones
                ):
                    notifier = getattr(
                        self._state.container, "notification_service", None
                    )
                    if notifier is not None:
                        from lib.infrastructure.services.notification_service import (
                            NotificationKind,
                        )

                        notifier.push(
                            title=tr("notify.goal_reached", lang),
                            body=updated.name,
                            kind=NotificationKind.GOAL_MILESTONE,
                            related_id=updated.id,
                        )
                    else:
                        self._state.push_notification(
                            f"{tr('notify.goal_reached', lang)} {updated.name}"
                        )
                else:
                    snack(self._page, tr("action.saved", lang))

            close = open_fullscreen_form(
                self._page,
                title=f"{tr('goal.contribute', lang)} · {goal.name}",
                lang=lang,
                overlay_key="goal_contribute",
                body=[account_dd, amount_tf, convert_hint],
                on_save=_save,
                save_icon=ft.Icons.SAVINGS_OUTLINED,
            )

        run_async(self._page, _open)

    def _open_detail(self, goal: Goal) -> None:
        lang = self._state.language
        body = ft.Column(spacing=12, scroll=ft.ScrollMode.AUTO, expand=True)
        close_holder: dict[str, object] = {}

        def _close_detail() -> None:
            closer = close_holder.get("close")
            if callable(closer):
                closer()

        async def _load() -> None:
            body.controls = [loading_indicator()]
            try:
                body.update()
            except Exception:  # noqa: BLE001
                pass
            try:
                fresh = await self._state.container.goal_repository.get_by_id(goal.id)
                goal_obj = fresh or goal
                projection = await self._state.container.get_goal_projection.execute(
                    goal_obj.id
                )
                accounts = {
                    a.id: a
                    for a in await self._state.container.list_accounts.execute(
                        active_only=False
                    )
                }
                txs = await self._state.container.list_transactions.execute(
                    goal_id=goal_obj.id,
                    limit=_CONTRIB_PAGE + 1,
                    offset=0,
                )
            except Exception as exc:  # noqa: BLE001
                snack(self._page, str(exc), error=True)
                return

            has_more = len(txs) > _CONTRIB_PAGE
            shown = txs[:_CONTRIB_PAGE]
            offset = {"n": len(shown)}

            proj_rows: list[ft.Control] = [
                ft.Text(tr("goal.projection", lang), weight=ft.FontWeight.W_700),
            ]
            if projection.required_monthly_contribution is not None:
                proj_rows.append(
                    ft.Text(
                        f"{tr('goal.required_monthly', lang)}: "
                        f"{format_money(projection.required_monthly_contribution, goal_obj.currency)}"
                    )
                )
            if projection.projected_completion_date is not None:
                proj_rows.append(
                    ft.Text(
                        f"{tr('goal.projected_date', lang)}: "
                        f"{format_date(projection.projected_completion_date)}"
                    )
                )
            if projection.is_on_track is True:
                proj_rows.append(
                    ft.Text(tr("goal.on_track", lang), color=ft.Colors.PRIMARY)
                )
            elif projection.is_on_track is False:
                proj_rows.append(
                    ft.Text(tr("goal.off_track", lang), color=ft.Colors.ERROR)
                )

            contrib_col = ft.Column(spacing=8, tight=True)
            contrib_col.controls = [
                ft.Text(tr("goal.contributions", lang), weight=ft.FontWeight.W_700),
            ]
            if not shown:
                contrib_col.controls.append(muted_text("—"))
            else:
                for tx in shown:
                    contrib_col.controls.append(
                        self._contribution_row(goal_obj, tx, accounts, close_holder)
                    )

            async def _more(_e: ft.ControlEvent | None = None) -> None:
                more = await self._state.container.list_transactions.execute(
                    goal_id=goal_obj.id,
                    limit=_CONTRIB_PAGE + 1,
                    offset=offset["n"],
                )
                more_has = len(more) > _CONTRIB_PAGE
                chunk = more[:_CONTRIB_PAGE]
                offset["n"] += len(chunk)
                for tx in chunk:
                    contrib_col.controls.append(
                        self._contribution_row(goal_obj, tx, accounts, close_holder)
                    )
                load_more_btn.visible = more_has
                contrib_col.update()
                load_more_btn.update()

            load_more_btn = ft.TextButton(
                tr("action.load_more", lang, default="Load more"),
                visible=has_more,
                on_click=lambda e: run_async(self._page, _more, e),
            )

            async def _do_duplicate(_e: ft.ControlEvent | None = None) -> None:
                await self._duplicate(goal_obj, close_holder)

            async def _do_archive(_e: ft.ControlEvent | None = None) -> None:
                await self._archive(goal_obj, close_holder)

            def _edit(_e: ft.ControlEvent | None = None) -> None:
                _close_detail()
                self._open_editor(goal_obj)

            def _contrib(_e: ft.ControlEvent | None = None) -> None:
                _close_detail()
                self._contribute(goal_obj)

            actions: list[ft.Control] = []
            if goal_obj.status == GoalStatus.ACTIVE:
                actions.append(
                    ft.FilledButton(
                        tr("goal.contribute", lang),
                        icon=ft.Icons.ADD,
                        on_click=_contrib,
                    )
                )
            actions.extend(
                [
                    ft.FilledTonalButton(
                        tr("action.edit", lang),
                        icon=ft.Icons.EDIT_OUTLINED,
                        on_click=_edit,
                    ),
                    ft.OutlinedButton(
                        tr("goal.duplicate", lang),
                        icon=ft.Icons.CONTENT_COPY,
                        on_click=lambda e: run_async(self._page, _do_duplicate, e),
                    ),
                ]
            )
            if goal_obj.status == GoalStatus.COMPLETED:
                actions.append(
                    ft.OutlinedButton(
                        tr("goal.archive", lang),
                        icon=ft.Icons.ARCHIVE_OUTLINED,
                        on_click=lambda e: run_async(self._page, _do_archive, e),
                    )
                )

            body.controls = [
                GoalProgress(
                    goal_obj,
                    currency=goal_obj.currency,
                    language=lang,
                ),
                card_surface(ft.Column(proj_rows, spacing=6, tight=True)),
                ft.Row(wrap=True, spacing=8, controls=actions),
                contrib_col,
                load_more_btn,
            ]
            body.update()

        close = open_fullscreen_form(
            self._page,
            title=goal.name,
            lang=lang,
            overlay_key="goal_detail",
            body=[body],
            on_save=None,
            show_save=False,
        )
        close_holder["close"] = close
        run_async(self._page, _load)

    def _contribution_row(
        self,
        goal: Goal,
        tx: object,
        accounts: dict,
        close_holder: dict,
    ) -> ft.Control:
        lang = self._state.language
        from lib.domain.use_cases.goals import goal_credit_amount

        credit = goal_credit_amount(tx)  # type: ignore[arg-type]
        account = accounts.get(getattr(tx, "account_id", ""))
        account_name = account.name if account is not None else "—"
        comment = (getattr(tx, "comment", "") or "").strip()
        date_txt = format_date(getattr(tx, "date", None))

        def _delete(_e: ft.ControlEvent | None = None) -> None:
            async def _do() -> None:
                try:
                    await self._state.container.delete_goal_contribution.execute(
                        getattr(tx, "id"),
                        goal_id=goal.id,
                    )
                except Exception as exc:  # noqa: BLE001
                    snack(self._page, str(exc), error=True)
                    return
                self._state.bump_refresh(
                    "dashboard", "accounts", "transactions", "goals"
                )
                closer = close_holder.get("close")
                if callable(closer):
                    closer()
                await self.reload()
                refreshed = await self._state.container.goal_repository.get_by_id(
                    goal.id
                )
                if refreshed is not None:
                    self._open_detail(refreshed)
                snack(self._page, tr("action.saved", lang))

            confirm_dialog(
                self._page,
                title=tr("action.confirm_delete", lang),
                message=format_money(credit, goal.currency),
                confirm_text=tr("action.delete", lang),
                cancel_text=tr("action.cancel", lang),
                on_confirm=_do,
            )

        return card_surface(
            ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.START,
                controls=[
                    ft.Column(
                        spacing=2,
                        tight=True,
                        expand=True,
                        controls=[
                            ft.Text(
                                f"{date_txt} · {format_money(credit, goal.currency)}",
                                weight=ft.FontWeight.W_600,
                            ),
                            muted_text(account_name),
                            muted_text(comment) if comment else ft.Container(height=0),
                        ],
                    ),
                    ft.IconButton(
                        icon=ft.Icons.DELETE_OUTLINE,
                        icon_color=ft.Colors.ERROR,
                        on_click=_delete,
                    ),
                ],
            )
        )

    async def _archive(self, goal: Goal, close_holder: dict) -> None:
        try:
            await self._state.container.archive_goal.execute(goal.id)
        except Exception as exc:  # noqa: BLE001
            snack(self._page, str(exc), error=True)
            return
        closer = close_holder.get("close")
        if callable(closer):
            closer()
        self._state.bump_refresh("dashboard")
        await self.reload()
        snack(self._page, tr("action.saved", self._state.language))

    async def _duplicate(self, goal: Goal, close_holder: dict) -> None:
        lang = self._state.language
        try:
            await self._state.container.duplicate_goal.execute(
                goal.id,
                name_suffix=tr("goal.copy_suffix", lang),
            )
        except Exception as exc:  # noqa: BLE001
            snack(self._page, str(exc), error=True)
            return
        closer = close_holder.get("close")
        if callable(closer):
            closer()
        self._state.bump_refresh("dashboard")
        await self.reload()
        snack(self._page, tr("action.saved", lang))

    def _open_editor(self, goal: Optional[Goal] = None) -> None:
        lang = self._state.language
        name_tf = ft.TextField(
            label=tr("field.name", lang), value=goal.name if goal else ""
        )
        target_tf = make_amount_field(
            lang,
            label=tr("goal.target", lang),
            value=goal.target_amount if goal else "",
        )
        priority_dd = ft.Dropdown(
            label=tr("field.priority", lang),
            value=str(goal.priority if goal else 3),
            options=[ft.DropdownOption(key=str(i), text=str(i)) for i in range(1, 6)],
        )
        deadline_field = DateTimeField(
            self._page,
            lang=lang,
            label=tr("field.date", lang),
            value=goal.deadline if goal and goal.deadline else None,
            allow_clear=True,
        )
        currency_picker = CurrencyTickerPicker(
            self._page,
            lang=lang,
            label=tr("goal.currency", lang),
            value=(goal.currency if goal else self._state.base_currency),
            include_crypto=True,
        )
        editor_controls: list[ft.Control] = [
            name_tf,
            target_tf,
            currency_picker,
        ]
        if goal:
            editor_controls.append(
                ft.Text(
                    f"{tr('goal.progress', lang)}: "
                    f"{format_money(goal.current_amount, goal.currency)}",
                    size=13,
                    color=ft.Colors.ON_SURFACE_VARIANT,
                )
            )
            editor_controls.append(
                ft.Text(
                    tr("goal.progress_hint", lang),
                    size=11,
                    color=ft.Colors.ON_SURFACE_VARIANT,
                )
            )
        editor_controls.extend([priority_dd, deadline_field])

        async def _save() -> None:
            try:
                target = parse_amount(target_tf.value)
                if target <= 0:
                    raise InvalidOperation
            except (InvalidOperation, ValueError):
                snack(self._page, tr("invalid_amount", lang), error=True)
                return
            deadline = deadline_field.value
            entity = Goal(
                id=goal.id if goal else Goal(name="tmp", target_amount=1).id,
                name=(name_tf.value or "").strip() or "Goal",
                target_amount=target,
                current_amount=goal.current_amount if goal else Decimal("0"),
                currency=currency_picker.value or self._state.base_currency,
                deadline=deadline,
                priority=int(priority_dd.value or 3),
                category_link=goal.category_link
                if goal
                else tr("category.savings", lang),
                status=goal.status if goal else GoalStatus.ACTIVE,
                is_completed=goal.is_completed if goal else False,
                created_at=goal.created_at if goal else datetime.now(timezone.utc),
            )
            if goal:
                await self._state.container.update_goal.execute(entity)
            else:
                await self._state.container.create_goal.execute(entity)
            close()
            self._state.bump_refresh("dashboard")
            await self.reload()
            snack(self._page, tr("action.saved", lang))

        def _delete(_e: ft.ControlEvent | None = None) -> None:
            if not goal:
                return

            async def _do() -> None:
                await self._state.container.delete_goal.execute(goal.id)
                close()
                self._state.bump_refresh("dashboard")
                await self.reload()

            confirm_dialog(
                self._page,
                title=tr("action.confirm_delete", lang),
                message=goal.name,
                confirm_text=tr("action.delete", lang),
                cancel_text=tr("action.cancel", lang),
                on_confirm=_do,
            )

        if goal:
            editor_controls.append(
                ft.OutlinedButton(
                    tr("action.delete", lang),
                    icon=ft.Icons.DELETE_OUTLINE,
                    style=ft.ButtonStyle(color=ft.Colors.ERROR),
                    on_click=_delete,
                )
            )

        close = open_fullscreen_form(
            self._page,
            title=tr("action.edit", lang) if goal else tr("action.add", lang),
            lang=lang,
            overlay_key="goal_editor",
            body=editor_controls,
            on_save=_save,
        )
