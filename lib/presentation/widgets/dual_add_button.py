"""Full-width dual action control: expense / income."""

from __future__ import annotations

from typing import Callable, Optional

import flet as ft

from lib.presentation.utils import tr


def dual_add_button(
    lang: str,
    *,
    on_expense: Optional[Callable[[], None]] = None,
    on_income: Optional[Callable[[], None]] = None,
) -> ft.Container:
    """One long button: left = expense, right = income."""

    def _side(
        *,
        label: str,
        icon: ft.IconData,
        bgcolor: str,
        color: str,
        on_click: Optional[Callable[[], None]],
    ) -> ft.Container:
        return ft.Container(
            expand=True,
            bgcolor=bgcolor,
            ink=True,
            on_click=lambda _e: on_click() if on_click else None,
            padding=ft.Padding.symmetric(horizontal=14, vertical=14),
            content=ft.Row(
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=6,
                tight=True,
                controls=[
                    ft.Icon(icon, size=18, color=color),
                    ft.Text(
                        label,
                        size=13,
                        weight=ft.FontWeight.W_700,
                        color=color,
                    ),
                ],
            ),
        )

    return ft.Container(
        height=52,
        border_radius=16,
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
        border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
        shadow=ft.BoxShadow(
            blur_radius=14,
            color="#00000033",
            offset=ft.Offset(0, 4),
        ),
        content=ft.Row(
            spacing=0,
            expand=True,
            controls=[
                _side(
                    label=tr("transaction.expense", lang),
                    icon=ft.Icons.REMOVE_ROUNDED,
                    bgcolor=ft.Colors.ERROR_CONTAINER,
                    color=ft.Colors.ON_ERROR_CONTAINER,
                    on_click=on_expense,
                ),
                _side(
                    label=tr("transaction.income", lang),
                    icon=ft.Icons.ADD_ROUNDED,
                    bgcolor=ft.Colors.PRIMARY_CONTAINER,
                    color=ft.Colors.ON_PRIMARY_CONTAINER,
                    on_click=on_income,
                ),
            ],
        ),
    )
