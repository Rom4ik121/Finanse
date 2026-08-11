"""Category dropdown with create / edit dialog (icon + color)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Optional

import flet as ft

from lib.core.config import CATEGORY_COLORS, CATEGORY_ICON_GROUPS, CATEGORY_ICONS
from lib.domain.entities.category import Category, CategoryKind
from lib.domain.entities.transaction import TransactionType
from lib.presentation.utils import category_icon, run_async, snack, tr
from lib.presentation.widgets.fullscreen_form import open_fullscreen_form

if TYPE_CHECKING:
    from lib.presentation.state.app_state import AppState

_CREATE_KEY = "__create__"


class CategoryPicker(ft.Column):
    """Pick an existing category or create a new one with icon/color."""

    def __init__(
        self,
        page: ft.Page,
        state: "AppState",
        *,
        tx_type: str = TransactionType.EXPENSE.value,
        initial_name: str | None = None,
        on_changed: Optional[Callable[[], None]] = None,
    ) -> None:
        self._page = page
        self._state = state
        self._tx_type = tx_type
        self._on_changed = on_changed
        self._categories: list[Category] = []
        self._selected_name = initial_name or ""

        self._dropdown = ft.Dropdown(
            label=tr("field.category", state.language),
            expand=True,
            dense=True,
            on_select=self._on_select,
        )
        self._edit_btn = ft.IconButton(
            icon=ft.Icons.PALETTE_OUTLINED,
            icon_color=ft.Colors.PRIMARY,
            tooltip=tr("category.edit", state.language),
            on_click=lambda _e: self._open_editor(existing_name=self.selected_name),
        )
        super().__init__(
            spacing=0,
            tight=True,
            controls=[
                ft.Row(
                    spacing=4,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[self._dropdown, self._edit_btn],
                )
            ],
        )

    @property
    def selected_name(self) -> str:
        value = self._dropdown.value or self._selected_name
        if value == _CREATE_KEY:
            return self._selected_name
        return (value or "").strip()

    def has_category(self, name: str) -> bool:
        """True when ``name`` is already loaded in this picker (no create needed)."""
        needle = (name or "").strip()
        if not needle:
            return False
        folded = needle.casefold()
        return any(
            c.name == needle or c.name.casefold() == folded for c in self._categories
        )

    def set_tx_type(self, tx_type: str) -> None:
        """Refresh options when income/expense changes."""
        self._tx_type = tx_type
        run_async(self._page, self.reload)

    async def reload(self) -> None:
        """Load categories for the current transaction type."""
        lang = self._state.language
        uc = self._state.container.list_categories
        if uc is None:
            self._categories = []
        else:
            self._categories = await uc.execute(for_type=self._tx_type)
        options: list[ft.DropdownOption] = [
            ft.DropdownOption(key=c.name, text=c.name) for c in self._categories
        ]
        options.append(
            ft.DropdownOption(
                key=_CREATE_KEY,
                text=tr("category.create", lang),
            )
        )
        self._dropdown.options = options
        if self._selected_name and any(
            c.name == self._selected_name for c in self._categories
        ):
            self._dropdown.value = self._selected_name
        elif self._categories:
            self._dropdown.value = self._categories[0].name
            self._selected_name = self._categories[0].name
        else:
            self._dropdown.value = _CREATE_KEY
        try:
            self._dropdown.update()
        except Exception:  # noqa: BLE001
            pass

    def _on_select(self, _e: ft.ControlEvent) -> None:
        if self._dropdown.value == _CREATE_KEY:
            self._open_editor(existing_name=None)
            return
        self._selected_name = self._dropdown.value or ""
        if self._on_changed:
            self._on_changed()

    def _open_editor(self, *, existing_name: str | None) -> None:
        lang = self._state.language
        existing = next(
            (c for c in self._categories if c.name == existing_name), None
        )
        default_icon = (
            existing.icon
            if existing and existing.icon in CATEGORY_ICONS
            else CATEGORY_ICONS[0]
        )
        default_color = (
            existing.color
            if existing and existing.color in CATEGORY_COLORS
            else CATEGORY_COLORS[0]
        )
        selected_icon = {"value": default_icon}
        selected_color = {"value": default_color}
        icons_open = {"value": False}
        colors_open = {"value": False}

        name_tf = ft.TextField(
            label=tr("field.name", lang),
            value=existing.name if existing else "",
            autofocus=True,
            expand=True,
        )
        kind_dd = ft.Dropdown(
            label=tr("field.type", lang),
            value=(
                existing.kind.value
                if existing
                else (
                    CategoryKind.INCOME.value
                    if self._tx_type == TransactionType.INCOME.value
                    else CategoryKind.EXPENSE.value
                )
            ),
            options=[
                ft.DropdownOption(
                    key=CategoryKind.EXPENSE.value,
                    text=tr("transaction.expense", lang),
                ),
                ft.DropdownOption(
                    key=CategoryKind.INCOME.value,
                    text=tr("transaction.income", lang),
                ),
                ft.DropdownOption(
                    key=CategoryKind.BOTH.value,
                    text=tr("category.both", lang),
                ),
            ],
            expand=True,
            dense=True,
        )

        icon_preview = ft.Container(
            width=48,
            height=48,
            border_radius=14,
            alignment=ft.Alignment.CENTER,
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
            border=ft.Border.all(2, ft.Colors.OUTLINE_VARIANT),
            content=ft.Icon(category_icon(selected_icon["value"]), size=26),
        )
        color_preview = ft.Container(
            width=48,
            height=48,
            border_radius=24,
            bgcolor=selected_color["value"],
            border=ft.Border.all(2, ft.Colors.OUTLINE_VARIANT),
        )
        icon_toggle_label = ft.Text(
            tr("picker.choose_icon", lang),
            size=13,
            weight=ft.FontWeight.W_600,
            expand=True,
        )
        color_toggle_label = ft.Text(
            tr("picker.choose_color", lang),
            size=13,
            weight=ft.FontWeight.W_600,
            expand=True,
        )
        icon_chevron = ft.Icon(ft.Icons.EXPAND_MORE, size=20)
        color_chevron = ft.Icon(ft.Icons.EXPAND_MORE, size=20)

        icon_groups_col = ft.Column(spacing=12, tight=True)
        color_grid = ft.Row(wrap=True, spacing=6, run_spacing=6)

        icon_panel = ft.Container(
            visible=False,
            padding=ft.padding.only(top=8),
            content=ft.Container(
                height=280,
                border_radius=14,
                bgcolor=ft.Colors.SURFACE_CONTAINER_HIGH,
                border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
                padding=10,
                content=ft.Column(
                    scroll=ft.ScrollMode.AUTO,
                    spacing=0,
                    controls=[icon_groups_col],
                ),
            ),
        )
        color_panel = ft.Container(
            visible=False,
            padding=ft.padding.only(top=8),
            content=ft.Container(
                height=160,
                border_radius=14,
                bgcolor=ft.Colors.SURFACE_CONTAINER_HIGH,
                border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
                padding=10,
                content=ft.Column(
                    scroll=ft.ScrollMode.AUTO,
                    spacing=0,
                    controls=[color_grid],
                ),
            ),
        )

        def _refresh_previews() -> None:
            icon_preview.content = ft.Icon(
                category_icon(selected_icon["value"]),
                size=26,
                color=selected_color["value"],
            )
            icon_preview.border = ft.Border.all(2, selected_color["value"])
            color_preview.bgcolor = selected_color["value"]
            icon_chevron.icon = (
                ft.Icons.EXPAND_LESS if icons_open["value"] else ft.Icons.EXPAND_MORE
            )
            color_chevron.icon = (
                ft.Icons.EXPAND_LESS if colors_open["value"] else ft.Icons.EXPAND_MORE
            )
            icon_toggle_label.value = (
                tr("picker.close", lang)
                if icons_open["value"]
                else tr("picker.choose_icon", lang)
            )
            color_toggle_label.value = (
                tr("picker.close", lang)
                if colors_open["value"]
                else tr("picker.choose_color", lang)
            )
            try:
                icon_preview.update()
                color_preview.update()
                icon_chevron.update()
                color_chevron.update()
                icon_toggle_label.update()
                color_toggle_label.update()
            except Exception:  # noqa: BLE001
                pass

        def _icon_tile(key: str) -> ft.Container:
            active = key == selected_icon["value"]
            return ft.Container(
                width=40,
                height=40,
                border_radius=12,
                bgcolor=(
                    ft.Colors.PRIMARY_CONTAINER if active else ft.Colors.SURFACE
                ),
                border=ft.Border.all(
                    2,
                    selected_color["value"] if active else ft.Colors.OUTLINE_VARIANT,
                ),
                alignment=ft.Alignment.CENTER,
                ink=True,
                on_click=lambda _e, k=key: _select_icon(k),
                content=ft.Icon(
                    category_icon(key),
                    size=20,
                    color=selected_color["value"],
                ),
            )

        def _rebuild_grids() -> None:
            icon_groups_col.controls = []
            for group_key, keys in CATEGORY_ICON_GROUPS:
                icon_groups_col.controls.append(
                    ft.Text(
                        tr(group_key, lang),
                        size=12,
                        weight=ft.FontWeight.W_600,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                    )
                )
                icon_groups_col.controls.append(
                    ft.Row(
                        wrap=True,
                        spacing=6,
                        run_spacing=6,
                        controls=[_icon_tile(k) for k in keys],
                    )
                )
            color_grid.controls = []
            for color in CATEGORY_COLORS:
                active = color == selected_color["value"]
                color_grid.controls.append(
                    ft.Container(
                        width=32,
                        height=32,
                        border_radius=16,
                        bgcolor=color,
                        border=ft.Border.all(
                            3,
                            ft.Colors.ON_SURFACE if active else ft.Colors.TRANSPARENT,
                        ),
                        ink=True,
                        on_click=lambda _e, c=color: _select_color(c),
                    )
                )
            try:
                icon_groups_col.update()
                color_grid.update()
            except Exception:  # noqa: BLE001
                pass

        def _set_panel(kind: str, open_: bool) -> None:
            if kind == "icon":
                icons_open["value"] = open_
                if open_:
                    colors_open["value"] = False
            else:
                colors_open["value"] = open_
                if open_:
                    icons_open["value"] = False
            icon_panel.visible = icons_open["value"]
            color_panel.visible = colors_open["value"]
            _refresh_previews()
            try:
                icon_panel.update()
                color_panel.update()
            except Exception:  # noqa: BLE001
                pass

        def _toggle_icons(_e: ft.ControlEvent | None = None) -> None:
            _set_panel("icon", not icons_open["value"])

        def _toggle_colors(_e: ft.ControlEvent | None = None) -> None:
            _set_panel("color", not colors_open["value"])

        def _select_icon(key: str) -> None:
            selected_icon["value"] = key
            _rebuild_grids()
            _set_panel("icon", False)

        def _select_color(color: str) -> None:
            selected_color["value"] = color
            _rebuild_grids()
            _set_panel("color", False)

        _rebuild_grids()
        _refresh_previews()

        icon_toggle = ft.Container(
            padding=ft.padding.symmetric(horizontal=10, vertical=8),
            border_radius=14,
            bgcolor=ft.Colors.SURFACE_CONTAINER,
            border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
            ink=True,
            on_click=_toggle_icons,
            content=ft.Row(
                spacing=10,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    icon_preview,
                    ft.Column(
                        spacing=2,
                        tight=True,
                        expand=True,
                        controls=[
                            ft.Text(
                                tr("field.icon", lang),
                                size=11,
                                color=ft.Colors.ON_SURFACE_VARIANT,
                            ),
                            icon_toggle_label,
                        ],
                    ),
                    icon_chevron,
                ],
            ),
        )
        color_toggle = ft.Container(
            padding=ft.padding.symmetric(horizontal=10, vertical=8),
            border_radius=14,
            bgcolor=ft.Colors.SURFACE_CONTAINER,
            border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
            ink=True,
            on_click=_toggle_colors,
            content=ft.Row(
                spacing=10,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    color_preview,
                    ft.Column(
                        spacing=2,
                        tight=True,
                        expand=True,
                        controls=[
                            ft.Text(
                                tr("field.color", lang),
                                size=11,
                                color=ft.Colors.ON_SURFACE_VARIANT,
                            ),
                            color_toggle_label,
                        ],
                    ),
                    color_chevron,
                ],
            ),
        )

        async def _save() -> None:
            name = (name_tf.value or "").strip()
            if not name:
                snack(self._page, tr("field.name", lang), error=True)
                return
            kind = CategoryKind(kind_dd.value or CategoryKind.BOTH.value)
            try:
                if existing is None:
                    created = await self._state.container.create_category.execute(
                        Category(
                            name=name,
                            icon=selected_icon["value"],
                            color=selected_color["value"],
                            kind=kind,
                        )
                    )
                    self._selected_name = created.name
                else:
                    updated = await self._state.container.update_category.execute(
                        existing.model_copy(
                            update={
                                "name": name,
                                "icon": selected_icon["value"],
                                "color": selected_color["value"],
                                "kind": kind,
                            }
                        )
                    )
                    self._selected_name = updated.name
            except Exception as exc:  # noqa: BLE001
                snack(self._page, str(exc), error=True)
                return
            close()
            await self.reload()
            self._dropdown.value = self._selected_name
            try:
                self._dropdown.update()
            except Exception:  # noqa: BLE001
                pass
            if self._on_changed:
                self._on_changed()
            snack(self._page, tr("action.saved", lang))

        close = open_fullscreen_form(
            self._page,
            title=(
                tr("category.edit", lang)
                if existing
                else tr("category.create", lang)
            ),
            lang=lang,
            overlay_key="category_editor",
            body=[
                name_tf,
                kind_dd,
                icon_toggle,
                icon_panel,
                color_toggle,
                color_panel,
            ],
            on_save=_save,
        )
