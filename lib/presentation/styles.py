"""Reusable modern UI building blocks that adapt to light/dark themes."""

from __future__ import annotations

from typing import Optional, Sequence

import flet as ft

from lib.presentation.theme import DARK_EXPENSE, DARK_INCOME, LIGHT_EXPENSE, LIGHT_INCOME


CARD_RADIUS = 18
CHIP_RADIUS = 14
SECTION_GAP = 14


def card_surface(
    content: ft.Control,
    *,
    padding: int | ft.Padding = 16,
    accent: Optional[str] = None,
    ink: bool = False,
    on_click: Optional[ft.ControlEventHandler] = None,
    expand: Optional[bool] = None,
) -> ft.Container:
    """Elevated card with readable border in both themes."""
    return ft.Container(
        content=content,
        padding=padding,
        border_radius=CARD_RADIUS,
        bgcolor=ft.Colors.SURFACE_CONTAINER,
        border=ft.Border.all(1, accent or ft.Colors.OUTLINE_VARIANT),
        shadow=ft.BoxShadow(
            spread_radius=0,
            blur_radius=18,
            color="#00000022",
            offset=ft.Offset(0, 6),
        ),
        ink=ink,
        on_click=on_click,
        expand=expand,
        animate=ft.Animation(220, ft.AnimationCurve.EASE_OUT),
    )


def hero_card(
    content: ft.Control,
    *,
    padding: int = 20,
    expand: bool = True,
) -> ft.Container:
    """Primary gradient hero surface (balance / lock / KPI)."""
    return ft.Container(
        content=content,
        padding=padding,
        expand=expand,
        border_radius=22,
        gradient=ft.LinearGradient(
            begin=ft.Alignment.TOP_LEFT,
            end=ft.Alignment.BOTTOM_RIGHT,
            colors=[
                ft.Colors.PRIMARY_CONTAINER,
                ft.Colors.SURFACE_CONTAINER_HIGH,
            ],
        ),
        border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
        shadow=ft.BoxShadow(
            spread_radius=0,
            blur_radius=24,
            color="#00000033",
            offset=ft.Offset(0, 8),
        ),
    )


def section_title(text: str) -> ft.Text:
    """Section heading."""
    return ft.Text(
        text,
        size=15,
        weight=ft.FontWeight.W_700,
        color=ft.Colors.ON_SURFACE,
    )


def muted_text(text: str, *, size: int = 12) -> ft.Text:
    """Secondary / meta text with strong readability."""
    return ft.Text(text, size=size, color=ft.Colors.ON_SURFACE_VARIANT)


def summary_strip(
    rows: Sequence[tuple[str, str, Optional[str]]],
) -> ft.Container:
    """Compact summary card: list of (label, value, optional accent color)."""
    controls: list[ft.Control] = []
    for index, (label, value, accent) in enumerate(rows):
        if index:
            controls.append(ft.Container(height=1, bgcolor=ft.Colors.OUTLINE_VARIANT))
        controls.append(
            ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Text(
                        label,
                        size=12,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                        expand=True,
                    ),
                    ft.Text(
                        value,
                        size=14,
                        weight=ft.FontWeight.W_700,
                        color=accent or ft.Colors.ON_SURFACE,
                    ),
                ],
            )
        )
    return card_surface(
        ft.Column(spacing=8, tight=True, controls=controls),
        padding=14,
    )


def page_header(
    title: str,
    *,
    actions: Optional[Sequence[ft.Control]] = None,
    leading: Optional[ft.Control] = None,
) -> ft.Container:
    """Page top bar — sits below SafeArea, clear of notch / status bar."""
    left: list[ft.Control] = []
    if leading is not None:
        left.append(leading)
    left.append(
        ft.Text(
            title,
            size=22,
            weight=ft.FontWeight.W_700,
            color=ft.Colors.ON_SURFACE,
            overflow=ft.TextOverflow.ELLIPSIS,
            max_lines=1,
            expand=True,
        )
    )
    return ft.Container(
        # Horizontal inset + comfortable tap height under Dynamic Island / notch.
        padding=ft.padding.only(left=16, right=10, top=12, bottom=8),
        content=ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Row(
                    controls=left,
                    spacing=4,
                    tight=True,
                    expand=True,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Row(
                    controls=list(actions or []),
                    tight=True,
                    spacing=0,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            ],
        ),
    )


def notice_banner(title: str, body: str) -> ft.Container:
    """Theme-aware reminder / alert strip."""
    return ft.Container(
        padding=14,
        border_radius=14,
        bgcolor=ft.Colors.TERTIARY_CONTAINER,
        border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
        content=ft.Row(
            spacing=10,
            controls=[
                ft.Icon(ft.Icons.NOTIFICATIONS_ACTIVE, color=ft.Colors.ON_TERTIARY_CONTAINER),
                ft.Column(
                    spacing=2,
                    tight=True,
                    expand=True,
                    controls=[
                        ft.Text(
                            title,
                            weight=ft.FontWeight.W_600,
                            color=ft.Colors.ON_TERTIARY_CONTAINER,
                            size=13,
                        ),
                        ft.Text(
                            body,
                            size=12,
                            color=ft.Colors.ON_TERTIARY_CONTAINER,
                        ),
                    ],
                ),
            ],
        ),
    )


def shortcut_chip(
    label: str,
    icon: ft.IconData,
    *,
    on_click: Optional[ft.ControlEventHandler] = None,
    width: int | None = None,
    expand: bool = True,
) -> ft.Container:
    """Quick-nav tile that stretches inside a responsive grid."""
    return ft.Container(
        width=width,
        expand=expand,
        padding=ft.padding.symmetric(horizontal=8, vertical=10),
        border_radius=CHIP_RADIUS,
        bgcolor=ft.Colors.SURFACE_CONTAINER_HIGH,
        border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
        ink=True,
        on_click=on_click,
        content=ft.Column(
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=6,
            tight=True,
            controls=[
                ft.Container(
                    width=34,
                    height=34,
                    border_radius=11,
                    bgcolor=ft.Colors.PRIMARY_CONTAINER,
                    alignment=ft.Alignment.CENTER,
                    content=ft.Icon(icon, color=ft.Colors.ON_PRIMARY_CONTAINER, size=18),
                ),
                ft.Text(
                    label,
                    size=11,
                    weight=ft.FontWeight.W_600,
                    text_align=ft.TextAlign.CENTER,
                    overflow=ft.TextOverflow.ELLIPSIS,
                    max_lines=1,
                ),
            ],
        ),
    )


def amount_color(is_income: bool, *, dark: bool = True) -> str:
    """Income / expense color tuned for theme contrast."""
    if is_income:
        return DARK_INCOME if dark else LIGHT_INCOME
    return DARK_EXPENSE if dark else LIGHT_EXPENSE


def icon_badge(
    icon: ft.IconData,
    *,
    bgcolor: Optional[str] = None,
    color: Optional[str] = None,
    size: int = 40,
) -> ft.Container:
    """Circular / rounded icon badge."""
    return ft.Container(
        width=size,
        height=size,
        border_radius=size // 3,
        bgcolor=bgcolor or ft.Colors.PRIMARY_CONTAINER,
        alignment=ft.Alignment.CENTER,
        content=ft.Icon(
            icon,
            color=color or ft.Colors.ON_PRIMARY_CONTAINER,
            size=int(size * 0.48),
        ),
    )
