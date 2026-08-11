"""AppState observer and refresh tokens."""

from __future__ import annotations

from lib.domain.entities.settings import AppSettings
from lib.presentation.state.app_state import AppState


class _FakeContainer:
    pass


def test_subscribe_notify() -> None:
    state = AppState(_FakeContainer())
    seen: list[int] = []

    def listener(s: AppState) -> None:
        seen.append(s.refresh_token)

    state.subscribe(listener)
    state.bump_refresh("dashboard")
    assert seen
    state.unsubscribe(listener)
    prev = len(seen)
    state.bump_refresh("accounts")
    assert len(seen) == prev


def test_language_and_currency_normalized() -> None:
    state = AppState(_FakeContainer())
    state.set_settings(
        AppSettings(language="uz-UZ", default_currency="usd"),
        notify=False,
    )
    assert state.language == "uz"
    assert state.base_currency == "USD"


def test_secondary_route_and_notifications() -> None:
    state = AppState(_FakeContainer())
    state.open_secondary("goals")
    assert state.secondary_route == "goals"
    state.close_secondary()
    assert state.secondary_route is None
    state.push_notification("hello")
    assert state.pop_notifications() == ["hello"]
    assert state.pop_notifications() == []


def test_tabs_and_rebuild() -> None:
    state = AppState(_FakeContainer())
    state.set_tab(AppState.TAB_SETTINGS)
    assert state.selected_tab == AppState.TAB_SETTINGS
    before = state.view_rebuild_token
    state.request_view_rebuild()
    assert state.view_rebuild_token == before + 1
