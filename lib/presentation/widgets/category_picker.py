"""Category picker — fullscreen list with icons, plus create/edit form."""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Optional

import flet as ft

from lib.core.config import CATEGORY_COLORS, CATEGORY_ICON_GROUPS, CATEGORY_ICONS
from lib.domain.entities.category import Category, CategoryKind
from lib.domain.entities.transaction import TransactionType
from lib.presentation.styles import page_header
from lib.presentation.utils import category_icon, run_async, snack, tr
from lib.infrastructure.services.localization import localize_category_name
from lib.presentation.widgets.appearance_picker import open_color_picker, open_icon_picker
from lib.presentation.widgets.fullscreen_form import dismiss_fullscreen, open_fullscreen_form

if TYPE_CHECKING:
    from lib.presentation.state.app_state import AppState

_CREATE_KEY = "__create__"
_PICKER_KEY = "category_picker"


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

        self._icon_badge = ft.Container(
            width=34,
            height=34,
            border_radius=11,
            bgcolor=ft.Colors.PRIMARY_CONTAINER,
            alignment=ft.Alignment.CENTER,
            content=ft.Icon(ft.Icons.CATEGORY_OUTLINED, size=18),
        )
        self._caption = ft.Text(
            tr("field.category", state.language),
            size=11,
            color=ft.Colors.ON_SURFACE_VARIANT,
        )
        self._display = ft.Text(
            tr("category.create", state.language),
            size=14,
            weight=ft.FontWeight.W_600,
            overflow=ft.TextOverflow.ELLIPSIS,
            max_lines=1,
            expand=True,
        )
        self._field = ft.Container(
            expand=True,
            border_radius=14,
            bgcolor=ft.Colors.SURFACE,
            border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
            padding=ft.Padding.symmetric(horizontal=12, vertical=10),
            ink=True,
            on_click=lambda _e: self._open_picker(),
            content=ft.Row(
                spacing=10,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    self._icon_badge,
                    ft.Column(
                        spacing=2,
                        tight=True,
                        expand=True,
                        controls=[self._caption, self._display],
                    ),
                    ft.Icon(
                        ft.Icons.EXPAND_MORE,
                        size=20,
                        color=ft.Colors.PRIMARY,
                    ),
                ],
            ),
        )
        self._edit_btn = ft.IconButton(
            icon=ft.Icons.PALETTE_OUTLINED,
            icon_color=ft.Colors.PRIMARY,
            tooltip=tr("category.edit", state.language),
            on_click=lambda _e: self._open_editor(existing_name=self.selected_name),
        )
        self._empty_hint = ft.Text(
            tr("category.empty_hint", state.language),
            size=12,
            color=ft.Colors.ON_SURFACE_VARIANT,
            visible=False,
        )
        super().__init__(
            spacing=4,
            tight=True,
            controls=[
                ft.Row(
                    spacing=4,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[self._field, self._edit_btn],
                ),
                self._empty_hint,
            ],
        )

    @property
    def selected_name(self) -> str:
        return (self._selected_name or "").strip()

    def has_category(self, name: str) -> bool:
        """True when ``name`` is already loaded in this picker (no create needed)."""
        needle = (name or "").strip()
        if not needle:
            return False
        folded = needle.casefold()
        return any(
            c.name == needle or c.name.casefold() == folded for c in self._categories
        )

    @property
    def is_empty(self) -> bool:
        """True when the user has not created any categories for this type yet."""
        return not self._categories

    def set_tx_type(self, tx_type: str) -> None:
        """Refresh options when income/expense changes."""
        self._tx_type = tx_type
        run_async(self._page, self.reload)

    def _selected_category(self) -> Category | None:
        name = self.selected_name
        if not name:
            return None
        return next((c for c in self._categories if c.name == name), None)

    def _sync_display(self) -> None:
        lang = self._state.language
        category = self._selected_category()
        if category is None:
            self._display.value = tr("category.create", lang)
            self._icon_badge.bgcolor = ft.Colors.PRIMARY_CONTAINER
            self._icon_badge.content = ft.Icon(
                ft.Icons.ADD,
                size=18,
                color=ft.Colors.ON_PRIMARY_CONTAINER,
            )
        else:
            self._display.value = localize_category_name(category.name, lang)
            self._icon_badge.bgcolor = category.color or ft.Colors.PRIMARY_CONTAINER
            self._icon_badge.content = ft.Icon(
                category_icon(category.icon),
                size=18,
                color="#FFFFFF",
            )
        try:
            self._display.update()
            self._icon_badge.update()
        except Exception:  # noqa: BLE001
            pass

    async def reload(self) -> None:
        """Load categories for the current transaction type."""
        lang = self._state.language
        uc = self._state.container.list_categories
        if uc is None:
            self._categories = []
        else:
            self._categories = await uc.execute(for_type=self._tx_type)

        if self._selected_name and any(
            c.name == self._selected_name for c in self._categories
        ):
            pass
        elif self._categories:
            self._selected_name = self._categories[0].name
        else:
            self._selected_name = ""

        self._empty_hint.value = tr("category.empty_hint", lang)
        self._empty_hint.visible = not self._categories
        self._sync_display()
        try:
            self._empty_hint.update()
        except Exception:  # noqa: BLE001
            pass

    def prompt_if_empty(self) -> None:
        """Open the create-category form when the catalog is still empty."""
        if not self._categories:
            self._open_editor(existing_name=None)

    def _pick(self, name: str) -> None:
        self._selected_name = name
        self._sync_display()
        if self._on_changed:
            self._on_changed()

    def _open_picker(self) -> None:
        """Fullscreen category list with icons."""
        lang = self._state.language
        dismiss_fullscreen(self._page, key=_PICKER_KEY)

        list_col = ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO, expand=True)

        def _close(_e: ft.ControlEvent | None = None) -> None:
            dismiss_fullscreen(self._page, key=_PICKER_KEY)

        def _select(name: str) -> None:
            _close()
            if name == _CREATE_KEY:
                self._open_editor(existing_name=None)
                return
            self._pick(name)

        def _tile(category: Category) -> ft.Control:
            selected = category.name == self.selected_name
            return ft.Container(
                border_radius=14,
                bgcolor=(
                    ft.Colors.PRIMARY_CONTAINER
                    if selected
                    else ft.Colors.SURFACE_CONTAINER
                ),
                border=ft.Border.all(
                    1,
                    ft.Colors.PRIMARY if selected else ft.Colors.OUTLINE_VARIANT,
                ),
                padding=ft.Padding.symmetric(horizontal=12, vertical=10),
                ink=True,
                on_click=lambda _e, n=category.name: _select(n),
                content=ft.Row(
                    spacing=12,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Container(
                            width=40,
                            height=40,
                            border_radius=12,
                            bgcolor=category.color or ft.Colors.PRIMARY,
                            alignment=ft.Alignment.CENTER,
                            content=ft.Icon(
                                category_icon(category.icon),
                                size=20,
                                color="#FFFFFF",
                            ),
                        ),
                        ft.Text(
                            localize_category_name(category.name, self._state.language),
                            size=15,
                            weight=ft.FontWeight.W_600,
                            expand=True,
                            overflow=ft.TextOverflow.ELLIPSIS,
                            max_lines=1,
                        ),
                        ft.Icon(
                            ft.Icons.CHECK_CIRCLE if selected else ft.Icons.CHEVRON_RIGHT,
                            size=20,
                            color=(
                                ft.Colors.PRIMARY
                                if selected
                                else ft.Colors.ON_SURFACE_VARIANT
                            ),
                        ),
                    ],
                ),
            )

        tiles: list[ft.Control] = [_tile(c) for c in self._categories]
        tiles.append(
            ft.Container(
                border_radius=14,
                bgcolor=ft.Colors.SURFACE_CONTAINER_HIGH,
                border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
                padding=ft.Padding.symmetric(horizontal=12, vertical=12),
                ink=True,
                on_click=lambda _e: _select(_CREATE_KEY),
                content=ft.Row(
                    spacing=12,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Container(
                            width=40,
                            height=40,
                            border_radius=12,
                            bgcolor=ft.Colors.PRIMARY_CONTAINER,
                            alignment=ft.Alignment.CENTER,
                            content=ft.Icon(
                                ft.Icons.ADD,
                                size=20,
                                color=ft.Colors.ON_PRIMARY_CONTAINER,
                            ),
                        ),
                        ft.Text(
                            tr("category.create", lang),
                            size=15,
                            weight=ft.FontWeight.W_700,
                            expand=True,
                        ),
                    ],
                ),
            )
        )
        if not self._categories:
            list_col.controls = [
                ft.Container(
                    padding=16,
                    content=ft.Text(
                        tr("category.empty_hint", lang),
                        color=ft.Colors.ON_SURFACE_VARIANT,
                    ),
                ),
                *tiles,
            ]
        else:
            list_col.controls = tiles

        overlay = ft.Container(
            left=0,
            top=0,
            right=0,
            bottom=0,
            bgcolor=ft.Colors.SURFACE,
            data=_PICKER_KEY,
            content=ft.SafeArea(
                expand=True,
                content=ft.Column(
                    expand=True,
                    spacing=0,
                    controls=[
                        page_header(
                            tr("field.category", lang),
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
                            content=list_col,
                        ),
                    ],
                ),
            ),
        )
        self._page.overlay.append(overlay)
        self._page.update()

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
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGH,
            alignment=ft.Alignment.CENTER,
            border=ft.Border.all(2, selected_color["value"]),
            content=ft.Icon(category_icon(selected_icon["value"]), size=26),
        )
        icon_toggle_label = ft.Text(
            tr("picker.choose_icon", lang),
            size=12,
            color=ft.Colors.PRIMARY,
            weight=ft.FontWeight.W_600,
        )
        color_toggle_label = ft.Text(
            tr("picker.choose_color", lang),
            size=12,
            color=ft.Colors.PRIMARY,
            weight=ft.FontWeight.W_600,
        )
        icon_chevron = ft.Icon(ft.Icons.CHEVRON_RIGHT, size=22)
        color_chevron = ft.Icon(ft.Icons.CHEVRON_RIGHT, size=22)
        color_swatch = ft.Container(
            width=32,
            height=32,
            border_radius=16,
            bgcolor=selected_color["value"],
        )

        def _refresh_previews() -> None:
            icon_preview.content = ft.Icon(
                category_icon(selected_icon["value"]),
                size=26,
            )
            icon_preview.border = ft.Border.all(2, selected_color["value"])
            color_swatch.bgcolor = selected_color["value"]
            try:
                icon_preview.update()
                color_swatch.update()
            except Exception:  # noqa: BLE001
                pass

        def _select_icon(key: str) -> None:
            selected_icon["value"] = key
            _refresh_previews()

        def _select_color(hex_color: str) -> None:
            selected_color["value"] = hex_color
            _refresh_previews()

        def _open_icons(_e: ft.ControlEvent | None = None) -> None:
            open_icon_picker(
                self._page,
                lang=lang,
                groups=CATEGORY_ICON_GROUPS,
                selected=selected_icon["value"],
                on_select=_select_icon,
                render_icon=lambda key: ft.Icon(
                    category_icon(key), size=22, color="#FFFFFF"
                ),
                overlay_key="category_icon_picker",
                accent=selected_color["value"],
            )

        def _open_colors(_e: ft.ControlEvent | None = None) -> None:
            open_color_picker(
                self._page,
                lang=lang,
                colors=CATEGORY_COLORS,
                selected=selected_color["value"],
                on_select=_select_color,
                overlay_key="category_color_picker",
            )

        _refresh_previews()

        icon_toggle = ft.Container(
            border_radius=14,
            bgcolor=ft.Colors.SURFACE_CONTAINER,
            border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
            padding=12,
            ink=True,
            on_click=_open_icons,
            content=ft.Row(
                spacing=12,
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
            border_radius=14,
            bgcolor=ft.Colors.SURFACE_CONTAINER,
            border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
            padding=12,
            ink=True,
            on_click=_open_colors,
            content=ft.Row(
                spacing=12,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    color_swatch,
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
                color_toggle,
            ],
            on_save=_save,
        )
