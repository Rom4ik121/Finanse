"""Biometric env override paths."""

from __future__ import annotations

import asyncio
from typing import Any

from lib.infrastructure.services.biometric import (
    BiometricResult,
    BiometricStatus,
    biometric_env_override_ok,
    mobile_runtime,
    platform_supports_biometrics,
    probe_biometric_status,
    request_biometric_verification,
    set_local_auth_service,
    status_is_usable,
)
from lib.infrastructure.services.encryption_service import EncryptionService


class _FakeLocalAuth:
    def __init__(
        self,
        *,
        supported: bool = True,
        can_check: bool = True,
        biometrics: list[str] | None = None,
        auth_result: dict[str, Any] | None = None,
    ) -> None:
        self._supported = supported
        self._can_check = can_check
        self._biometrics = biometrics if biometrics is not None else ["fingerprint"]
        self._auth_result = auth_result or {"ok": True, "code": None}

    async def is_device_supported(self) -> bool:
        return self._supported

    async def can_check_biometrics(self) -> bool:
        return self._can_check

    async def get_available_biometrics(self) -> list[str]:
        return list(self._biometrics)

    async def authenticate(self, *, reason: str, biometric_only: bool = True) -> dict[str, Any]:
        return dict(self._auth_result)


def test_env_override(monkeypatch) -> None:
    monkeypatch.setenv("FINANCE_BIOMETRIC_OK", "1")
    assert biometric_env_override_ok() is True

    async def _run() -> None:
        assert await probe_biometric_status() is BiometricStatus.AVAILABLE
        assert await request_biometric_verification("test") is BiometricResult.VERIFIED
        service = EncryptionService()
        assert await service.authenticate_biometric() is BiometricResult.VERIFIED

    asyncio.run(_run())


def test_mobile_probe_and_auth(monkeypatch) -> None:
    monkeypatch.setenv("FLET_PLATFORM", "android")
    set_local_auth_service(_FakeLocalAuth())
    assert mobile_runtime() is True
    assert platform_supports_biometrics() is True

    async def _run() -> None:
        assert await probe_biometric_status() is BiometricStatus.AVAILABLE
        assert await request_biometric_verification("unlock") is BiometricResult.VERIFIED

    asyncio.run(_run())
    set_local_auth_service(None)
    monkeypatch.delenv("FLET_PLATFORM", raising=False)


def test_mobile_not_configured(monkeypatch) -> None:
    monkeypatch.setenv("FLET_PLATFORM", "android")
    set_local_auth_service(_FakeLocalAuth(biometrics=[]))

    async def _run() -> None:
        assert await probe_biometric_status() is BiometricStatus.NOT_CONFIGURED

    asyncio.run(_run())
    set_local_auth_service(None)
    monkeypatch.delenv("FLET_PLATFORM", raising=False)


def test_mobile_cancel_maps(monkeypatch) -> None:
    monkeypatch.setenv("FLET_PLATFORM", "ios")
    set_local_auth_service(
        _FakeLocalAuth(auth_result={"ok": False, "code": "UserCanceled"})
    )

    async def _run() -> None:
        assert await request_biometric_verification("unlock") is BiometricResult.CANCELED

    asyncio.run(_run())
    set_local_auth_service(None)
    monkeypatch.delenv("FLET_PLATFORM", raising=False)


def test_status_is_usable() -> None:
    assert status_is_usable(BiometricStatus.AVAILABLE) is True
    assert status_is_usable(BiometricStatus.UNSUPPORTED) is False
