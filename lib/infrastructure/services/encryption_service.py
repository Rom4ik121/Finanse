"""PIN hashing / verification and biometric unlock."""

from __future__ import annotations

import hashlib
import hmac
import logging
import secrets
from dataclasses import dataclass
from typing import Optional

from lib.infrastructure.services.biometric import (
    BiometricResult,
    BiometricStatus,
    probe_biometric_status,
    request_biometric_verification,
    status_is_usable,
)

logger = logging.getLogger("finanse.infrastructure.services.encryption")

_HASH_ITERATIONS = 120_000
_SALT_BYTES = 16
_DKLEN = 32


@dataclass(slots=True, frozen=True)
class PinCredentials:
    """Salted PIN hash material suitable for persistence."""

    pin_hash: str
    pin_salt: str


class EncryptionService:
    """PIN protection (PBKDF2-HMAC-SHA256) plus OS biometric consent."""

    def __init__(self, *, biometric_available: bool | None = None) -> None:
        # Optional cached flag from a prior probe; ``None`` means probe lazily.
        self._biometric_available = biometric_available
        self._last_status: BiometricStatus | None = None

    def hash_pin(self, pin: str, *, salt: Optional[str] = None) -> PinCredentials:
        """Hash a PIN with a random (or provided) salt."""
        if not pin:
            raise ValueError("PIN must not be empty")

        salt_bytes = bytes.fromhex(salt) if salt else secrets.token_bytes(_SALT_BYTES)
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            pin.encode("utf-8"),
            salt_bytes,
            _HASH_ITERATIONS,
            dklen=_DKLEN,
        )
        credentials = PinCredentials(
            pin_hash=digest.hex(),
            pin_salt=salt_bytes.hex(),
        )
        logger.debug("PIN hash generated")
        return credentials

    def verify_pin(self, pin: str, pin_hash: str, salt: str) -> bool:
        """Return True when ``pin`` matches the stored hash."""
        try:
            candidate = self.hash_pin(pin, salt=salt)
            ok = hmac.compare_digest(candidate.pin_hash, pin_hash)
            if not ok:
                logger.info("PIN verification failed")
            return ok
        except (ValueError, TypeError):
            logger.exception("PIN verification error")
            return False

    async def refresh_biometric_status(self) -> BiometricStatus:
        """Probe the OS and cache whether biometrics are ready."""
        status = await probe_biometric_status()
        self._last_status = status
        self._biometric_available = status_is_usable(status)
        return status

    def biometric_available(self) -> bool:
        """Cached readiness from the last probe (False until probed)."""
        if self._biometric_available is None:
            return False
        return bool(self._biometric_available)

    def last_biometric_status(self) -> BiometricStatus | None:
        """Most recent :func:`probe_biometric_status` result, if any."""
        return self._last_status

    async def authenticate_biometric(
        self,
        *,
        message: str = "Unlock Finanse",
    ) -> BiometricResult:
        """Show the OS biometric / Windows Hello prompt."""
        return await request_biometric_verification(message)

    def set_biometric_available(self, available: bool) -> None:
        """Override cached readiness (tests / DI)."""
        self._biometric_available = available
        if available:
            self._last_status = BiometricStatus.AVAILABLE
