"""Accounts CRUD page with multi-currency display and icon/color pickers."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import TYPE_CHECKING, Optional

import flet as ft

from lib.core.config import ACCOUNT_COLORS
from lib.domain.entities.account import Account
from lib.domain.entities.currency_codes import normalize_currency_code
from lib.presentation.account_icons import (
    account_icon_control,
    account_icon_groups,
    is_valid_account_icon,
)
from lib.presentation.styles import ICON_CATALOG_GLYPH, page_header
from lib.presentation.utils import (
    load_rate_book,
    run_async,
    safe_update,
    snack,
    tr,
)
from lib.presentation.widgets.account_card import AccountCard
from lib.presentation.widgets.appearance_picker import open_color_picker, open_icon_picker
from lib.presentation.widgets.confirm_dialog import confirm_dialog
from lib.presentation.widgets.currency_ticker_picker import CurrencyTickerPicker
from lib.presentation.widgets.empty_state import EmptyState
from lib.presentation.widgets.fullscreen_form import dismiss_fullscreen
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
                    padding=ft.Padding.symmetric(horizontal=12),
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
        book = await load_rate_book(self._state.container)
        cards: list[ft.Control] = []
        for account in accounts:
            converted = book.convert(
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
        initial_icon = account.icon if account else "wallet"
        if not is_valid_account_icon(initial_icon):
            initial_icon = "wallet"
        selected_icon = {"value": initial_icon}
        selected_color = {"value": account.color if account else ACCOUNT_COLORS[0]}

        name_tf = ft.TextField(
            label=tr("field.name", lang),
            value=account.name if account else "",
        )
        currency_picker = CurrencyTickerPicker(
            self._page,
            lang=lang,
            label=tr("field.currency", lang),
            value=normalize_currency_code(
                account.currency if account else self._state.base_currency
            ),
            include_crypto=True,
            expand=True,
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
            border_radius=24,
            alignment=ft.Alignment.CENTER,
            bgcolor=selected_color["value"],
            content=account_icon_control(
                selected_icon["value"],
                size=24,
                color=ICON_CATALOG_GLYPH,
            ),
        )
        color_preview = ft.Container(
            width=48,
            height=48,
            border_radius=24,
            bgcolor=selected_color["value"],
            border=ft.Border.all(2, ft.Colors.OUTLINE_VARIANT),
        )
        color_toggle_label = ft.Text(
            tr("picker.choose_color", lang),
            size=13,
            weight=ft.FontWeight.W_600,
            expand=True,
        )
        icon_toggle_label = ft.Text(
            tr("picker.choose_icon", lang),
            size=13,
            weight=ft.FontWeight.W_600,
            expand=True,
        )
        color_chevron = ft.Icon(ft.Icons.CHEVRON_RIGHT, size=22)
        icon_chevron = ft.Icon(ft.Icons.CHEVRON_RIGHT, size=22)

        def _refresh_previews() -> None:
            icon_preview.content = account_icon_control(
                selected_icon["value"],
                size=24,
                color=ICON_CATALOG_GLYPH,
            )
            icon_preview.bgcolor = selected_color["value"]
            color_preview.bgcolor = selected_color["value"]
            try:
                icon_preview.update()
                color_preview.update()
            except Exception:  # noqa: BLE001
                pass

        def _select_icon(key: str) -> None:
            selected_icon["value"] = key
            _refresh_previews()

        def _select_color(color: str) -> None:
            selected_color["value"] = color
            _refresh_previews()

        def _open_icons(_e: ft.ControlEvent | None = None) -> None:
            open_icon_picker(
                self._page,
                lang=lang,
                groups=account_icon_groups(),
                selected=selected_icon["value"],
                on_select=_select_icon,
                render_icon=lambda key: account_icon_control(
                    key, size=22, color=ICON_CATALOG_GLYPH
                ),
                overlay_key="account_icon_picker",
            )

        def _open_colors(_e: ft.ControlEvent | None = None) -> None:
            open_color_picker(
                self._page,
                lang=lang,
                colors=ACCOUNT_COLORS,
                selected=selected_color["value"],
                on_select=_select_color,
                overlay_key="account_color_picker",
            )

        _refresh_previews()

        icon_toggle = ft.Container(
            padding=ft.Padding.symmetric(horizontal=10, vertical=8),
            border_radius=14,
            bgcolor=ft.Colors.SURFACE_CONTAINER,
            border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
            ink=True,
            on_click=_open_icons,
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
            padding=ft.Padding.symmetric(horizontal=10, vertical=8),
            border_radius=14,
            bgcolor=ft.Colors.SURFACE_CONTAINER,
            border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
            ink=True,
            on_click=_open_colors,
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
                currency=normalize_currency_code(currency_picker.value or "RUB"),
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
                            padding=ft.Padding.symmetric(horizontal=16, vertical=8),
                            content=ft.Column(
                                expand=True,
                                spacing=12,
                                scroll=ft.ScrollMode.AUTO,
                                controls=[
                                    name_tf,
                                    currency_picker,
                                    balance_tf,
                                    icon_toggle,
                                    color_toggle,
                                    ft.Container(height=24),
                                ],
                            ),
                        ),
                    ],
                ),
            ),
        )

        def _close_editor(_e: ft.ControlEvent | None = None) -> None:
            dismiss_fullscreen(self._page, key="account_icon_picker")
            dismiss_fullscreen(self._page, key="account_color_picker")
            currency_picker.close_overlay()
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

