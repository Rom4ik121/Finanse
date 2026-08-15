"""Branded launch screen shown while FinWise initializes."""

from __future__ import annotations

from pathlib import Path

import flet as ft

from lib.presentation.utils import tr

_SPLASH_BG = "#000000"
_SPLASH_BG_TOP = "#0A0A0A"
_ACCENT = "#FFFFFF"
_TAGLINE_KEY = "app.tagline"


def _icon_asset_path() -> str | None:
    """Return a path/URL usable by ``ft.Image`` in desktop and packaged mobile builds."""
    rel = Path("assets") / "icon.png"
    if rel.is_file():
        return str(rel.resolve())
    bundled = Path(__file__).resolve().parents[2] / "assets" / "icon.png"
    if bundled.is_file():
        return str(bundled)
    return None


def build_launch_splash(*, language: str = "ru") -> ft.Control:
    """Full-screen splash with icon, app name, and loading indicator."""
    icon_path = _icon_asset_path()
    icon_control: ft.Control
    if icon_path:
        icon_control = ft.Image(
            src=icon_path,
            width=132,
            height=132,
            fit=ft.BoxFit.CONTAIN,
        )
    else:
        icon_control = ft.Icon(ft.Icons.ACCOUNT_BALANCE_WALLET, size=96, color=_ACCENT)

    return ft.Container(
        expand=True,
        gradient=ft.LinearGradient(
            begin=ft.Alignment(0, -1),
            end=ft.Alignment(0, 1),
            colors=[_SPLASH_BG_TOP, _SPLASH_BG],
        ),
        alignment=ft.Alignment.CENTER,
        content=ft.Column(
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=20,
            controls=[
                icon_control,
                ft.Text(
                    tr("app.name", language),
                    size=34,
                    weight=ft.FontWeight.W_700,
                    color=ft.Colors.WHITE,
                ),
                ft.Container(
                    width=72,
                    height=4,
                    border_radius=2,
                    bgcolor=_ACCENT,
                ),
                ft.Text(
                    tr(_TAGLINE_KEY, language),
                    size=15,
                    color="#A0A0A0",
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.Container(height=28),
                ft.ProgressRing(width=34, height=34, color=_ACCENT, stroke_width=3),
            ],
        ),
    )
