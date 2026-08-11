"""Responsive layout helpers for compact mobile-first UI."""

from __future__ import annotations

from typing import Sequence

import flet as ft


def h_scroll(
    controls: Sequence[ft.Control],
    *,
    spacing: int = 10,
    height: int | None = None,
    padding: int | ft.Padding | None = None,
) -> ft.Container:
    """Horizontal scroll strip — use when items don't fit the viewport width."""
    return ft.Container(
        height=height,
        padding=padding,
        content=ft.Row(
            controls=list(controls),
            spacing=spacing,
            scroll=ft.ScrollMode.AUTO,
            vertical_alignment=ft.CrossAxisAlignment.START,
        ),
    )


def v_scroll_body(
    *controls: ft.Control,
    spacing: int = 12,
    padding: int | ft.Padding | None = 16,
) -> ft.Container:
    """Expanding vertical scroll area for page body content."""
    return ft.Container(
        expand=True,
        padding=padding,
        content=ft.Column(
            expand=True,
            spacing=spacing,
            scroll=ft.ScrollMode.AUTO,
            controls=list(controls),
        ),
    )


def compact_button_row(*buttons: ft.Control) -> ft.Control:
    """Action buttons in a horizontal scroll so they never crush each other."""
    return h_scroll(buttons, spacing=8, height=48)
