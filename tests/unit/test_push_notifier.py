"""Unit tests for OS push notifier helpers."""

from __future__ import annotations

import os

from lib.infrastructure.services.push_notifier import (
    dispatch_push,
    push_disabled_by_env,
    stable_notification_id,
)


def test_stable_notification_id_is_deterministic() -> None:
    a = stable_notification_id("debt_reminder", "abc")
    b = stable_notification_id("debt_reminder", "abc")
    c = stable_notification_id("debt_reminder", "xyz")
    assert a == b
    assert a != c
    assert 0 < a < 2_000_000_000


def test_dispatch_push_respects_disable_env(monkeypatch) -> None:
    monkeypatch.setenv("FINANCE_DISABLE_PUSH", "1")
    assert push_disabled_by_env()
    # Must not raise.
    dispatch_push("Title", "Body", kind="info")
    monkeypatch.delenv("FINANCE_DISABLE_PUSH", raising=False)
    assert not push_disabled_by_env()
