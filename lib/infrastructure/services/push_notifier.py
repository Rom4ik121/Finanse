"""OS push / local notifications (Windows Toast + Android)."""

from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import sys
from pathlib import Path
from typing import Any, Optional, Protocol

logger = logging.getLogger("finanse.infrastructure.services.push_notifier")

APP_ID = "FinWise"
ANDROID_CHANNEL_ID = "finwise_reminders"
ANDROID_CHANNEL_NAME = "FinWise reminders"
ANDROID_CHANNEL_DESC = "Debt, subscription, and goal alerts"


class AndroidNotificationsBridge(Protocol):
    """Subset of ``FletAndroidNotifications`` used by FinWise."""

    async def request_permissions(self) -> Any: ...

    async def are_notifications_enabled(self) -> Any: ...

    async def show_notification(
        self,
        notification_id: int,
        title: str,
        body: str,
        **kwargs: Any,
    ) -> Any: ...


_android_service: AndroidNotificationsBridge | None = None
_seq = 0


def set_android_notifications(service: AndroidNotificationsBridge | None) -> None:
    """Register the Flet Android notifications service."""
    global _android_service
    _android_service = service


def get_android_notifications() -> AndroidNotificationsBridge | None:
    """Return the registered Android notifications service, if any."""
    return _android_service


def push_disabled_by_env() -> bool:
    """Test hook: ``FINANCE_DISABLE_PUSH=1`` skips OS notifications."""
    return os.environ.get("FINANCE_DISABLE_PUSH", "").strip().lower() in {
        "1",
        "true",
        "yes",
    }


def stable_notification_id(kind: str, related_id: str | None = None) -> int:
    """Stable positive int id for replaceable OS notifications."""
    digest = hashlib.md5(f"{kind}:{related_id or ''}".encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % 2_000_000_000 or 1


def next_notification_id() -> int:
    """Monotonic fallback id when no related entity exists."""
    global _seq
    _seq += 1
    return 100_000 + (_seq % 1_000_000)


def _icon_path() -> str:
    icon = Path(__file__).resolve().parents[3] / "assets" / "icon.ico"
    return str(icon) if icon.is_file() else ""


def _show_windows_toast(title: str, body: str) -> bool:
    """Show a Windows toast notification via winotify."""
    if sys.platform != "win32":
        return False
    try:
        from winotify import Notification
    except Exception:  # noqa: BLE001
        logger.debug("winotify unavailable", exc_info=True)
        return False
    try:
        toast = Notification(
            app_id=APP_ID,
            title=title or APP_ID,
            msg=body or "",
            icon=_icon_path(),
            duration="short",
        )
        toast.show()
        return True
    except Exception:  # noqa: BLE001
        logger.exception("Windows toast failed")
        return False


async def request_push_permissions() -> bool:
    """Request OS notification permission when supported."""
    if push_disabled_by_env():
        return False
    svc = _android_service
    if svc is None:
        # Windows toasts do not need a runtime permission prompt.
        return sys.platform == "win32"
    try:
        granted = await svc.request_permissions()
        return bool(granted)
    except Exception:  # noqa: BLE001
        logger.exception("Android notification permission request failed")
        return False


async def show_os_notification(
    title: str,
    body: str,
    *,
    notification_id: Optional[int] = None,
    kind: str = "info",
    related_id: Optional[str] = None,
) -> bool:
    """Show a system notification on the current platform."""
    if push_disabled_by_env():
        return False

    nid = notification_id
    if nid is None:
        nid = (
            stable_notification_id(kind, related_id)
            if related_id
            else next_notification_id()
        )

    svc = _android_service
    if svc is not None:
        try:
            await svc.show_notification(
                nid,
                title or APP_ID,
                body or "",
                channel_id=ANDROID_CHANNEL_ID,
                channel_name=ANDROID_CHANNEL_NAME,
                channel_description=ANDROID_CHANNEL_DESC,
                importance="high",
                play_sound=True,
                enable_vibration=True,
            )
            return True
        except Exception:  # noqa: BLE001
            logger.exception("Android OS notification failed")

    if _show_windows_toast(title, body):
        return True

    logger.debug("No OS notification backend available for this platform")
    return False


def dispatch_push(
    title: str,
    body: str,
    *,
    kind: str = "info",
    related_id: Optional[str] = None,
    notification_id: Optional[int] = None,
) -> None:
    """Fire an OS notification from sync code (schedules async when needed)."""
    if push_disabled_by_env():
        return

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # No event loop — Windows toast is sync-safe.
        if _android_service is None:
            _show_windows_toast(title, body)
        else:
            logger.debug("Skipping Android push outside event loop")
        return

    loop.create_task(
        show_os_notification(
            title,
            body,
            notification_id=notification_id,
            kind=kind,
            related_id=related_id,
        )
    )


def register_android_notifications(page: Any) -> bool:
    """Attach ``FletAndroidNotifications`` on Android builds."""
    try:
        from flet import PagePlatform
        from lib.infrastructure.services.biometric import is_mobile_platform

        if not is_mobile_platform(page):
            return False
        if getattr(page, "platform", None) not in {
            PagePlatform.ANDROID,
            PagePlatform.ANDROID_TV,
        }:
            # iOS: package does not provide a bridge yet.
            return False
    except Exception:  # noqa: BLE001
        return False

    try:
        from flet_android_notifications import FletAndroidNotifications

        service = FletAndroidNotifications()
        page.add(service)
        page.update()
        set_android_notifications(service)
        logger.info("Android push notification service registered")
        return True
    except Exception:  # noqa: BLE001
        logger.exception("Failed to register Android notifications")
        return False
