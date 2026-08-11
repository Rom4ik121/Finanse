"""Accounts CRUD page with multi-currency display and icon/color pickers."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import TYPE_CHECKING, Optional

import flet as ft

from lib.core.config import ACCOUNT_COLORS, ACCOUNT_ICONS
from lib.domain.entities.account import Account
from lib.domain.entities.currency_codes import normalize_currency_code
from lib.presentation.account_icons import (
    account_icon_control,
    account_icon_groups,
    is_valid_account_icon,
)
from lib.presentation.currency_options import currency_dropdown_options
from lib.presentation.styles import page_header
from lib.presentation.utils import (
    run_async,
    safe_convert,
    safe_update,
    snack,
    tr,
)
from lib.presentation.widgets.account_card import AccountCard
from lib.presentation.widgets.confirm_dialog import confirm_dialog
from lib.presentation.widgets.empty_state import EmptyState
from lib.presentation.widgets.loading import loading_indicator
if TYPE_CHECKING:
    from lib.presentation.state.app_state import AppState


class AccountsPage(ft.Column):
    """List and manage accounts."""

    def __init__(self, page: ft.Page, state: "AppState") -> None:
        self._page = page
        self._state = state
        self._token = -1
        self._list = ft.Column(expand=True, scroll=ft.ScrollMode.AUTO, spacing=12)
        super().__init__(
            expand=True,
            controls=[
                page_header(
                    tr("nav.accounts", state.language),
                    actions=[
                        ft.IconButton(
                            icon=ft.Icons.REFRESH,
                            icon_color=ft.Colors.PRIMARY,
                            tooltip=tr("action.refresh", state.language),
                            on_click=lambda _e: run_async(page, self.reload),
                        ),
                        ft.IconButton(
                            icon=ft.Icons.ADD,
                            icon_color=ft.Colors.PRIMARY,
                            on_click=lambda _e: self._open_editor(),
                        ),
                    ],
                ),
                ft.Container(
                    expand=True,
                    padding=ft.padding.symmetric(horizontal=12),
                    content=self._list,
                ),
            ],
        )
        state.subscribe(self._on_state)
        run_async(page, self.reload)

    def _on_state(self, state: "AppState") -> None:
        if state.accounts_token != self._token:
            run_async(self._page, self.reload)

    async def reload(self) -> None:
        """Reload accounts and convert balances to base currency."""
        self._token = self._state.accounts_token
        lang = self._state.language
        self._list.controls = [loading_indicator()]
        safe_update(self._list)

        try:
            accounts = await self._state.container.list_accounts.execute()
        except Exception as exc:  # noqa: BLE001
            snack(self._page, str(exc), error=True)
            self._list.controls = [EmptyState(tr("error.generic", lang))]
            safe_update(self._list)
            return

        if not accounts:
            self._list.controls = [
                EmptyState(
                    tr("empty.accounts", lang),
                    action_label=tr("action.add", lang),
                    on_action=lambda _e: self._open_editor(),
                )
            ]
            safe_update(self._list)
            return

        base = self._state.base_currency
        cards: list[ft.Control] = []
        for account in accounts:
            converted = await safe_convert(
                self._state.container,
                account.balance,
                account.currency,
                base,
            )
            cards.append(
                AccountCard(
                    account,
                    base_currency=base,
                    base_balance=converted,
                    language=self._state.language,
                    on_edit=self._open_editor,
                    on_delete=self._confirm_delete,
                )
            )
        self._list.controls = cards
        safe_update(self._list)

    def _confirm_delete(self, account: Account) -> None:
        lang = self._state.language

        async def _do() -> None:
            await self._state.container.delete_account.execute(account.id)
            self._state.bump_refresh("dashboard", "accounts", "transactions")
            snack(self._page, tr("action.saved", lang))

        confirm_dialog(
            self._page,
            title=tr("action.confirm_delete", lang),
            message=account.name,
            confirm_text=tr("action.delete", lang),
            cancel_text=tr("action.cancel", lang),
            on_confirm=_do,
        )

    def _open_editor(self, account: Optional[Account] = None) -> None:
        lang = self._state.language
        initial_icon = account.icon if account else ACCOUNT_ICONS[0]
        if not is_valid_account_icon(initial_icon):
            initial_icon = ACCOUNT_ICONS[0]
        selected_icon = {"value": initial_icon}
        selected_color = {"value": account.color if account else ACCOUNT_COLORS[0]}
        icons_open = {"value": False}
        colors_open = {"value": False}

        name_tf = ft.TextField(
            label=tr("field.name", lang),
            value=account.name if account else "",
        )
        currency_dd = ft.Dropdown(
            label=tr("field.currency", lang),
            value=normalize_currency_code(
                account.currency if account else self._state.base_currency
            ),
            options=currency_dropdown_options(lang=lang, include_crypto=True),
            expand=True,
            dense=True,
        )
        balance_tf = ft.TextField(
            label=tr("account.balance", lang),
            value=str(account.initial_balance if account else "0"),
            keyboard_type=ft.KeyboardType.NUMBER,
            disabled=account is not None,
        )

        icon_preview = ft.Container(
            width=48,
            height=48,
            border_radius=14,
            alignment=ft.Alignment.CENTER,
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
            border=ft.Border.all(2, ft.Colors.OUTLINE_VARIANT),
            content=account_icon_control(selected_icon["value"], size=26),
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
            icon_preview.content = account_icon_control(
                selected_icon["value"],
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
                content=account_icon_control(
                    key,
                    size=20,
                    color=selected_color["value"],
                ),
            )

        def _rebuild_grids() -> None:
            icon_groups_col.controls = []
            for group_key, keys in account_icon_groups():
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
            for color in ACCOUNT_COLORS:
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

        async def _save(_e: ft.ControlEvent | None = None) -> None:
            try:
                initial = Decimal(str(balance_tf.value or "0").replace(",", "."))
            except (InvalidOperation, ValueError):
                snack(self._page, tr("invalid_amount", lang), error=True)
                return
            if not (name_tf.value or "").strip():
                snack(self._page, tr("field.name", lang), error=True)
                return
            entity = Account(
                id=account.id if account else Account(name="tmp").id,
                name=name_tf.value.strip(),
                currency=normalize_currency_code(currency_dd.value or "RUB"),
                balance=account.balance if account else initial,
                initial_balance=account.initial_balance if account else initial,
                icon=selected_icon["value"],
                color=selected_color["value"],
                is_active=account.is_active if account else True,
                created_at=account.created_at if account else Account(name="tmp").created_at,
            )
            try:
                if account:
                    await self._state.container.update_account.execute(entity)
                else:
                    await self._state.container.create_account.execute(entity)
            except Exception as exc:  # noqa: BLE001
                snack(self._page, str(exc), error=True)
                return
            _close_editor()
            self._state.bump_refresh("dashboard", "accounts", "transactions")
            snack(self._page, tr("action.saved", lang))

        title = tr("action.edit", lang) if account else tr("action.add", lang)
        overlay = ft.Container(
            left=0,
            top=0,
            right=0,
            bottom=0,
            bgcolor=ft.Colors.SURFACE,
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
                                on_click=lambda _e: _close_editor(),
                            ),
                            actions=[
                                ft.FilledButton(
                                    tr("action.save", lang),
                                    icon=ft.Icons.CHECK,
                                    on_click=lambda e: run_async(self._page, _save, e),
                                ),
                            ],
                        ),
                        ft.Container(
                            expand=True,
                            padding=ft.padding.symmetric(horizontal=16, vertical=8),
                            content=ft.Column(
                                expand=True,
                                spacing=12,
                                scroll=ft.ScrollMode.AUTO,
                                controls=[
                                    name_tf,
                                    currency_dd,
                                    balance_tf,
                                    icon_toggle,
                                    icon_panel,
                                    color_toggle,
                                    color_panel,
                                    ft.Container(height=24),
                                ],
                            ),
                        ),
                    ],
                ),
            ),
        )

        def _close_editor(_e: ft.ControlEvent | None = None) -> None:
            try:
                if overlay in self._page.overlay:
                    self._page.overlay.remove(overlay)
                self._page.update()
            except Exception:  # noqa: BLE001
                pass

        # Drop any previous fullscreen account editor.
        for item in list(self._page.overlay):
            if getattr(item, "data", None) == "account_editor":
                try:
                    self._page.overlay.remove(item)
                except Exception:  # noqa: BLE001
                    pass
        overlay.data = "account_editor"
        self._page.overlay.append(overlay)
        self._page.update()

