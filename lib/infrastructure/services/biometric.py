"""Platform biometric / Windows Hello / mobile local_auth verification."""

from __future__ import annotations

import logging
import os
import sys
from enum import Enum
from typing import Any, Protocol

logger = logging.getLogger("finanse.infrastructure.services.biometric")


class BiometricStatus(str, Enum):
    """Whether the OS can present a biometric / Hello prompt."""

    AVAILABLE = "available"
    DEVICE_NOT_PRESENT = "device_not_present"
    NOT_CONFIGURED = "not_configured"
    DISABLED_BY_POLICY = "disabled_by_policy"
    DEVICE_BUSY = "device_busy"
    UNSUPPORTED = "unsupported"


class BiometricResult(str, Enum):
    """Outcome of a verification attempt."""

    VERIFIED = "verified"
    CANCELED = "canceled"
    DEVICE_NOT_PRESENT = "device_not_present"
    NOT_CONFIGURED = "not_configured"
    DISABLED_BY_POLICY = "disabled_by_policy"
    DEVICE_BUSY = "device_busy"
    RETRIES_EXHAUSTED = "retries_exhausted"
    FAILED = "failed"
    UNSUPPORTED = "unsupported"


class LocalAuthBridge(Protocol):
    """Subset of :class:`flet_local_auth.FinanseLocalAuth` used by Finanse."""

    async def is_device_supported(self) -> bool: ...

    async def can_check_biometrics(self) -> bool: ...

    async def get_available_biometrics(self) -> list[str]: ...

    async def authenticate(
        self, *, reason: str, biometric_only: bool = True
    ) -> dict[str, Any]: ...


_local_auth_service: LocalAuthBridge | None = None


def set_local_auth_service(service: LocalAuthBridge | None) -> None:
    """Register the Flet local_auth service (Android / iOS builds)."""
    global _local_auth_service
    _local_auth_service = service


def get_local_auth_service() -> LocalAuthBridge | None:
    """Return the registered mobile auth service, if any."""
    return _local_auth_service


def biometric_env_override_ok() -> bool:
    """Test hook: ``FINANCE_BIOMETRIC_OK=1`` forces success."""
    return os.environ.get("FINANCE_BIOMETRIC_OK", "").strip().lower() in {
        "1",
        "true",
        "yes",
    }


def mobile_runtime() -> bool:
    """True when Python runs inside a packaged Flet Android / iOS app."""
    return os.getenv("FLET_PLATFORM", "").strip().lower() in {"android", "ios"}


def platform_supports_biometrics() -> bool:
    """True when this build can talk to an OS biometric API."""
    if biometric_env_override_ok():
        return True
    if mobile_runtime():
        return _local_auth_service is not None
    if sys.platform != "win32":
        return False
    try:
        import winrt.windows.security.credentials.ui  # noqa: F401
    except Exception:  # noqa: BLE001
        return False
    return True


def _map_mobile_auth_code(code: str | None) -> BiometricResult:
    """Map ``local_auth`` / PlatformException codes to :class:`BiometricResult`."""
    normalized = (code or "").strip().lower().replace("_", "")
    if normalized in {"usercanceled", "canceled", "cancel", "auth_in_progress"}:
        return BiometricResult.CANCELED
    if normalized in {
        "notavailable",
        "nobiometrichardware",
        "otheroperatingsystem",
        "nohardware",
    }:
        return BiometricResult.DEVICE_NOT_PRESENT
    if normalized in {"notenrolled", "passcodenotset", "biometricnotavailable"}:
        return BiometricResult.NOT_CONFIGURED
    if normalized in {"lockedout", "permanentlylockedout", "toomanyattempts"}:
        return BiometricResult.RETRIES_EXHAUSTED
    if normalized in {"systemcancel", "timeout"}:
        return BiometricResult.DEVICE_BUSY
    if normalized in {"notinteractive", "securityupdate_required"}:
        return BiometricResult.DISABLED_BY_POLICY
    return BiometricResult.FAILED


async def _probe_mobile_status() -> BiometricStatus:
    service = _local_auth_service
    if service is None:
        return BiometricStatus.UNSUPPORTED
    try:
        if not await service.is_device_supported():
            return BiometricStatus.DEVICE_NOT_PRESENT
        if not await service.can_check_biometrics():
            return BiometricStatus.NOT_CONFIGURED
        biometrics = await service.get_available_biometrics()
        if not biometrics:
            return BiometricStatus.NOT_CONFIGURED
        return BiometricStatus.AVAILABLE
    except Exception:  # noqa: BLE001
        logger.exception("Mobile biometric availability check failed")
        return BiometricStatus.UNSUPPORTED


