"""Goal progress bar widget."""

from __future__ import annotations

from typing import Callable, Optional

import flet as ft

from lib.domain.entities.goal import Goal, GoalStatus
from lib.presentation.styles import card_surface, muted_text
from lib.presentation.utils import format_date, format_money, tr


class GoalProgress(ft.Container):
    """Shows goal name, amounts, and a progress bar."""

    def __init__(
        self,
        goal: Goal,
        *,
        currency: str = "RUB",
        language: str = "ru",
        alert: bool = False,
        on_click: Optional[Callable[[Goal], None]] = None,
        on_contribute: Optional[Callable[[Goal], None]] = None,
    ) -> None:
        ratio = float(goal.progress_ratio)
        ratio = max(0.0, min(ratio, 1.0))
        pct = int(round(ratio * 100))
        deadline = (
            tr("goal.deadline_by", language, date=format_date(goal.deadline))
            if goal.deadline
            else tr("goal.no_deadline", language)
        )
        status = (
            goal.status
            if isinstance(goal.status, GoalStatus)
            else GoalStatus(goal.status)
        )
        badge_key = f"goal.badge.{status.value}"
        status_label = tr(badge_key, language, default=status.value)
        status_bg = {
            GoalStatus.ACTIVE: ft.Colors.PRIMARY_CONTAINER,
            GoalStatus.COMPLETED: ft.Colors.SECONDARY_CONTAINER,
            GoalStatus.ARCHIVED: ft.Colors.SURFACE_CONTAINER_HIGHEST,
        }.get(status, ft.Colors.PRIMARY_CONTAINER)
        status_fg = {
            GoalStatus.ACTIVE: ft.Colors.ON_PRIMARY_CONTAINER,
            GoalStatus.COMPLETED: ft.Colors.ON_SECONDARY_CONTAINER,
            GoalStatus.ARCHIVED: ft.Colors.ON_SURFACE_VARIANT,
        }.get(status, ft.Colors.ON_PRIMARY_CONTAINER)

        def _chip(text: str, *, bgcolor: str, color: str) -> ft.Container:
            return ft.Container(
                padding=ft.Padding.symmetric(horizontal=10, vertical=4),
                border_radius=999,
                bgcolor=bgcolor,
                content=ft.Text(
                    text,
                    size=11,
                    weight=ft.FontWeight.W_700,
                    color=color,
                ),
            )

        can_contribute = on_contribute is not None and status == GoalStatus.ACTIVE
        if alert:
            action_btn: ft.Control = ft.IconButton(
                icon=ft.Icons.PRIORITY_HIGH,
                icon_color=ft.Colors.ON_ERROR,
                bgcolor=ft.Colors.ERROR,
                tooltip=tr("notify.goal_off_track_title", language),
                on_click=lambda _e: on_contribute(goal) if can_contribute else None,
                style=ft.ButtonStyle(
                    shape=ft.CircleBorder(),
                    padding=10,
                ),
            )
        elif can_contribute:
            action_btn = ft.IconButton(
                icon=ft.Icons.ADD,
                icon_color=ft.Colors.ON_PRIMARY,
                bgcolor=ft.Colors.PRIMARY,
                tooltip=tr("goal.contribute", language),
                on_click=lambda _e: on_contribute(goal) if on_contribute else None,
                style=ft.ButtonStyle(
                    shape=ft.CircleBorder(),
                    padding=10,
                ),
            )
        else:
            action_btn = ft.Container(width=0, height=0)

        body = ft.Column(
            spacing=12,
            tight=True,
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                    controls=[
                        ft.Column(
                            spacing=6,
                            tight=True,
                            expand=True,
                            controls=[
                                ft.Text(
                                    goal.name,
                                    weight=ft.FontWeight.W_700,
                                    size=17,
                                    max_lines=2,
                                    overflow=ft.TextOverflow.ELLIPSIS,
                                ),
                                ft.Row(
                                    spacing=6,
                                    wrap=True,
                                    controls=[
                                        _chip(
                                            status_label,
                                            bgcolor=status_bg,
                                            color=status_fg,
                                        ),
                                        _chip(
                                            f"P{goal.priority}",
                                            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
                                            color=ft.Colors.ON_SURFACE,
                                        ),
                                    ],
                                ),
                            ],
                        ),
                        action_btn,
                    ],
                ),
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.END,
                    controls=[
                        ft.Text(
                            f"{format_money(goal.current_amount, currency)} / "
                            f"{format_money(goal.target_amount, currency)}",
                            size=13,
                            weight=ft.FontWeight.W_600,
                            expand=True,
                        ),
                        ft.Text(
                            f"{pct}%",
                            size=18,
                            weight=ft.FontWeight.W_800,
                            color=ft.Colors.PRIMARY,
                        ),
                    ],
                ),
                ft.ProgressBar(
                    value=ratio,
                    color=ft.Colors.PRIMARY,
                    bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
                    bar_height=8,
                    border_radius=999,
                ),
                muted_text(deadline),
            ],
        )
        card = card_surface(
            body,
            padding=16,
            ink=on_click is not None,
            on_click=lambda _e: on_click(goal) if on_click else None,
        )
        super().__init__(
            padding=card.padding,
            border_radius=card.border_radius,
            bgcolor=card.bgcolor,
            border=card.border,
            shadow=card.shadow,
            ink=on_click is not None,
            on_click=card.on_click,
            animate=card.animate,
            content=body,
        )
