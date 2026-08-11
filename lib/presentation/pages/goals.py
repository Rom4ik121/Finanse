"""Goals CRUD page with progress."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import TYPE_CHECKING, Optional

import flet as ft

from lib.domain.entities.goal import Goal
from lib.presentation.styles import page_header, summary_strip
from lib.presentation.utils import format_money, run_async, snack, tr
from lib.presentation.widgets.confirm_dialog import confirm_dialog
from lib.presentation.widgets.date_time_field import DateTimeField
from lib.presentation.widgets.empty_state import EmptyState
from lib.presentation.widgets.goal_progress import GoalProgress
from lib.presentation.widgets.loading import loading_indicator

if TYPE_CHECKING:
    from lib.presentation.state.app_state import AppState


class GoalsPage(ft.Column):
    """Manage savings goals."""

    def __init__(self, page: ft.Page, state: "AppState") -> None:
        self._page = page
        self._state = state
        self._list = ft.Column(expand=True, scroll=ft.ScrollMode.AUTO, spacing=12)
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
                            icon=ft.Icons.ADD,
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
        run_async(page, self.reload)

    async def reload(self) -> None:
        """Reload goals list."""
        lang = self._state.language
        self._list.controls = [loading_indicator()]
        self._list.update()
        try:
            goals = await self._state.container.list_goals.execute()
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

        currency = self._state.base_currency
        total_target = sum((g.target_amount for g in goals), Decimal("0"))
        total_saved = sum((g.current_amount for g in goals), Decimal("0"))
        total_remaining = sum(
            (
                max(Decimal("0"), g.target_amount - g.current_amount)
                for g in goals
                if not g.is_completed
            ),
            Decimal("0"),
        )
        self._list.controls = [
            summary_strip(
                [
                    (
                        tr("goals.total_target", lang),
                        format_money(total_target, currency),
                        ft.Colors.PRIMARY,
                    ),
                    (
                        tr("goals.total_saved", lang),
                        format_money(total_saved, currency),
                        ft.Colors.SECONDARY,
                    ),
                    (
                        tr("goals.total_remaining", lang),
                        format_money(total_remaining, currency),
                        ft.Colors.ERROR,
                    ),
                ]
            ),
            *[
                GoalProgress(
                    g,
                    currency=currency,
                    on_click=self._open_editor,
                    on_contribute=self._contribute,
                )
                for g in sorted(goals, key=lambda x: (-x.priority, x.name))
            ],
        ]
        self._list.update()

    def _contribute(self, goal: Goal) -> None:
        lang = self._state.language

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
                if amount > account.balance:
                    snack(self._page, tr("error.insufficient_funds", lang), error=True)
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
                self._page.pop_dialog()
                self._state.bump_refresh("dashboard")
                self._state.bump_refresh("accounts")
                self._state.bump_refresh("transactions")
                await self.reload()
                if updated.is_completed and self._state.settings.goal_milestones:
                    self._state.push_notification(
                        f"{tr('notify.goal_reached', lang)} {updated.name}"
                    )
                else:
                    snack(self._page, tr("action.saved", lang))

            self._page.show_dialog(
                ft.AlertDialog(
                    modal=True,
                    title=ft.Text(f"{tr('goal.contribute', lang)} · {goal.name}"),
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
                            tr("goal.contribute", lang),
                            on_click=lambda e: run_async(self._page, _save, e),
                        ),
                    ],
                )
            )

        run_async(self._page, _open)

    def _open_editor(self, goal: Optional[Goal] = None) -> None:
        lang = self._state.language
        name_tf = ft.TextField(
            label=tr("field.name", lang), value=goal.name if goal else ""
        )
        target_tf = ft.TextField(
            label=tr("goal.target", lang),
            value=str(goal.target_amount) if goal else "",
            keyboard_type=ft.KeyboardType.NUMBER,
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
        editor_controls: list[ft.Control] = [
            name_tf,
            target_tf,
        ]
        if goal:
            editor_controls.append(
                ft.Text(
                    f"{tr('goal.progress', lang)}: "
                    f"{format_money(goal.current_amount, self._state.base_currency)}",
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

        async def _save(_e: ft.ControlEvent) -> None:
            try:
                target = Decimal(str(target_tf.value or "").replace(",", "."))
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
                deadline=deadline,
                priority=int(priority_dd.value or 3),
                category_link=goal.category_link
                if goal
                else tr("category.savings", lang),
                is_completed=goal.is_completed if goal else False,
                created_at=goal.created_at if goal else datetime.now(timezone.utc),
            )
            if goal:
                await self._state.container.update_goal.execute(entity)
            else:
                await self._state.container.create_goal.execute(entity)
            self._page.pop_dialog()
            self._state.bump_refresh("dashboard")
            await self.reload()
            snack(self._page, tr("action.saved", lang))

        def _delete() -> None:
            if not goal:
                return

            async def _do() -> None:
                await self._state.container.delete_goal.execute(goal.id)
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

        actions = [
            ft.TextButton(
                tr("action.cancel", lang),
                on_click=lambda _e: self._page.pop_dialog(),
            ),
            ft.FilledButton(
                tr("action.save", lang),
                on_click=lambda e: run_async(self._page, _save, e),
            ),
        ]
        if goal:
            actions.insert(
                0,
                ft.TextButton(
                    tr("action.delete", lang),
                    on_click=lambda _e: _delete(),
                ),
            )

        self._page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title=ft.Text(
                    tr("action.edit", lang) if goal else tr("action.add", lang)
                ),
                content=ft.Container(
                    width=400,
                    content=ft.Column(
                        tight=True,
                        spacing=10,
                        scroll=ft.ScrollMode.AUTO,
                        height=420,
                        controls=editor_controls,
                    ),
                ),
                actions=actions,
            )
        )
