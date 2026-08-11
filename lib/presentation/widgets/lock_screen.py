"""PIN / biometric unlock screen."""

from __future__ import annotations

from typing import Awaitable, Callable, Optional

import flet as ft

from lib.infrastructure.services.biometric import BiometricResult, BiometricStatus
from lib.infrastructure.services.encryption_service import EncryptionService
from lib.presentation.theme import is_dark_mode, page_gradient
from lib.presentation.utils import run_async, snack, tr


def _biometric_error_key(result: BiometricResult) -> str:
    mapping = {
        BiometricResult.CANCELED: "lock.biometric_canceled",
        BiometricResult.DEVICE_NOT_PRESENT: "lock.biometric_no_device",
        BiometricResult.NOT_CONFIGURED: "lock.biometric_not_configured",
        BiometricResult.DISABLED_BY_POLICY: "lock.biometric_policy",
        BiometricResult.DEVICE_BUSY: "lock.biometric_busy",
        BiometricResult.RETRIES_EXHAUSTED: "lock.biometric_retries",
        BiometricResult.UNSUPPORTED: "lock.biometric_unavailable",
        BiometricResult.FAILED: "lock.biometric_failed",
    }
    return mapping.get(result, "lock.biometric_failed")


class LockScreen(ft.Container):
    """Full-screen lock gate shown when a PIN is configured."""

    def __init__(
        self,
        page: ft.Page,
        *,
        language: str,
        pin_hash: str,
        pin_salt: str,
        biometric_enabled: bool,
        on_unlocked: Callable[[], Awaitable[None] | None],
        encryption: Optional[EncryptionService] = None,
        auto_biometric: bool = True,
    ) -> None:
        self._page = page
        self._lang = language
        self._pin_hash = pin_hash
        self._pin_salt = pin_salt
        self._biometric_enabled = biometric_enabled
        self._auto_biometric = auto_biometric
        self._on_unlocked = on_unlocked
        self._crypto = encryption or EncryptionService()
        self._biometric_busy = False
        self._pin = ft.TextField(
            label=tr("settings.pin", language),
            password=True,
            can_reveal_password=True,
            max_length=8,
            keyboard_type=ft.KeyboardType.NUMBER,
            width=280,
            text_align=ft.TextAlign.CENTER,
            border_radius=14,
            filled=True,
            bgcolor=ft.Colors.SURFACE_CONTAINER,
            on_submit=lambda _e: run_async(page, self._try_pin),
            autofocus=not biometric_enabled,
        )
        self._error = ft.Text("", color=ft.Colors.ERROR, size=12)
        self._bio_btn = ft.OutlinedButton(
            tr("settings.biometric", language),
            icon=ft.Icons.FINGERPRINT,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=14),
                padding=ft.Padding.symmetric(horizontal=18, vertical=14),
            ),
            width=280,
            visible=biometric_enabled,
            on_click=lambda _e: run_async(page, self._try_biometric),
        )

        btn_style = ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=14),
            padding=ft.Padding.symmetric(horizontal=18, vertical=14),
        )
        actions: list[ft.Control] = [
            ft.FilledButton(
                tr("lock.unlock", language),
                icon=ft.Icons.LOCK_OPEN,
                style=btn_style,
                width=280,
                on_click=lambda _e: run_async(page, self._try_pin),
            ),
            self._bio_btn,
        ]

        dark = is_dark_mode(page)
        super().__init__(
            expand=True,
            alignment=ft.Alignment.CENTER,
            gradient=page_gradient(dark),
            content=ft.Container(
                width=340,
                padding=28,
                border_radius=24,
                bgcolor=ft.Colors.SURFACE_CONTAINER,
                border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
                shadow=ft.BoxShadow(
                    blur_radius=30,
                    color="#00000044",
                    offset=ft.Offset(0, 12),
                ),
                content=ft.Column(
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=16,
                    tight=True,
                    controls=[
                        ft.Container(
                            width=72,
                            height=72,
                            border_radius=22,
                            bgcolor=ft.Colors.PRIMARY_CONTAINER,
                            alignment=ft.Alignment.CENTER,
                            content=ft.Icon(
                                ft.Icons.FINGERPRINT
                                if biometric_enabled
                                else ft.Icons.LOCK,
                                size=34,
                                color=ft.Colors.ON_PRIMARY_CONTAINER,
                            ),
                        ),
                        ft.Text(
                            tr("app.name", language),
                            size=30,
                            weight=ft.FontWeight.W_700,
                            color=ft.Colors.PRIMARY,
                        ),
                        ft.Text(
                            tr(
                                "lock.subtitle_bio" if biometric_enabled else "lock.subtitle",
                                language,
                            ),
                            size=14,
                            color=ft.Colors.ON_SURFACE_VARIANT,
                            text_align=ft.TextAlign.CENTER,
                        ),
                        self._pin,
                        self._error,
                        ft.Column(
                            spacing=10,
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            tight=True,
                            controls=actions,
                        ),
                    ],
                ),
            ),
        )
        if biometric_enabled and auto_biometric:
            run_async(page, self._bootstrap_biometric)

    async def _bootstrap_biometric(self) -> None:
        """Probe OS support, then auto-open the Hello / biometric prompt."""
        status = await self._crypto.refresh_biometric_status()
        self._bio_btn.visible = self._biometric_enabled
        try:
            self._bio_btn.update()
        except Exception:  # noqa: BLE001
            pass
        if status is BiometricStatus.AVAILABLE:
            await self._try_biometric()

    async def _finish(self) -> None:
        result = self._on_unlocked()
        if hasattr(result, "__await__"):
            await result  # type: ignore[misc]

    async def _try_pin(self) -> None:
        pin = (self._pin.value or "").strip()
        if self._crypto.verify_pin(pin, self._pin_hash, self._pin_salt):
            await self._finish()
            return
        self._error.value = tr("lock.wrong_pin", self._lang)
        self._pin.value = ""
        self.update()

    async def _try_biometric(self) -> None:
        if self._biometric_busy:
            return
        self._biometric_busy = True
        self._error.value = ""
        try:
            self.update()
        except Exception:  # noqa: BLE001
            pass
        try:
            result = await self._crypto.authenticate_biometric(
                message=tr("lock.biometric_prompt", self._lang),
            )
            if result is BiometricResult.VERIFIED:
                await self._finish()
                return
            if result is BiometricResult.CANCELED:
                # Soft: user dismissed the prompt — keep PIN field ready.
                return
            msg = tr(_biometric_error_key(result), self._lang)
            self._error.value = msg
            snack(self._page, msg, error=True)
            try:
                self.update()
            except Exception:  # noqa: BLE001
                pass
        finally:
            self._biometric_busy = False
