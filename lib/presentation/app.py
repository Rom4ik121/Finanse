"""Finanse Flet application shell and navigation."""

from __future__ import annotations

import logging
import os
from typing import Any, Optional

import flet as ft

from lib.infrastructure.services.encryption_service import EncryptionService
from lib.presentation.pages.accounts import AccountsPage
from lib.presentation.pages.currencies import CurrenciesPage
from lib.presentation.pages.dashboard import DashboardPage
from lib.presentation.pages.debts import DebtsPage
from lib.presentation.pages.goals import GoalsPage
from lib.presentation.pages.settings import SettingsPage
from lib.presentation.pages.subscriptions import SubscriptionsPage
from lib.presentation.pages.transactions import TransactionsPage
from lib.presentation.state.app_state import AppState
from lib.presentation.theme import apply_theme
from lib.presentation.utils import snack, tr
from lib.presentation.widgets.lock_screen import LockScreen

logger = logging.getLogger("finanse.presentation.app")

_NAV_RADIUS = 28
_NAV_MARGIN = ft.Margin.only(left=12, right=12, bottom=8, top=4)


class FinanseApp:
    """Root UI controller: floating NavigationBar shell + secondary routes."""

    def __init__(self, page: ft.Page, container: Any) -> None:
        self.page = page
        self.state = AppState(container)
        self._content = ft.AnimatedSwitcher(
            content=ft.Container(expand=True),
            transition=ft.AnimatedSwitcherTransition.FADE,
            duration=280,
            reverse_duration=180,
            switch_in_curve=ft.AnimationCurve.EASE_OUT,
            switch_out_curve=ft.AnimationCurve.EASE_IN,
            expand=True,
        )
        self._nav = ft.NavigationBar(
            destinations=[],
            on_change=self._on_nav_change,
        )
        self._nav_host = ft.Container(
            margin=_NAV_MARGIN,
            border_radius=_NAV_RADIUS,
            clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
            bgcolor=ft.Colors.SURFACE_CONTAINER,
            border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
            shadow=ft.BoxShadow(
                spread_radius=0,
                blur_radius=22,
                color="#00000033",
                offset=ft.Offset(0, 6),
            ),
            content=self._nav,
        )
        self._shell = ft.SafeArea(
            expand=True,
            avoid_intrusions_top=True,
            avoid_intrusions_left=True,
            avoid_intrusions_right=True,
            avoid_intrusions_bottom=True,
            minimum_padding=ft.padding.only(top=8, bottom=4, left=0, right=0),
            maintain_bottom_view_padding=True,
            content=ft.Column(
                expand=True,
                spacing=0,
                controls=[self._content, self._nav_host],
            ),
        )
        self._rendered_tab: Optional[int] = None
        self._rendered_secondary: Optional[str] = None
        self._rendered_lang: Optional[str] = None
        self._rendered_unlocked: Optional[bool] = None
        self._rendered_rebuild_token: int = -1
        self._primary_cache: dict[int, ft.Control] = {}
        self._pin_hash: Optional[str] = None
        self._pin_salt: Optional[str] = None

    async def start(self) -> None:
        """Load settings, apply theme, and mount the shell."""
        page = self.page
        page.title = "Finanse"
        page.padding = 0
        # Custom floating nav — do not use scaffold NavigationBar.
        page.navigation_bar = None
        try:
            page.window.min_width = 320
            page.window.min_height = 560
            # Comfortable default desktop size (still mobile-friendly layout).
            if getattr(page.window, "width", None) in (None, 0):
                page.window.width = 420
                page.window.height = 780
        except Exception:  # noqa: BLE001
            pass

        try:
            settings = await self.state.container.get_settings.execute()
            self.state.set_settings(settings, notify=False)
        except Exception:  # noqa: BLE001
            logger.exception("Failed to load settings; using defaults")

        apply_theme(page, self.state.theme_mode)
        await self._load_pin_gate()
        self._build_navigation_bar()
        self.state.subscribe(self._on_state_changed)

        page.add(self._shell)
        self._render(force=True)
        self._flush_notifications()

    async def _load_pin_gate(self) -> None:
        """Decide whether the session starts locked."""
        repo = self.state.container.settings_repository
        if repo is None or not hasattr(repo, "get_pin_credentials"):
            self.state.set_unlocked(True, notify=False)
            return
        try:
            pin_hash, pin_salt, biometric = await repo.get_pin_credentials()
        except Exception:  # noqa: BLE001
            logger.exception("Failed to load PIN credentials")
            self.state.set_unlocked(True, notify=False)
            return
        self._pin_hash = pin_hash
        self._pin_salt = pin_salt
        if pin_hash and pin_salt:
            self.state.settings.biometric_enabled = biometric
            self.state.set_unlocked(False, notify=False)
        else:
            self.state.set_unlocked(True, notify=False)

    def _build_navigation_bar(self) -> None:
        lang = self.state.language
        self._nav.selected_index = self.state.selected_tab
        self._nav.bgcolor = ft.Colors.TRANSPARENT
        self._nav.indicator_color = ft.Colors.PRIMARY_CONTAINER
        self._nav.elevation = 0
        self._nav.shadow_color = ft.Colors.TRANSPARENT
        self._nav.label_behavior = ft.NavigationBarLabelBehavior.ALWAYS_SHOW
        self._nav.destinations = [
            ft.NavigationBarDestination(
                icon=ft.Icons.HOME_OUTLINED,
                selected_icon=ft.Icons.HOME,
                label=tr("nav.home", lang),
            ),
            ft.NavigationBarDestination(
                icon=ft.Icons.RECEIPT_LONG_OUTLINED,
                selected_icon=ft.Icons.RECEIPT_LONG,
                label=tr("nav.transactions", lang),
            ),
            ft.NavigationBarDestination(
                icon=ft.Icons.ACCOUNT_BALANCE_WALLET_OUTLINED,
                selected_icon=ft.Icons.ACCOUNT_BALANCE_WALLET,
                label=tr("nav.accounts", lang),
            ),
            ft.NavigationBarDestination(
                icon=ft.Icons.SETTINGS_OUTLINED,
                selected_icon=ft.Icons.SETTINGS,
                label=tr("nav.settings", lang),
            ),
        ]
        self._nav_host.bgcolor = ft.Colors.SURFACE_CONTAINER
        self._nav_host.border = ft.Border.all(1, ft.Colors.OUTLINE_VARIANT)
        self._rendered_lang = lang

    def _on_nav_change(self, e: ft.ControlEvent) -> None:
        index = int(getattr(e.control, "selected_index", 0) or 0)
        self.state.set_tab(index)

    def _on_state_changed(self, _state: AppState) -> None:
        if self._rendered_rebuild_token != self.state.view_rebuild_token:
            self._primary_cache.clear()
            self._rendered_rebuild_token = self.state.view_rebuild_token
            self._render(force=True)
            self._flush_notifications()
            return
        needs_nav = (
            self._rendered_tab != self.state.selected_tab
            or self._rendered_secondary != self.state.secondary_route
            or self._rendered_lang != self.state.language
            or self._rendered_unlocked != self.state.is_unlocked
        )
        if self._rendered_lang != self.state.language:
            # Nav labels update immediately; force remount so page strings
            # switch language too (plain _render early-returns on same tab).
            self._build_navigation_bar()
            self._primary_cache.clear()
            self._render(force=True)
            self._flush_notifications()
            return
        if needs_nav:
            self._render()
        self._flush_notifications()

    def _flush_notifications(self) -> None:
        for message in self.state.pop_notifications():
            snack(self.page, message)

    def _primary_page(self, tab: int) -> ft.Control:
        cached = self._primary_cache.get(tab)
        if cached is not None:
            return cached
        if tab == AppState.TAB_TRANSACTIONS:
            view: ft.Control = TransactionsPage(self.page, self.state)
        elif tab == AppState.TAB_ACCOUNTS:
            view = AccountsPage(self.page, self.state)
        elif tab == AppState.TAB_SETTINGS:
            view = SettingsPage(self.page, self.state)
        else:
            view = DashboardPage(self.page, self.state)
        self._primary_cache[tab] = view
        return view

    def _secondary_page(self, route: str) -> ft.Control:
        if route == "goals":
            return GoalsPage(self.page, self.state)
        if route == "debts":
            return DebtsPage(self.page, self.state)
        if route == "subscriptions":
            return SubscriptionsPage(self.page, self.state)
        if route == "currencies":
            return CurrenciesPage(self.page, self.state)
        return self._primary_page(self.state.selected_tab)

    async def _unlock(self) -> None:
        self.state.set_unlocked(True)

    def _render(self, *, force: bool = False) -> None:
        """Swap primary / secondary content based on AppState."""
        if not self.state.is_unlocked and self._pin_hash and self._pin_salt:
            self._nav_host.visible = False
            self._content.content = LockScreen(
                self.page,
                language=self.state.language,
                pin_hash=self._pin_hash,
                pin_salt=self._pin_salt,
                biometric_enabled=bool(self.state.settings.biometric_enabled),
                on_unlocked=self._unlock,
                encryption=self.state.container.encryption_service
                or EncryptionService(),
                # Windows Hello is local to the PC; skip auto-prompt for remote web/mobile sessions.
                auto_biometric=os.environ.get("FLET_FORCE_WEB_SERVER", "").lower()
                not in {"1", "true", "yes"},
            )
            self._rendered_unlocked = False
            self.page.update()
            return

        route = self.state.secondary_route
        tab = self.state.selected_tab
        if (
            not force
            and self._rendered_tab == tab
            and self._rendered_secondary == route
            and self._rendered_unlocked is True
        ):
            return

        if route:
            view = self._secondary_page(route)
        else:
            view = self._primary_page(tab)

        self._nav_host.visible = route is None
        self._nav.selected_index = tab

        self._content.content = view
        self._rendered_tab = tab
        self._rendered_secondary = route
        self._rendered_unlocked = True
        self.page.update()
