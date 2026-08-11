"""Subscription list card."""

from __future__ import annotations

from typing import Callable, Optional

import flet as ft

from lib.domain.entities.subscription import Periodicity, Subscription
from lib.presentation.styles import card_surface, muted_text
from lib.presentation.utils import format_date, format_money


class SubscriptionCard(ft.Container):
    """Shows recurring charge details and next billing date."""

    def __init__(
        self,
        subscription: Subscription,
        *,
        language: str = "ru",
        on_edit: Optional[Callable[[Subscription], None]] = None,
        on_delete: Optional[Callable[[Subscription], None]] = None,
    ) -> None:
        from lib.presentation.utils import tr

        period = (
            tr("subscription.monthly", language)
            if subscription.periodicity == Periodicity.MONTHLY
            else tr("subscription.yearly", language)
        )
        body = ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            controls=[
                ft.Column(
                    spacing=4,
                    tight=True,
                    expand=True,
                    controls=[
                        ft.Text(subscription.name, weight=ft.FontWeight.W_700, size=16),
                        muted_text(f"{subscription.category} · {period}"),
                        ft.Text(
                            tr(
                                "subscription.next_billing",
                                language,
                                date=format_date(subscription.next_billing_date),
                            ),
                            size=12,
                            weight=ft.FontWeight.W_500,
                        ),
                    ],
                ),
                ft.Column(
                    horizontal_alignment=ft.CrossAxisAlignment.END,
                    tight=True,
                    spacing=4,
                    controls=[
                        ft.Text(
                            format_money(subscription.amount, subscription.currency),
                            weight=ft.FontWeight.W_700,
                            color=ft.Colors.PRIMARY,
                            size=16,
                        ),
                        ft.PopupMenuButton(
                            icon=ft.Icons.MORE_VERT,
                            icon_color=ft.Colors.ON_SURFACE_VARIANT,
                            items=[
                                ft.PopupMenuItem(
                                    content=ft.Text(tr("action.edit", language)),
                                    icon=ft.Icons.EDIT_OUTLINED,
                                    on_click=lambda _e: on_edit(subscription)
                                    if on_edit
                                    else None,
                                ),
                                ft.PopupMenuItem(
                                    content=ft.Text(tr("action.delete", language)),
                                    icon=ft.Icons.DELETE_OUTLINE,
                                    on_click=lambda _e: on_delete(subscription)
                                    if on_delete
                                    else None,
                                ),
                            ],
                        ),
                    ],
                ),
            ],
        )
        card = card_surface(
            body,
            ink=True,
            on_click=lambda _e: on_edit(subscription) if on_edit else None,
        )
        super().__init__(
            padding=card.padding,
            border_radius=card.border_radius,
            bgcolor=card.bgcolor,
            border=card.border,
            shadow=card.shadow,
            opacity=1.0 if subscription.is_active else 0.55,
            ink=True,
            on_click=card.on_click,
            animate=card.animate,
            content=body,
        )
