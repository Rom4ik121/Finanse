"""Platform biometric / Windows Hello consent verification."""

from __future__ import annotations

import logging
import os
import sys
from enum import Enum

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


def biometric_env_override_ok() -> bool:
    """Test hook: ``FINANCE_BIOMETRIC_OK=1`` forces success."""
    return os.environ.get("FINANCE_BIOMETRIC_OK", "").strip().lower() in {
        "1",
        "true",
        "yes",
    }


def platform_supports_biometrics() -> bool:
    """True when this build can talk to an OS biometric API."""
    if biometric_env_override_ok():
        return True
    if sys.platform != "win32":
        return False
    try:
        import winrt.windows.security.credentials.ui  # noqa: F401
    except Exception:  # noqa: BLE001
        return False
    return True


async def probe_biometric_status() -> BiometricStatus:
    """Ask the OS whether Windows Hello / biometrics can be used."""
    if biometric_env_override_ok():
        return BiometricStatus.AVAILABLE
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
