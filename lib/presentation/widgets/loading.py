"""Loading indicators."""

from __future__ import annotations

import flet as ft


def loading_indicator(*, message: str = "") -> ft.Control:
    """Compact centered progress ring with optional caption."""
    controls: list[ft.Control] = [ft.ProgressRing()]
    if message:
        controls.append(ft.Text(message, color=ft.Colors.ON_SURFACE_VARIANT))
    return ft.Container(
        expand=True,
        alignment=ft.Alignment.CENTER,
        content=ft.Column(
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=12,
            controls=controls,
        ),
    )


class LoadingOverlay(ft.Container):
    """Semi-transparent overlay used while async work runs."""

    def __init__(self, *, message: str = "") -> None:
        super().__init__(
            expand=True,
            bgcolor=ft.Colors.with_opacity(0.35, ft.Colors.BLACK),
            alignment=ft.Alignment.CENTER,
            visible=False,
            content=ft.Container(
                padding=20,
                border_radius=16,
                bgcolor=ft.Colors.SURFACE,
                content=ft.Column(
                    tight=True,
                    spacing=12,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.ProgressRing(),
                        ft.Text(message),
                    ],
                ),
            ),
        )

    def show(self, message: str | None = None) -> None:
        """Show the overlay, optionally updating the caption."""
        if message is not None and isinstance(self.content, ft.Container):
            col = self.content.content
            if isinstance(col, ft.Column) and len(col.controls) > 1:
                col.controls[1] = ft.Text(message)
        self.visible = True

    def hide(self) -> None:
        """Hide the overlay."""
        self.visible = False
