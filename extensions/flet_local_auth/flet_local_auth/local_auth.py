"""FinanseLocalAuth — OS fingerprint / Face ID via local_auth."""

from __future__ import annotations

from typing import Any

import flet as ft

__all__ = ["FinanseLocalAuth"]


@ft.control("FinanseLocalAuth")
class FinanseLocalAuth(ft.Service):
    """Non-visual service that shows the platform biometric prompt."""

    async def is_device_supported(self) -> bool:
        """True when the device can show any local auth (PIN/biometric)."""
        return bool(await self._invoke_method("is_device_supported"))

    async def can_check_biometrics(self) -> bool:
        """True when biometric hardware is available."""
        return bool(await self._invoke_method("can_check_biometrics"))

    async def get_available_biometrics(self) -> list[str]:
        """Biometric types enrolled on the device (e.g. fingerprint, face)."""
        result = await self._invoke_method("get_available_biometrics")
        if isinstance(result, list):
            return [str(item) for item in result]
        return []

    async def authenticate(
        self,
        *,
        reason: str,
        biometric_only: bool = True,
    ) -> dict[str, Any]:
        """Show the OS biometric sheet.

        Returns:
            ``{"ok": bool, "code": str | None}`` — ``code`` is set on failure.
        """
        result = await self._invoke_method(
            "authenticate",
            {"reason": reason, "biometric_only": biometric_only},
        )
        if isinstance(result, dict):
            return {
                "ok": bool(result.get("ok")),
                "code": result.get("code"),
            }
        return {"ok": bool(result), "code": None}
