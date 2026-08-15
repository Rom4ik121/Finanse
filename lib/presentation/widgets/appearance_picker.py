"""Fullscreen icon and color pickers (covers the current form)."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Optional

import flet as ft

from lib.presentation.styles import (
    ICON_CATALOG_BADGE,
    ICON_CATALOG_BADGE_SELECTED,
    page_header,
)
from lib.presentation.utils import tr
from lib.presentation.widgets.fullscreen_form import dismiss_fullscreen

IconRenderer = Callable[[str], ft.Control]
SelectStr = Callable[[str], None]


def _safe_update(page: ft.Page) -> None:
    try:
        page.update()
    except Exception:  # noqa: BLE001
        pass


def build_icon_catalog(
    *,
    lang: str,
    groups: Sequence[tuple[str, Sequence[str]]],
    selected: dict[str, str],
    render_icon: IconRenderer,
    on_change: Optional[SelectStr] = None,
    accent: Optional[str] = None,
) -> list[ft.Control]:
    """Grouped circular sage badges with white glyphs.

    ``selected`` is a mutable ``{"value": key}`` dict shared with the caller.
    """
    accent_color = accent or ft.Colors.WHITE
    tiles_by_key: dict[str, list[ft.Container]] = {}

    def _style_tile(key: str, tile: ft.Container) -> None:
        active = key == selected["value"]
        tile.bgcolor = ICON_CATALOG_BADGE_SELECTED if active else ICON_CATALOG_BADGE
        tile.border = ft.Border.all(
            3 if active else 0,
            accent_color if active else ft.Colors.TRANSPARENT,
        )
        tile.shadow = (
            ft.BoxShadow(
                blur_radius=10,
                color="#00000033",
                offset=ft.Offset(0, 2),
            )
            if active
            else None
        )

    def _highlight(key: str) -> None:
        previous = selected["value"]
        selected["value"] = key
        to_refresh: list[ft.Container] = []
        for old in tiles_by_key.get(previous, ()):
            _style_tile(previous, old)
            to_refresh.append(old)
        for new in tiles_by_key.get(key, ()):
            _style_tile(key, new)
            to_refresh.append(new)
        try:
            for tile in to_refresh:
                tile.update()
        except Exception:  # noqa: BLE001
            pass
        if on_change is not None:
            on_change(key)

    controls: list[ft.Control] = []
    cols = 5
    cell = 66
    for group_key, keys in groups:
        if not keys:
            continue
        controls.append(
            ft.Text(
                tr(group_key, lang),
                size=16,
                weight=ft.FontWeight.W_700,
                color=ft.Colors.ON_SURFACE,
            )
        )
        tiles: list[ft.Control] = []
        for key in keys:
            tile = ft.Container(
                width=56,
                height=56,
                border_radius=999,
                alignment=ft.Alignment.CENTER,
                ink=True,
                on_click=lambda _e, k=key: _highlight(k),
                content=render_icon(key),
            )
            _style_tile(key, tile)
            tiles_by_key.setdefault(key, []).append(tile)
            tiles.append(tile)
        rows = (len(tiles) + cols - 1) // cols
        controls.append(
            ft.GridView(
                runs_count=cols,
                max_extent=56,
                child_aspect_ratio=1,
                spacing=10,
                run_spacing=10,
                padding=0,
                height=rows * cell,
                controls=tiles,
            )
        )
        controls.append(ft.Container(height=16))
    return controls


def open_icon_picker(
    page: ft.Page,
    *,
    lang: str,
    groups: Sequence[tuple[str, Sequence[str]]],
    selected: str,
    on_select: SelectStr,
    render_icon: IconRenderer,
    overlay_key: str = "icon_picker",
    accent: Optional[str] = None,
) -> None:
    """Open a full-screen grouped icon catalog.

    Tapping an icon highlights it; ``Select`` applies and closes.
    """
    dismiss_fullscreen(page, key=overlay_key)
    current = {"value": selected}

    def _close(_e: object = None) -> None:
        dismiss_fullscreen(page, key=overlay_key)

    def _confirm(_e: object = None) -> None:
        if current["value"]:
            on_select(current["value"])
        _close()

    group_controls = build_icon_catalog(
        lang=lang,
        groups=groups,
        selected=current,
        render_icon=render_icon,
        accent=accent,
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
                        tr("picker.icon_catalog", lang),
                        leading=ft.IconButton(
                            icon=ft.Icons.ARROW_BACK,
                            icon_color=ft.Colors.ON_SURFACE,
                            tooltip=tr("action.cancel", lang),
                            on_click=_close,
                        ),
                    ),
                    ft.Container(
                        expand=True,
                        padding=ft.Padding.symmetric(horizontal=16, vertical=8),
                        content=ft.ListView(
                            expand=True,
                            spacing=4,
                            controls=[*group_controls, ft.Container(height=8)],
                        ),
                    ),
                    ft.Container(
                        padding=ft.Padding.only(left=16, right=16, bottom=12, top=4),
                        content=ft.FilledButton(
                            tr("action.select", lang),
                            expand=True,
                            height=48,
                            on_click=_confirm,
                        ),
                    ),
                ],
            ),
        ),
    )
    page.overlay.append(overlay)
    _safe_update(page)


def open_color_picker(
    page: ft.Page,
    *,
    lang: str,
    colors: Sequence[str],
    selected: str,
    on_select: SelectStr,
    overlay_key: str = "color_picker",
) -> None:
    """Open a full-screen color palette with confirm.

    Tapping a swatch highlights it; ``Select`` applies and closes.
    """
    dismiss_fullscreen(page, key=overlay_key)
    palette = list(colors)
    if selected and selected not in palette:
        palette.insert(0, selected)
    current = {"value": selected or (palette[0] if palette else "#00897B")}
    tiles_by_color: dict[str, ft.Container] = {}

    def _close(_e: object = None) -> None:
        dismiss_fullscreen(page, key=overlay_key)

    def _apply_border(color: str, tile: ft.Container) -> None:
        active = color == current["value"]
        tile.border = ft.Border.all(
            3 if active else 1,
            ft.Colors.ON_SURFACE if active else ft.Colors.OUTLINE_VARIANT,
        )

    def _highlight(color: str) -> None:
        previous = current["value"]
        current["value"] = color
        old = tiles_by_color.get(previous)
        new = tiles_by_color.get(color)
        if old is not None:
            _apply_border(previous, old)
        if new is not None:
            _apply_border(color, new)
        try:
            if old is not None:
                old.update()
            if new is not None:
                new.update()
        except Exception:  # noqa: BLE001
            pass

    def _confirm(_e: object = None) -> None:
        on_select(current["value"])
        _close()

    tiles: list[ft.Control] = []
    for color in palette:
        tile = ft.Container(
            border_radius=999,
            bgcolor=color,
            ink=True,
            on_click=lambda _e, c=color: _highlight(c),
        )
        _apply_border(color, tile)
        tiles_by_color[color] = tile
        tiles.append(tile)

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
                        tr("picker.color_title", lang),
                        leading=ft.IconButton(
                            icon=ft.Icons.ARROW_BACK,
                            icon_color=ft.Colors.ON_SURFACE,
                            tooltip=tr("action.cancel", lang),
                            on_click=_close,
                        ),
                    ),
                    ft.Container(
                        expand=True,
                        padding=ft.Padding.symmetric(horizontal=12, vertical=8),
                        content=ft.GridView(
                            expand=True,
                            runs_count=6,
                            max_extent=56,
                            child_aspect_ratio=1,
                            spacing=8,
                            run_spacing=8,
                            controls=tiles,
                        ),
                    ),
                    ft.Container(
                        padding=ft.Padding.only(left=16, right=16, bottom=12, top=4),
                        content=ft.FilledButton(
                            tr("action.select", lang),
                            expand=True,
                            height=48,
                            on_click=_confirm,
                        ),
                    ),
                ],
            ),
        ),
    )
    page.overlay.append(overlay)
    _safe_update(page)
