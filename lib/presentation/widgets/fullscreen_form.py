"""Fullscreen form overlay (covers nav / content like a native screen)."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Sequence
from typing import Any

import flet as ft

from lib.presentation.styles import page_header
from lib.presentation.utils import run_async, tr

CloseFn = Callable[[], None]
SaveFn = Callable[[], Awaitable[None]]


def dismiss_fullscreen(page: ft.Page, *, key: str) -> None:
    """Remove any overlay tagged with ``key``."""
    for item in list(page.overlay):
        if getattr(item, "data", None) == key:
            try:
                page.overlay.remove(item)
            except Exception:  # noqa: BLE001
                pass
    try:
        page.update()
    except Exception:  # noqa: BLE001
        pass


def open_fullscreen_form(
    page: ft.Page,
    *,
    title: str,
    lang: str,
    body: Sequence[ft.Control],
    on_save: SaveFn | None = None,
    overlay_key: str = "fullscreen_form",
    save_icon: ft.IconData = ft.Icons.CHECK,
    save_label: str | None = None,
    show_save: bool = True,
) -> CloseFn:
    """Show a full-screen form with close + optional save in the header.

    Returns a ``close`` callback the caller can invoke after a successful save.
    """
    dismiss_fullscreen(page, key=overlay_key)

    def _close(_e: Any = None) -> None:
        dismiss_fullscreen(page, key=overlay_key)

    async def _save_click(_e: ft.ControlEvent | None = None) -> None:
        if on_save is not None:
            await on_save()

    actions: list[ft.Control] = []
    if show_save and on_save is not None:
        actions.append(
            ft.FilledButton(
                save_label or tr("action.save", lang),
                icon=save_icon,
                on_click=lambda e: run_async(page, _save_click, e),
            )
        )

    overlay = ft.Container(
        left=0,
        top=0,
        right=0,
        bottom=0,
        bgcolor=ft.Colors.SURFACE,
        data=overlay_key,
        content=ft.SafeArea(
            expand=True,
            content=ft.Column(
                expand=True,
                spacing=0,
                controls=[
                    page_header(
                        title,
                        leading=ft.IconButton(
                            icon=ft.Icons.CLOSE,
                            icon_color=ft.Colors.ON_SURFACE,
                            tooltip=tr("action.cancel", lang),
                            on_click=lambda _e: _close(),
                        ),
                        actions=actions,
                    ),
                    ft.Container(
                        expand=True,
                        padding=ft.Padding.symmetric(horizontal=16, vertical=8),
                        content=ft.Column(
                            expand=True,
                            spacing=12,
                            scroll=ft.ScrollMode.AUTO,
                            controls=[*body, ft.Container(height=24)],
                        ),
                    ),
                ],
            ),
        ),
    )
    page.overlay.append(overlay)
    page.update()
    return _close