async def _request_mobile_verification(message: str) -> BiometricResult:
    service = _local_auth_service
    if service is None:
        return BiometricResult.UNSUPPORTED
    try:
        payload = await service.authenticate(reason=message, biometric_only=True)
    except Exception:  # noqa: BLE001
        logger.exception("Mobile biometric verification request failed")
        return BiometricResult.FAILED

    if payload.get("ok"):
        return BiometricResult.VERIFIED
    return _map_mobile_auth_code(payload.get("code"))


async def probe_biometric_status() -> BiometricStatus:
    """Ask the OS whether biometrics can be used."""
    if biometric_env_override_ok():
        return BiometricStatus.AVAILABLE
    if mobile_runtime():
        status = await _probe_mobile_status()
        logger.info("Mobile biometric availability: %s", status.value)
        return status
    if sys.platform != "win32":
        return BiometricStatus.UNSUPPORTED
    try:
        from winrt.windows.security.credentials.ui import (
            UserConsentVerifier,
            UserConsentVerifierAvailability,
        )
    except Exception:  # noqa: BLE001
        logger.info("winrt biometric packages not installed")
        return BiometricStatus.UNSUPPORTED

    try:
        raw = await UserConsentVerifier.check_availability_async()
    except Exception:  # noqa: BLE001
        logger.exception("Biometric availability check failed")
        return BiometricStatus.UNSUPPORTED

    mapping = {
        UserConsentVerifierAvailability.AVAILABLE: BiometricStatus.AVAILABLE,
        UserConsentVerifierAvailability.DEVICE_NOT_PRESENT: BiometricStatus.DEVICE_NOT_PRESENT,
        UserConsentVerifierAvailability.NOT_CONFIGURED_FOR_USER: BiometricStatus.NOT_CONFIGURED,
        UserConsentVerifierAvailability.DISABLED_BY_POLICY: BiometricStatus.DISABLED_BY_POLICY,
        UserConsentVerifierAvailability.DEVICE_BUSY: BiometricStatus.DEVICE_BUSY,
    }
    status = mapping.get(raw, BiometricStatus.UNSUPPORTED)
    logger.info("Biometric availability: %s", status.value)
    return status


async def request_biometric_verification(message: str) -> BiometricResult:
    """Show the OS consent prompt (Windows Hello / fingerprint / face)."""
    if biometric_env_override_ok():
        logger.info("Biometric accepted via FINANCE_BIOMETRIC_OK")
        return BiometricResult.VERIFIED

    if mobile_runtime():
        result = await _request_mobile_verification(message)
        logger.info("Mobile biometric verification result: %s", result.value)
        return result

    if sys.platform != "win32":
        return BiometricResult.UNSUPPORTED

    try:
        from winrt.windows.security.credentials.ui import (
            UserConsentVerificationResult,
            UserConsentVerifier,
        )
    except Exception:  # noqa: BLE001
        return BiometricResult.UNSUPPORTED

    try:
        raw = await UserConsentVerifier.request_verification_async(message)
    except Exception:  # noqa: BLE001
        logger.exception("Biometric verification request failed")
        return BiometricResult.FAILED

    mapping = {
        UserConsentVerificationResult.VERIFIED: BiometricResult.VERIFIED,
        UserConsentVerificationResult.CANCELED: BiometricResult.CANCELED,
        UserConsentVerificationResult.DEVICE_NOT_PRESENT: BiometricResult.DEVICE_NOT_PRESENT,
        UserConsentVerificationResult.NOT_CONFIGURED_FOR_USER: BiometricResult.NOT_CONFIGURED,
        UserConsentVerificationResult.DISABLED_BY_POLICY: BiometricResult.DISABLED_BY_POLICY,
        UserConsentVerificationResult.DEVICE_BUSY: BiometricResult.DEVICE_BUSY,
        UserConsentVerificationResult.RETRIES_EXHAUSTED: BiometricResult.RETRIES_EXHAUSTED,
    }
    result = mapping.get(raw, BiometricResult.FAILED)
    logger.info("Biometric verification result: %s", result.value)
    return result


def status_is_usable(status: BiometricStatus) -> bool:
    """Whether we should auto-prompt / advertise biometrics as ready."""
    return status is BiometricStatus.AVAILABLE
