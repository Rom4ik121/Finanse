"""Account card with multi-currency balance display."""

from __future__ import annotations

from decimal import Decimal
from typing import Callable, Optional

import flet as ft

from lib.domain.entities.account import Account
from lib.presentation.account_icons import account_icon_control
from lib.presentation.styles import card_surface, muted_text
from lib.presentation.utils import format_money


class AccountCard(ft.Container):
    """Card showing account name, native balance, and optional base conversion."""

    def __init__(
        self,
        account: Account,
        *,
        base_currency: str = "RUB",
        base_balance: Optional[Decimal] = None,
        language: str = "ru",
        on_click: Optional[Callable[[Account], None]] = None,
        on_edit: Optional[Callable[[Account], None]] = None,
        on_delete: Optional[Callable[[Account], None]] = None,
    ) -> None:
        from lib.presentation.utils import tr

        native = format_money(account.balance, account.currency)
        accent = account.color or ft.Colors.PRIMARY
        converted_line: list[ft.Control] = []
        if (
            base_balance is not None
            and account.currency.upper() != base_currency.upper()
        ):
            converted_line.append(
                muted_text(f"≈ {format_money(base_balance, base_currency)}")
            )

        menu = ft.PopupMenuButton(
            icon=ft.Icons.MORE_VERT,
            icon_color=ft.Colors.ON_SURFACE_VARIANT,
            items=[
                ft.PopupMenuItem(
                    content=ft.Text(tr("action.edit", language)),
                    icon=ft.Icons.EDIT_OUTLINED,
                    on_click=lambda _e: on_edit(account) if on_edit else None,
                ),
                ft.PopupMenuItem(
                    content=ft.Text(tr("action.delete", language)),
                    icon=ft.Icons.DELETE_OUTLINE,
                    on_click=lambda _e: on_delete(account) if on_delete else None,
                ),
            ],
        )

        body = ft.Column(
            spacing=12,
            tight=True,
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Row(
                            spacing=12,
                            controls=[
                                ft.Container(
                                    width=46,
                                    height=46,
                                    border_radius=14,
                                    bgcolor=accent,
                                    alignment=ft.Alignment.CENTER,
                                    content=account_icon_control(
                                        account.icon,
                                        size=24,
                                        color=ft.Colors.WHITE,
                                    ),
                                ),
                                ft.Column(
                                    spacing=2,
                                    tight=True,
                                    controls=[
                                        ft.Text(
                                            account.name,
                                            weight=ft.FontWeight.W_700,
                                            size=16,
                                        ),
                                        muted_text(account.currency),
                                    ],
                                ),
                            ],
                        ),
                        menu,
                    ],
                ),
                ft.Text(native, size=22, weight=ft.FontWeight.W_700),
                *converted_line,
            ],
        )
        card = card_surface(
            body,
            accent=accent,
            ink=True,
            on_click=lambda _e: on_click(account)
            if on_click
            else (on_edit(account) if on_edit else None),
        )
        super().__init__(
            padding=12,
            border_radius=14,
            bgcolor=card.bgcolor,
            border=card.border,
            shadow=card.shadow,
            ink=True,
            on_click=card.on_click,
            content=body,
            margin=ft.Margin.only(bottom=8),
        )
