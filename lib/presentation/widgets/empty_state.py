"""Empty-state placeholder for lists."""

from __future__ import annotations

from typing import Optional

import flet as ft


class EmptyState(ft.Container):
    """Centered icon + message (+ optional action) when a list is empty."""

    def __init__(
        self,
        message: str,
        *,
        icon: ft.IconData = ft.Icons.INBOX_OUTLINED,
        action_label: Optional[str] = None,
        on_action: Optional[ft.ControlEventHandler] = None,
    ) -> None:
        controls: list[ft.Control] = [
            ft.Container(
                width=56,
                height=56,
                border_radius=18,
                bgcolor=ft.Colors.PRIMARY_CONTAINER,
                alignment=ft.Alignment.CENTER,
                content=ft.Icon(icon, size=28, color=ft.Colors.ON_PRIMARY_CONTAINER),
            ),
            ft.Text(
                message,
                text_align=ft.TextAlign.CENTER,
                size=14,
                weight=ft.FontWeight.W_600,
                color=ft.Colors.ON_SURFACE,
            ),
        ]
        if action_label and on_action:
            controls.append(
                ft.FilledButton(action_label, icon=ft.Icons.ADD, on_click=on_action)
            )
        super().__init__(
            padding=20,
            alignment=ft.Alignment.CENTER,
            content=ft.Column(
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=10,
                tight=True,
                controls=controls,
            ),
        )
