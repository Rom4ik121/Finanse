"""Biometric env override paths."""

from __future__ import annotations

import asyncio

from lib.infrastructure.services.biometric import (
    BiometricResult,
    BiometricStatus,
    biometric_env_override_ok,
    probe_biometric_status,
    request_biometric_verification,
    status_is_usable,
)
from lib.infrastructure.services.encryption_service import EncryptionService


def test_env_override(monkeypatch) -> None:
    monkeypatch.setenv("FINANCE_BIOMETRIC_OK", "1")
    assert biometric_env_override_ok() is True

    async def _run() -> None:
        assert await probe_biometric_status() is BiometricStatus.AVAILABLE
        assert await request_biometric_verification("test") is BiometricResult.VERIFIED
        service = EncryptionService()
        assert await service.authenticate_biometric() is BiometricResult.VERIFIED

    asyncio.run(_run())


def test_status_is_usable() -> None:
    assert status_is_usable(BiometricStatus.AVAILABLE) is True
    assert status_is_usable(BiometricStatus.UNSUPPORTED) is False
