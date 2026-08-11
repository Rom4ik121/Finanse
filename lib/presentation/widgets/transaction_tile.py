"""List tile for a single transaction."""

from __future__ import annotations

from typing import Callable, Optional

import flet as ft

from lib.domain.entities.category import Category
from lib.domain.entities.transaction import Transaction, TransactionType
from lib.presentation.styles import muted_text
from lib.presentation.utils import category_icon, format_date, format_money


class TransactionTile(ft.Container):
    """Compact row showing category, comment, date, and signed amount."""

    def __init__(
        self,
        transaction: Transaction,
        *,
        category: Optional[Category] = None,
        on_edit: Optional[Callable[[Transaction], None]] = None,
        on_delete: Optional[Callable[[Transaction], None]] = None,
        language: str = "ru",
        dark: bool = True,
    ) -> None:
        from lib.presentation.utils import tr

        _ = dark
        is_income = transaction.type == TransactionType.INCOME
        amount_color = ft.Colors.SECONDARY if is_income else ft.Colors.ERROR
        signed = format_money(
            transaction.amount,
            transaction.currency,
            signed=True,
        )
        if not is_income and not signed.startswith("−"):
            signed = f"−{format_money(transaction.amount, transaction.currency)}"

        tags = ", ".join(f"#{tag}" for tag in (transaction.tags or [])[:3])
        subtitle_parts = [format_date(transaction.date, with_time=True)]
        if transaction.comment:
            subtitle_parts.append(transaction.comment)
        if tags:
            subtitle_parts.append(tags)

        trailing_menu = ft.PopupMenuButton(
            icon=ft.Icons.MORE_VERT,
            icon_color=ft.Colors.ON_SURFACE_VARIANT,
            items=[
                ft.PopupMenuItem(
                    content=ft.Text(tr("action.edit", language)),
                    icon=ft.Icons.EDIT_OUTLINED,
                    on_click=lambda _e: on_edit(transaction) if on_edit else None,
                ),
                ft.PopupMenuItem(
                    content=ft.Text(tr("action.delete", language)),
                    icon=ft.Icons.DELETE_OUTLINE,
                    on_click=lambda _e: on_delete(transaction) if on_delete else None,
                ),
            ],
        )

        icon_bg = (
            category.color
            if category is not None
            else (
                ft.Colors.PRIMARY_CONTAINER
                if is_income
                else ft.Colors.ERROR_CONTAINER
            )
        )
        icon_data = (
            category_icon(category.icon)
            if category is not None
            else (ft.Icons.SOUTH_WEST if is_income else ft.Icons.NORTH_EAST)
        )
        icon_fg = "#FFFFFF" if category is not None else (
            ft.Colors.ON_PRIMARY_CONTAINER
            if is_income
            else ft.Colors.ON_ERROR_CONTAINER
        )

        body = ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=8,
            controls=[
                ft.Container(
                    width=36,
                    height=36,
                    border_radius=11,
                    bgcolor=icon_bg,
                    alignment=ft.Alignment.CENTER,
                    content=ft.Icon(icon_data, color=icon_fg, size=18),
                ),
                ft.Column(
                    spacing=1,
                    tight=True,
                    expand=True,
                    controls=[
                        ft.Text(
                            transaction.category,
                            weight=ft.FontWeight.W_600,
                            size=13,
                            overflow=ft.TextOverflow.ELLIPSIS,
                            max_lines=1,
                        ),
                        muted_text(" · ".join(subtitle_parts), size=10),
                    ],
                ),
                ft.Text(
                    signed,
                    color=amount_color,
                    weight=ft.FontWeight.W_700,
                    size=12,
                    text_align=ft.TextAlign.RIGHT,
                ),
                trailing_menu,
            ],
        )
        super().__init__(
            padding=ft.padding.symmetric(horizontal=10, vertical=8),
            border_radius=12,
            bgcolor=ft.Colors.SURFACE_CONTAINER,
            border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
            ink=True,
            on_click=lambda _e: on_edit(transaction) if on_edit else None,
            margin=ft.margin.only(bottom=6),
            content=body,
        )
