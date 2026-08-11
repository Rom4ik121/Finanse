"""Balance / income / expense summary cards."""

from __future__ import annotations

from typing import Optional

import flet as ft


class SummaryCard(ft.Container):
    """Compact KPI card that stretches to available width.

    Non-hero cards use a fixed height so pairs in a Row stay equal.
    """

    KPI_HEIGHT = 96

    def __init__(
        self,
        *,
        title: str,
        value: str,
        icon: ft.IconData = ft.Icons.ACCOUNT_BALANCE_WALLET,
        accent: Optional[str] = None,
        expand: bool = True,
        hero: bool = False,
        width: Optional[int] = None,
        on_click: Optional[ft.ControlEventHandler] = None,
    ) -> None:
        color = accent or ft.Colors.PRIMARY
        body = ft.Column(
            spacing=8,
            tight=False,
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            expand=True,
            controls=[
                ft.Row(
                    spacing=8,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                    controls=[
                        ft.Container(
                            width=30,
                            height=30,
                            border_radius=9,
                            bgcolor=ft.Colors.PRIMARY_CONTAINER,
                            alignment=ft.Alignment.CENTER,
                            content=ft.Icon(
                                icon,
                                size=16,
                                color=ft.Colors.ON_PRIMARY_CONTAINER,
                            ),
                        ),
                        ft.Text(
                            title,
                            size=11,
                            color=ft.Colors.ON_SURFACE_VARIANT,
                            weight=ft.FontWeight.W_500,
                            overflow=ft.TextOverflow.ELLIPSIS,
                            max_lines=2,
                            expand=True,
                        ),
                    ],
                ),
                ft.Text(
                    value,
                    size=16 if hero else 13,
                    weight=ft.FontWeight.W_700,
                    color=color,
                    overflow=ft.TextOverflow.ELLIPSIS,
                    max_lines=1 if not hero else 2,
                ),
            ],
        )
        kwargs: dict = {
            "expand": expand,
            "width": width,
            "height": None if hero else self.KPI_HEIGHT,
            "padding": 14 if hero else 12,
            "border_radius": 16 if hero else 14,
            "border": ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
            "shadow": ft.BoxShadow(
                spread_radius=0,
                blur_radius=12,
                color="#00000022",
                offset=ft.Offset(0, 3),
            ),
            "ink": on_click is not None,
            "on_click": on_click,
            "content": body,
        }
        if hero:
            kwargs["gradient"] = ft.LinearGradient(
                begin=ft.Alignment.TOP_LEFT,
                end=ft.Alignment.BOTTOM_RIGHT,
                colors=[
                    ft.Colors.PRIMARY_CONTAINER,
                    ft.Colors.SURFACE_CONTAINER_HIGH,
                ],
            )
        else:
            kwargs["bgcolor"] = ft.Colors.SURFACE_CONTAINER
        super().__init__(**kwargs)
