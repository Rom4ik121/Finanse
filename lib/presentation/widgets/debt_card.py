"""Debt summary card."""

from __future__ import annotations

from decimal import Decimal
from typing import Callable, Optional

import flet as ft

from lib.domain.entities.debt import Debt, DebtDirection, DebtStatus
from lib.presentation.styles import card_surface, muted_text
from lib.presentation.utils import format_date, format_money


class DebtCard(ft.Container):
    """Card for a personal debt with optional interest line."""

    def __init__(
        self,
        debt: Debt,
        *,
        language: str = "ru",
        interest_amount: Optional[Decimal] = None,
        alert: bool = False,
        on_click: Optional[Callable[[Debt], None]] = None,
        on_edit: Optional[Callable[[Debt], None]] = None,
        on_delete: Optional[Callable[[Debt], None]] = None,
        on_repay: Optional[Callable[[Debt], None]] = None,
    ) -> None:
        from lib.presentation.utils import tr

        i_owe = debt.direction == DebtDirection.I_OWE
        accent = ft.Colors.ERROR if i_owe else ft.Colors.SECONDARY
        status_value = (
            debt.status.value
            if isinstance(debt.status, DebtStatus)
            else str(debt.status)
        )
        status_color = (
            ft.Colors.ON_SURFACE_VARIANT
            if debt.status in (DebtStatus.PAID, DebtStatus.ARCHIVED)
            else (ft.Colors.ERROR if debt.status == DebtStatus.OVERDUE else accent)
        )
        interest_line: list[ft.Control] = []
        if debt.interest_rate is not None:
            text = tr(
                "debt.interest_per_year",
                language,
                rate=str(debt.interest_rate),
            )
            if interest_amount is not None:
                text += f" · {format_money(interest_amount, debt.currency)}"
            interest_line.append(muted_text(text))

        menu_items = [
            ft.PopupMenuItem(
                content=ft.Text(tr("action.edit", language)),
                icon=ft.Icons.EDIT_OUTLINED,
                on_click=lambda _e: on_edit(debt) if on_edit else None,
            ),
            ft.PopupMenuItem(
                content=ft.Text(tr("action.delete", language)),
                icon=ft.Icons.DELETE_OUTLINE,
                on_click=lambda _e: on_delete(debt) if on_delete else None,
            ),
        ]
        can_repay = (
            on_repay is not None
            and debt.status in (DebtStatus.ACTIVE, DebtStatus.OVERDUE)
        )
        if can_repay:
            menu_items.insert(
                0,
                ft.PopupMenuItem(
                    content=ft.Text(
                        tr("debt.repay", language)
                        if i_owe
                        else tr("debt.receive", language)
                    ),
                    icon=ft.Icons.PAYMENTS_OUTLINED,
                    on_click=lambda _e: on_repay(debt),
                ),
            )

        actions_row: list[ft.Control] = [
            ft.PopupMenuButton(
                icon=ft.Icons.MORE_VERT,
                icon_color=ft.Colors.ON_SURFACE_VARIANT,
                items=menu_items,
            )
        ]
        if alert:
            actions_row.insert(
                0,
                ft.IconButton(
                    icon=ft.Icons.PRIORITY_HIGH,
                    icon_color=ft.Colors.ON_ERROR,
                    bgcolor=ft.Colors.ERROR,
                    tooltip=tr("notify.debt_due", language),
                    on_click=lambda _e: on_repay(debt) if can_repay else None,
                    style=ft.ButtonStyle(
                        shape=ft.CircleBorder(),
                        padding=10,
                    ),
                ),
            )
        elif can_repay:
            actions_row.insert(
                0,
                ft.IconButton(
                    icon=ft.Icons.PAYMENTS_OUTLINED,
                    icon_color=accent,
                    tooltip=tr("debt.repay", language)
                    if i_owe
                    else tr("debt.receive", language),
                    on_click=lambda _e: on_repay(debt),
                ),
            )

        body = ft.Column(
            spacing=8,
            tight=True,
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Text(
                            debt.counterparty,
                            weight=ft.FontWeight.W_700,
                            size=16,
                            expand=True,
                        ),
                        ft.Row(tight=True, controls=actions_row),
                    ],
                ),
                ft.Container(
                    padding=ft.Padding.symmetric(horizontal=10, vertical=4),
                    border_radius=999,
                    bgcolor=ft.Colors.ERROR_CONTAINER
                    if i_owe
                    else ft.Colors.SECONDARY_CONTAINER,
                    content=ft.Text(
                        (
                            tr("debt.i_owe", language)
                            if i_owe
                            else tr("debt.owed_to_me", language)
                        )
                        + " · "
                        + tr(f"debt.status.{status_value}", language),
                        size=11,
                        weight=ft.FontWeight.W_600,
                        color=status_color,
                    ),
                ),
                ft.Text(
                    format_money(debt.remaining_amount, debt.currency),
                    size=20,
                    weight=ft.FontWeight.W_700,
                    color=accent,
                ),
                muted_text(
                    tr("debt.due_by", language, date=format_date(debt.due_date))
                    if debt.due_date
                    else tr("debt.no_due_date", language)
                ),
                *interest_line,
            ],
        )
        card = card_surface(
            body,
            ink=True,
            on_click=lambda _e: on_click(debt)
            if on_click
            else (on_edit(debt) if on_edit else None),
        )
        super().__init__(
            padding=card.padding,
            border_radius=card.border_radius,
            bgcolor=card.bgcolor,
            border=card.border,
            shadow=card.shadow,
            ink=True,
            on_click=card.on_click,
            animate=card.animate,
            content=body,
        )
