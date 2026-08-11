"""Refresh helpers — avoid GestureDetector wrappers that break layout."""

from __future__ import annotations

from typing import Awaitable, Callable

import flet as ft

from lib.presentation.utils import run_async


def wrap_pull_to_refresh(
    page: ft.Page,
    content: ft.Control,
    on_refresh: Callable[[], Awaitable[None]],
    *,
    expand: bool = True,
) -> ft.Control:
    """Return ``content`` unchanged (refresh is via header IconButton).

    Earlier GestureDetector wrappers painted an opaque grey hit-area and
    collapsed nested scroll views. Keep the API for callers, but do not wrap.
    """
    _ = page, on_refresh
    if expand and hasattr(content, "expand"):
        try:
            content.expand = True
        except Exception:  # noqa: BLE001
            pass
    return content


def refresh_header(
    page: ft.Page,
    on_refresh: Callable[[], Awaitable[None]],
    *,
    tooltip: str = "Refresh",
) -> ft.IconButton:
    """Compact refresh icon button for page headers."""
    return ft.IconButton(
        icon=ft.Icons.REFRESH,
        tooltip=tooltip,
        on_click=lambda _e: run_async(page, on_refresh),
    )
