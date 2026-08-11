"""Observable application state for the presentation layer."""

from __future__ import annotations

import logging
from typing import Any, Callable, Optional

from lib.domain.entities.currency_codes import normalize_currency_code
from lib.domain.entities.settings import AppSettings
from lib.infrastructure.services.localization import normalize_lang

logger = logging.getLogger("finanse.presentation.state")

Listener = Callable[["AppState"], None]


class AppState:
    """Central UI state with a simple Observer (subscribe / notify) pattern.

    Holds the DI container, settings snapshot, selected navigation tab,
    secondary route, and refresh tokens so pages can re-render when data
    changes.
    """

    TAB_HOME = 0
    TAB_TRANSACTIONS = 1
    TAB_ACCOUNTS = 2
    TAB_SETTINGS = 3

    def __init__(self, container: Any) -> None:
        self.container = container
        self.settings: AppSettings = AppSettings()
        self.selected_tab: int = self.TAB_HOME
        self.secondary_route: Optional[str] = None
        self.refresh_token: int = 0
        self.dashboard_token: int = 0
        self.transactions_token: int = 0
        self.accounts_token: int = 0
        self.is_loading: bool = False
        self.is_unlocked: bool = True
        self.pending_notifications: list[str] = []
        self.view_rebuild_token: int = 0
        self._listeners: list[Listener] = []

    # ------------------------------------------------------------------
    # Observer
    # ------------------------------------------------------------------

    def subscribe(self, listener: Listener) -> None:
        """Register a listener invoked on every :meth:`notify`."""
        if listener not in self._listeners:
            self._listeners.append(listener)

    def unsubscribe(self, listener: Listener) -> None:
        """Remove a previously registered listener."""
        try:
            self._listeners.remove(listener)
        except ValueError:
            pass

    def notify(self) -> None:
        """Notify all subscribers that state has changed."""
        for listener in list(self._listeners):
            try:
                listener(self)
            except Exception:  # noqa: BLE001 — UI must stay alive
                logger.exception("AppState listener failed")

    # ------------------------------------------------------------------
    # Mutators
    # ------------------------------------------------------------------

    @property
    def language(self) -> str:
        """Current UI language code."""
        return normalize_lang(self.settings.language)

    @property
    def base_currency(self) -> str:
        """User-selected base / display currency (normalized ISO code)."""
        return normalize_currency_code(self.settings.default_currency or "RUB")

    @property
    def theme_mode(self) -> str:
        """Theme preference: light / dark / system."""
        return self.settings.theme or "system"

    def set_settings(self, settings: AppSettings, *, notify: bool = True) -> None:
        """Replace settings snapshot and optionally notify listeners."""
        self.settings = settings
        if notify:
            self.notify()

    def set_tab(self, index: int, *, clear_secondary: bool = True) -> None:
        """Select a primary NavigationBar tab."""
        self.selected_tab = index
        if clear_secondary:
            self.secondary_route = None
        self.notify()

    def open_secondary(self, route: str) -> None:
        """Open a secondary screen (goals, debts, subscriptions, currencies)."""
        self.secondary_route = route
        self.notify()

    def close_secondary(self) -> None:
        """Return from a secondary screen to the primary tab content."""
        self.secondary_route = None
        self.notify()

    def bump_refresh(self, *scopes: str) -> None:
        """Increment refresh tokens so listening pages reload data.

        Args:
            scopes: Optional scopes such as ``dashboard``, ``transactions``,
                ``accounts``. Empty means global refresh.
        """
        self.refresh_token += 1
        if not scopes or "dashboard" in scopes:
            self.dashboard_token += 1
        if not scopes or "transactions" in scopes:
            self.transactions_token += 1
        if not scopes or "accounts" in scopes:
            self.accounts_token += 1
        self.notify()

    def set_loading(self, value: bool) -> None:
        """Toggle a global loading flag."""
        self.is_loading = value
        self.notify()

    def set_unlocked(self, value: bool, *, notify: bool = True) -> None:
        """Mark the session as unlocked (PIN gate passed)."""
        self.is_unlocked = value
        if notify:
            self.notify()

    def push_notification(self, message: str, *, notify: bool = True) -> None:
        """Queue an in-app notification banner message."""
        self.pending_notifications.append(message)
        if notify:
            self.notify()

    def pop_notifications(self) -> list[str]:
        """Drain queued notification messages."""
        items = list(self.pending_notifications)
        self.pending_notifications.clear()
        return items

    def request_view_rebuild(self) -> None:
        """Ask the shell to drop cached views (e.g. after theme change)."""
        self.view_rebuild_token += 1
        self.notify()
