"""Goal progress bar widget."""

from __future__ import annotations

from typing import Callable, Optional

import flet as ft

from lib.domain.entities.goal import Goal
from lib.presentation.styles import card_surface, muted_text
from lib.presentation.utils import format_date, format_money


class GoalProgress(ft.Container):
    """Shows goal name, amounts, and a progress bar."""

    def __init__(
        self,
        goal: Goal,
        *,
        currency: str = "RUB",
        on_click: Optional[Callable[[Goal], None]] = None,
        on_contribute: Optional[Callable[[Goal], None]] = None,
    ) -> None:
        ratio = float(goal.progress_ratio)
        ratio = max(0.0, min(ratio, 1.0))
        deadline = format_date(goal.deadline) if goal.deadline else "—"
        body = ft.Column(
            spacing=10,
            tight=True,
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Text(goal.name, weight=ft.FontWeight.W_700, size=16),
                        ft.Container(
                            padding=ft.Padding.symmetric(horizontal=10, vertical=4),
                            border_radius=999,
                            bgcolor=ft.Colors.PRIMARY_CONTAINER,
                            content=ft.Text(
                                f"P{goal.priority}",
                                size=11,
                                weight=ft.FontWeight.W_700,
                                color=ft.Colors.ON_PRIMARY_CONTAINER,
                            ),
                        ),
                    ],
                ),
                ft.Text(
                    f"{format_money(goal.current_amount, currency)} / "
                    f"{format_money(goal.target_amount, currency)}",
                    size=13,
                    weight=ft.FontWeight.W_500,
                ),
                ft.ProgressBar(
                    value=ratio,
                    color=ft.Colors.PRIMARY,
                    bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
                    bar_height=10,
                    border_radius=8,
                ),
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        muted_text(f"{ratio * 100:.0f}% · {deadline}"),
                        ft.FilledTonalButton(
                            content="+",
                            icon=ft.Icons.ADD,
                            on_click=lambda _e: on_contribute(goal)
                            if on_contribute
                            else None,
                            visible=on_contribute is not None and not goal.is_completed,
                            style=ft.ButtonStyle(padding=8),
                        ),
                    ],
                ),
            ],
        )
        card = card_surface(
            body,
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
